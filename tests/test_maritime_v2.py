import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/rs-paper-pipeline/scripts"))
from services import maritime as m, maritime_v2 as v, maritime_reading as reading
from clients import scholarly_client as s


def record(scheme="JCR", year=2025, value="Q1", category="VISION"):
    return {"scheme": scheme, "year": year, "category": category, "metric": "JIF Quartile", "quartile": value,
        "partition": 1 if value == "Q1" else 2, "scope": "major", "official_table": True, "verified": True,
        "evidence": {"kind": "institution", "url": "https://example.test/evidence", "checked_at": "2026-10-12"}}


def paper(aid="2610.00001", title="Maritime sensor fusion for object detection", abstract="Robust cross-modal matching for vessels"):
    return {"arxiv_id": aid, "title": title, "abstract": abstract, "authors": ["First Author", "Other Author"],
        "published": "2026-10-10", "arxiv_url": f"https://arxiv.org/abs/{aid}", "pdf_url": f"https://arxiv.org/pdf/{aid}"}


class V2Tests(unittest.TestCase):
    def test_recommendation_quotas_and_shortages_do_not_fill_other_buckets(self):
        samples = []
        for bucket, count in (("water", 15), ("land", 8), ("general", 4)):
            for i in range(count):
                samples.append({"paper_id": f"{bucket}-{i}", "recommendation": {"bucket": bucket}})
        result = v.select_recommendations(samples, self.policy)
        self.assertEqual({k: len(ids) for k, ids in result.items()}, {"water": 12, "land": 6, "general": 2})
        result = v.select_recommendations([p for p in samples if p["recommendation"]["bucket"] != "general"], self.policy)
        self.assertEqual(len(result["general"]), 0)
        self.assertEqual(len(result["water"]), 12)

    def test_direction_allows_related_arxiv_and_does_not_guess_journal_quality(self):
        def tagged(title, level="high", formal=False):
            p = {**paper(title=title, abstract=""), "assessment": {"level": level}}
            if formal:
                p.update(self.formal)
                p.update(title=title, abstract="", assessment={"level": level})
                p.pop("arxiv_id", None)
            return v.annotate(p, "test-id", self.venues, self.policy)["recommendation"]["bucket"]
        self.assertEqual(tagged("Ship object detection"), "water")
        self.assertEqual(tagged("Vehicle object detection"), "land")
        self.assertEqual(tagged("Vehicle object detection", "transfer"), "land")
        self.assertEqual(tagged("Vehicle object detection", "general"), "candidate")
        self.assertEqual(tagged("General visual perception"), "general")
        self.assertEqual(tagged("Ship structural mechanics"), "candidate")
        self.assertEqual(tagged("General visual perception", formal=True), "candidate")
        self.venues["journals"][0]["jcr_records"] = [record()]
        self.assertEqual(tagged("General visual perception", formal=True), "general")

    def test_ccf_a_requires_verified_publication_and_outranks_arxiv(self):
        fake = {**paper(title="CVPR visual perception"), "assessment": {"level": "high"}}
        fake = v.annotate(fake, "arxiv", self.venues, self.policy)
        self.assertFalse(fake["quality"]["ccf_a"])
        formal = {**fake, "venue_type": "conference", "publication_status": "published", "venue": "CVPR 2025",
                  "doi": "10.1234/cvpr", "publication_evidence": {"source": "Crossref"}}
        formal = v.annotate(formal, "formal", self.venues, self.policy)
        self.assertTrue(formal["quality"]["ccf_a"])
        self.assertGreater(v.rank_key(formal), v.rank_key(fake))
        formal["venue"] = "CVPR Workshop"
        self.assertFalse(v.venue_quality(formal, self.venues, self.policy)["ccf_a"])
        formal["venue"] = "CVPR Short Papers"
        self.assertFalse(v.venue_quality(formal, self.venues, self.policy)["ccf_a"])

    def setUp(self):
        self.rules = m.load_maritime_assets()
        self.venues, self.policy = v.assets()
        self.venues = {"journals": [{"id": "test", "name": "Test Journal", "issn": ["1234-5678"], "cas_records": [], "jcr_records": []}]}
        self.formal = {**paper(), "issn": ["1234-5678"], "doi": "10.1234/a", "venue": "Test Journal", "venue_type": "journal", "publication_status": "published"}

    def test_or_cas_only_jcr_only_both_and_unverified(self):
        journal = self.venues["journals"][0]
        journal["cas_records"] = [record("CAS")]
        journal["jcr_records"] = [record(value="Q2")]
        q = v.venue_quality(self.formal, self.venues, self.policy)
        self.assertTrue(q["high_journal"])
        self.assertFalse(q["both"])
        journal["cas_records"] = [record("CAS", value="Q2")]
        journal["jcr_records"] = [record()]
        q = v.venue_quality(self.formal, self.venues, self.policy)
        self.assertTrue(q["high_journal"])
        self.assertFalse(q["cas_one"])
        journal["cas_records"] = [record("CAS")]
        self.assertTrue(v.venue_quality(self.formal, self.venues, self.policy)["both"])
        journal["cas_records"] = []
        journal["jcr_records"][0]["verified"] = False
        self.assertFalse(v.venue_quality(self.formal, self.venues, self.policy)["high_journal"])

    def test_jif_not_jci_sjr_and_latest_category_year(self):
        journal = self.venues["journals"][0]
        journal["jcr_records"] = [record(year=2024), record(year=2025, value="Q2")]
        self.assertFalse(v.venue_quality(self.formal, self.venues, self.policy)["jcr_q1"])
        journal["jcr_records"].append(record(year=2025, category="FUSION"))
        q = v.venue_quality(self.formal, self.venues, self.policy)
        self.assertTrue(q["jcr_q1"])
        self.assertEqual(len(q["jcr_records"]), 3)
        for metric in ("JCI Quartile", "SJR Quartile"):
            journal["jcr_records"] = [{**record(), "metric": metric}]
            self.assertFalse(v.venue_quality(self.formal, self.venues, self.policy)["jcr_q1"])
        journal["cas_records"] = [record("CAS", year=2026), {**record("CAS"), "scope": "minor"}]
        self.assertFalse(v.venue_quality(self.formal, self.venues, self.policy)["cas_one"])

    def test_no_evidence_or_wrong_issn_never_quality(self):
        r = record()
        r["evidence"] = {}
        self.venues["journals"][0]["jcr_records"] = [r]
        self.assertFalse(v.venue_quality(self.formal, self.venues, self.policy)["high_journal"])
        self.venues["journals"][0]["jcr_records"] = [record()]
        self.assertFalse(v.venue_quality({**self.formal, "issn": ["0000-0000"]}, self.venues, self.policy)["high_journal"])
        self.assertFalse(v.venue_quality({**self.formal, "publication_status": "unknown"}, self.venues, self.policy)["high_journal"])

    def test_low_priority_does_not_take_homepage_and_generic_kept(self):
        for p in [paper(title="Medical cross-modal sensor fusion", abstract="visual perception representation learning for lesions"),
                  paper(title="Trajectory prediction", abstract="Spatiotemporal motion forecasting")]:
            p["assessment"] = m.score_paper(p, self.rules)
            v.annotate(p, p["arxiv_id"], self.venues, self.policy)
            self.assertEqual(p["recommendation"]["section"], "candidate")
        p = self.formal
        self.venues["journals"][0]["jcr_records"] = [record()]
        p["assessment"] = m.score_paper(p, self.rules)
        v.annotate(p, p["arxiv_id"], self.venues, self.policy)
        self.assertEqual(p["recommendation"]["section"], "maritime")
        p = {**p, "title": "Robust sensor fusion for object detection", "abstract": "Cross-modal matching for robots"}
        p["assessment"] = m.score_paper(p, self.rules)
        v.annotate(p, p["arxiv_id"], self.venues, self.policy)
        self.assertEqual(p["recommendation"]["section"], "methods")

    def test_metadata_first_author_mapping_and_inverted_index(self):
        cross = s.crossref_paper({"DOI": "10.1234/A", "type": "journal-article", "title": ["Ship detection"], "container-title": ["Test"],
            "published": {"date-parts": [[2025, 12]]}, "author": [{"given": "First", "family": "Person", "affiliation": [{"name": "First Institute"}]},
            {"given": "Other", "family": "Person", "affiliation": [{"name": "Other Institute"}]}]})
        self.assertEqual(cross["first_author_affiliations"], ["First Institute"])
        self.assertEqual(cross["published"], "2025-12")  # Do not invent day=1.
        oa = s.openalex_paper({"id": "https://openalex.org/W1", "doi": "https://doi.org/10.1234/a", "title": "Ship detection", "publication_date": "2025-12-01",
            "abstract_inverted_index": {"ship": [0, 2], "detect": [1]}, "primary_location": {"source": {"id": "S1", "type": "journal", "display_name": "Test", "issn": ["1234-5678"]}},
            "authorships": [{"author_position": "last", "author": {"display_name": "Other"}, "institutions": [{"display_name": "Wrong Institute"}]},
            {"author_position": "first", "author": {"display_name": "First"}, "institutions": [{"display_name": "Right Institute"}]}]})
        self.assertEqual(oa["first_author_affiliations"], ["Right Institute"])
        self.assertEqual(oa["abstract"], "ship detect ship")

    def test_safe_identity_merge_keeps_reading_and_title_not_identity(self):
        p = paper()
        p["reading"] = {"analysis": "Keep", "state": "已精读"}
        library = {"schema_version": 1, "papers": {p["arxiv_id"]: p}, "days": {}}
        incoming = {**self.formal, "paper_id": "doi:10.1234/a", "identity_evidence": {"source": "OpenAlex", "relation": "location"}, "metadata_source": ["OpenAlex"]}
        v.merge_records(library, [incoming], self.rules)
        self.assertEqual(len(library["papers"]), 1)
        self.assertEqual(library["papers"][p["arxiv_id"]]["reading"]["analysis"], "Keep")
        independent = {**incoming, "arxiv_id": None, "doi": "10.1234/b", "paper_id": "doi:10.1234/b"}
        v.merge_records(library, [independent], self.rules)
        self.assertEqual(len(library["papers"]), 2)
        v.merge_records(library, [{**incoming, "arxiv_id": None}], self.rules)
        self.assertEqual(len(library["papers"]), 2)

    def test_translation_cache_failure_and_manual_revision(self):
        p = paper(abstract="AIS uses Radar and LiDAR.")
        p["translation"] = reading.translate_one(p, lambda text: "方法：" + text)
        self.assertEqual(p["translation"]["status"], "machine")
        self.assertIn("LiDAR", p["translation"]["zh"])
        fake = lambda text: self.fail("cache not reused")
        self.assertEqual(reading.translate_one(p, fake), p["translation"])
        p["abstract"] += " New abstract."
        result = reading.translate_one(p, lambda text: (_ for _ in ()).throw(RuntimeError("failure")))
        self.assertEqual(result["status"], "failed")
        p["translation"] = {"status": "manual", "zh": "人工修订"}
        self.assertEqual(reading.translate_one(p, fake)["zh"], "人工修订")

    def test_pdf_html_rejected_and_private_prompt(self):
        p = {**paper(), "paper_id": "2610.00001"}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            local = root / "wrong.pdf"
            local.write_bytes(b"<html>login</html>")
            with self.assertRaises(ValueError):
                reading.prepare_pdf(p, root, local)
            local.write_bytes(b"%PDF-1.4\nmock fixture\n")
            manifest = reading.prepare_pdf(p, root, local)
            self.assertEqual(manifest["status"], "local_pdf_prepared")
            self.assertTrue(list(root.glob("papers/maritime/private/reading/*/prompt.md")))
            self.assertFalse((root / "docs").exists())

    @patch.object(s, "fetch_doi")
    def test_source_failure_keeps_success_and_returns_nonzero(self, fetch):
        incoming = {**self.formal, "paper_id": "doi:10.1234/a", "metadata_source": ["Crossref"]}
        fetch.side_effect = [incoming, RuntimeError("OpenAlex unavailable")]
        with tempfile.TemporaryDirectory() as temp:
            code = m.main(["--root", temp, "--action", "fetch-all", "--source", "crossref", "--source", "openalex", "--doi", "10.1234/a"])
            self.assertEqual(code, 1)
            library = m.load_library(Path(temp))
            self.assertEqual(len(library["papers"]), 1)
            self.assertEqual([r["status"] for r in library["source_runs"]], ["success", "failed"])

    def test_doi_backup_roundtrip_and_public_omits_private_assets(self):
        library = {"schema_version": 2, "papers": {"doi:10.1234/a": {**self.formal, "arxiv_id": None}}, "days": {}}
        m.import_backup(library, {"schema_version": 1, "readings": {"doi:10.1234/a": {"analysis": "# 原文", "state": "待读"}}})
        self.assertEqual(library["papers"]["doi:10.1234/a"]["reading"]["analysis"], "# 原文")

    def test_conference_submission_claim_and_workshops_not_high(self):
        p = {**paper(title="Accepted at CVPR"), "venue": "CVPR 2026", "venue_type": "unknown", "publication_status": "unknown"}
        p["assessment"] = m.score_paper(p, self.rules)
        v.annotate(p, p["arxiv_id"], self.venues, self.policy)
        self.assertFalse(p["quality"]["high_conference"])
        p.update({"doi": "10.1234/c", "venue_type": "conference", "publication_status": "published", "venue": "CVPR Workshops 2026", "publication_evidence": {"source": "Crossref"}})
        self.assertFalse(v.venue_quality(p, self.venues, self.policy)["high_conference"])
        p["venue"] = "CVPR 2026"
        self.assertTrue(v.venue_quality(p, self.venues, self.policy)["high_conference"])
        evidence = {**record(), "scheme": "official_proceedings", "paper_id": "openalex:W1", "venue": "NeurIPS 2025"}
        self.venues["conference_records"] = [evidence]
        p.update({"doi": "", "publication_status": "unknown", "publication_evidence": {}})
        v.annotate(p, "openalex:W1", self.venues, self.policy)
        self.assertTrue(p["quality"]["high_conference"])

    def test_old_arxiv_refresh_preserves_formal_doi_and_reading(self):
        p = {**self.formal, "publication_date": "2025-11-05", "published": "2025-11-05", "reading": {"analysis": "Keep", "state": "已精读"}}
        library = {"schema_version": 2, "papers": {p["arxiv_id"]: p}, "days": {}}
        m.merge_candidates(library, [{**paper(), "doi": "", "updated": "2026-10-12"}], ["2026-10-10"], self.rules, ["A"])
        saved = library["papers"][p["arxiv_id"]]
        self.assertEqual(saved["doi"], "10.1234/a")
        self.assertEqual(saved["published"], "2025-11-05")
        self.assertEqual(saved["reading"]["analysis"], "Keep")
        library["papers"]["doi:10.1234/a"] = library["papers"].pop(p["arxiv_id"])
        m.merge_candidates(library, [paper()], ["2026-10-10"], self.rules, ["A"])
        self.assertEqual(len(library["papers"]), 1)
        self.assertEqual(m.resolve_paper_id(library, p["arxiv_id"]), "doi:10.1234/a")

    def test_manual_scope_stats_not_padded_and_original_library_preserved(self):
        p = paper()
        library = {"schema_version": 1, "papers": {p["arxiv_id"]: p}, "days": {}}
        v.normalize_library(library, self.rules)
        sections = v.select_sections(list(library["papers"].values()), self.policy)
        self.assertEqual(len(sections["maritime"]), 0)
        self.assertEqual(len(sections["preprints"]), 1)
        backup = ROOT / "papers/maritime/backups/pre-v2-library.json"
        current = m.load_library(ROOT)
        if backup.exists():
            before = json.loads(backup.read_text(encoding="utf-8"))
            self.assertTrue(set(before["papers"]).issubset(current["papers"]))
            for key, old in before["papers"].items():
                if "reading" in old:
                    self.assertEqual(old["reading"], current["papers"][key]["reading"])

    def test_venue_import_does_not_erase_other_scheme_and_rejects_identity(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(v, "CONFIG_DIR", Path(temp)):
            venues = copy.deepcopy(self.venues)
            venues["journals"][0]["cas_records"] = [record("CAS")]
            directory = Path(temp)
            m.write_json(directory / "venues.json", venues)
            m.write_json(directory / "recommendation.json", self.policy)
            m.write_json(directory / "import.json", {"journals": [{"id": "test", "issn": ["1234-5678"], "jcr_records": [record()]}]})
            v.import_venues(directory / "import.json")
            saved = m.read_json(directory / "venues.json", {})
            self.assertEqual(saved["journals"][0]["cas_records"], venues["journals"][0]["cas_records"])
            before = (directory / "venues.json").read_bytes()
            m.write_json(directory / "import.json", {"journals": [{"id": "test", "issn": ["9999-9999"], "jcr_records": []}]})
            with self.assertRaises(ValueError):
                v.import_venues(directory / "import.json")
            self.assertEqual(before, (directory / "venues.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
