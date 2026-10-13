"""Offline fixtures stay in TemporaryDirectory; never in real daily archives."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/rs-paper-pipeline/scripts"
sys.path.insert(0, str(SCRIPTS))
from clients import arxiv_client as client
from services import maritime as m


def paper(aid="2610.00001", title="Cross-modal sensor fusion for object tracking", abstract="Robust data association and uncertainty for autonomous driving.", date="2026-10-10"):
    return {"arxiv_id": aid, "version_id": aid + "v1", "title": title, "abstract": abstract,
        "authors": ["Test Author"], "published": date, "updated": date,
        "arxiv_url": f"https://arxiv.org/abs/{aid}", "pdf_url": f"https://arxiv.org/pdf/{aid}"}


def atom(ids=("2610.00001v1",), total=1):
    return '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/">' + f'<o:totalResults>{total}</o:totalResults>' + ''.join(
        f'<entry><id>https://arxiv.org/abs/{aid}</id><title>Object detection</title><summary>Efficient visual learning</summary><published>2026-10-10T00:00:00Z</published><updated>2026-10-10T00:00:00Z</updated><author><name>Original Author</name></author></entry>' for aid in ids) + '</feed>'


class MaritimeTests(unittest.TestCase):
    def setUp(self):
        sleeper = patch.object(m.time, "sleep")
        sleeper.start()
        self.addCleanup(sleeper.stop)
        self.rules = m.load_maritime_assets()
        self.library = {"schema_version": 1, "papers": {}, "days": {}}

    def test_four_topics_and_generic_methods_without_maritime(self):
        examples = [paper(), paper(title="Efficient object detection", abstract="Robust visual representation learning"),
            paper(title="Data association for trajectory prediction", abstract="Spatiotemporal motion matching"),
            paper(title="Self-supervised representation learning for vision", abstract="Cross-modal alignment and efficient transfer")]
        for key, p in zip("ABCD", examples):
            assessment = m.score_paper(p, self.rules)
            self.assertIn(key, assessment["topics"])
            self.assertNotEqual(assessment["level"], "excluded")
            self.assertTrue(assessment["reasons"])

    def test_generic_buzzwords_and_unrelated_domains_excluded(self):
        for title, abstract in [("Transformer Attention Foundation Model", "A new model"),
                ("Efficient representation learning", "Language-only generation"),
                ("Cross-modal sensor fusion", "Protein folding and drug discovery")]:
            self.assertEqual(m.score_paper(paper(title=title, abstract=abstract), self.rules)["level"], "excluded")

    def test_group_cap_prevents_keyword_stuffing(self):
        p = paper(title=" ".join(self.rules["topics"]["B"]["groups"]["task"]), abstract="")
        self.assertLessEqual(m.score_paper(p, self.rules)["topic_scores"]["B"], self.rules["group_cap"])

    def test_id_versions_urls_and_old_ids(self):
        self.assertEqual(client.canonical_arxiv_id("https://arxiv.org/pdf/2610.00001v12.pdf"), "2610.00001")
        self.assertEqual(client.canonical_arxiv_id("https://arxiv.org/abs/cs/9901001v3"), "cs/9901001")
        with self.assertRaises(ValueError):
            client.canonical_arxiv_id("../../other")

    @patch.object(client, "fetch_query_with_fallback")
    def test_paginated_generic_fetch_preserves_metadata(self, fetch):
        fetch.side_effect = [atom(total=2), atom(("2610.00002v2",), total=2)]
        with patch.object(client.time, "sleep") as sleep:
            result = client.fetch_topic_candidates('all:"object detection"', "2026-10-10", "2026-10-10", page_size=1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["authors"], ["Original Author"])
        self.assertEqual(result[1]["arxiv_id"], "2610.00002")
        self.assertEqual(result[1]["version_id"], "2610.00002v2")
        self.assertIn("submittedDate:[202610100000 TO 202610102359]", fetch.call_args.args[0]["search_query"])
        sleep.assert_called_once_with(3)

    @patch.object(client, "fetch_query_with_fallback")
    def test_scan_limit_and_error_feed_are_errors(self, fetch):
        fetch.return_value = atom(total=2)
        with self.assertRaises(client.ArxivUnavailableError):
            client.fetch_topic_candidates("x", "2026-10-10", "2026-10-10", page_size=1, max_pages=1)
        for xml in ['<html>bad gateway</html>', '<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>error</id></entry></feed>']:
            fetch.return_value = xml
            with self.assertRaises(client.ArxivUnavailableError):
                client.fetch_topic_candidates("x", "2026-10-10", "2026-10-10")

    def test_duplicate_and_replay_preserve_reading_and_history(self):
        p = paper()
        m.merge_candidates(self.library, [p, p], ["2026-10-10"], self.rules, ["A"])
        self.library["papers"][p["arxiv_id"]]["reading"] = {"analysis": "Keep", "state": "已精读"}
        newer = {**p, "version_id": p["arxiv_id"] + "v2", "updated": "2026-10-12", "title": "New object detection"}
        m.merge_candidates(self.library, [newer], ["2026-10-11"], self.rules, ["B"])
        m.merge_candidates(self.library, [p], ["2026-10-10"], self.rules, ["A"])
        self.assertEqual(len(self.library["papers"]), 1)
        self.assertEqual(self.library["papers"][p["arxiv_id"]]["title"], newer["title"])
        self.assertEqual(self.library["papers"][p["arxiv_id"]]["reading"]["analysis"], "Keep")
        self.assertEqual(len(self.library["days"]), 2)
        self.assertEqual(self.library["days"]["2026-10-10"]["candidate_ids"], [p["arxiv_id"]])

    def test_backup_is_transactional_and_markdown_exact(self):
        p = paper()
        m.merge_candidates(self.library, [p], [p["published"]], self.rules, ["A"])
        record = {"analysis": "# 方法\n\n公式 $x$\n<script>test</script>\n", "state": "值得复现", "updated_at": "2026-10-12"}
        backup = {"schema_version": 1, "readings": {p["arxiv_id"]: record}}
        m.import_backup(self.library, json.loads(json.dumps(backup)))
        self.assertEqual(self.library["papers"][p["arxiv_id"]]["reading"], record)
        before = copy.deepcopy(self.library)
        backup["readings"]["2610.00099"] = record
        with self.assertRaises(ValueError):
            m.import_backup(self.library, backup)
        self.assertEqual(before, self.library)

    @patch.object(m, "fetch_topic_candidates", side_effect=client.ArxivUnavailableError("HTTP 503"))
    def test_failure_does_not_publish_empty_day_or_overwrite(self, fetch):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            m.write_json(m.library_path(root), self.library)
            before = m.library_path(root).read_bytes()
            result = m.main(["--root", temp, "--date", "20261010"])
            self.assertEqual(result, 1)
            self.assertEqual(m.library_path(root).read_bytes(), before)
            self.assertFalse((root / "docs/maritime-data/library.json").exists())
            self.assertIn("503", (root / "papers/maritime/logs/errors.jsonl").read_text())

    @patch.object(m, "fetch_topic_candidates", return_value=[])
    def test_successful_empty_day_without_tokens(self, fetch):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"LLM_API_KEY": "", "GITHUB_TOKEN": ""}):
            self.assertEqual(m.main(["--root", temp, "--date", "20261010"]), 0)
            report = Path(temp) / "daily_reports/maritime/202610/20261010.md"
            self.assertIn("无入选论文", report.read_text(encoding="utf-8"))

    @patch.object(m, "fetch_topic_candidates", return_value=[])
    def test_topic_queries_and_selection(self, fetch):
        with tempfile.TemporaryDirectory() as temp:
            for key in "ABCD":
                self.assertEqual(m.main(["--root", temp, "--date", "20261010", "--topic", key]), 0)
                query = fetch.call_args.args[0]
                self.assertIn(self.rules["topics"][key]["queries"][0], query)
            self.assertEqual(m.load_library(Path(temp))["days"]["2026-10-10"]["searched_topics"], list("ABCD"))

    def test_report_limit_and_all_candidates_available_to_site(self):
        ps = [paper(f"2610.{i:05d}") for i in range(30)]
        m.merge_candidates(self.library, ps, ["2026-10-10"], self.rules, list("ABCD"))
        day = m.daily_data(self.library, "2026-10-10", self.rules)
        self.assertEqual(len(day["paper_ids"]), 25)
        self.assertEqual(len(day["candidate_ids"]), 30)
        self.assertEqual(day["omitted_count"], 5)

    def test_cli_dispatch_without_legacy_dependencies(self):
        env = {**os.environ, "LLM_API_KEY": "", "GITHUB_TOKEN": "", "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run([sys.executable, "-S", str(SCRIPTS / "cli.py"), "maritime", "--action", "doctor"], env=env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK", result.stdout)

    def test_cli_markdown_import_export_site_and_rescore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = paper()
            m.merge_candidates(self.library, [p], [p["published"]], self.rules, ["A"])
            m.write_json(m.library_path(root), self.library)
            markdown = root / "analysis.md"
            markdown.write_text("# 方法\n\n$x$\n", encoding="utf-8")
            self.assertEqual(m.main(["--root", temp, "--action", "import", "--id", p["arxiv_id"], "--file", str(markdown)]), 0)
            exported = root / "backup.json"
            self.assertEqual(m.main(["--root", temp, "--action", "export", "--file", str(exported)]), 0)
            self.assertEqual(m.main(["--root", temp, "--action", "rescore"]), 0)
            public = m.read_json(root / "docs/maritime-data/library.json", {})
            backup = m.read_json(exported, {})
            self.assertEqual(public["papers"][0]["reading"], backup["readings"][p["arxiv_id"]])
            self.assertEqual(public["papers"][0]["reading"]["analysis"], markdown.read_text(encoding="utf-8"))

    @patch.object(m, "fetch_topic_candidates", return_value=[])
    def test_all_topics_are_smaller_separate_requests(self, fetch):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(m.main(["--root", temp, "--date", "20261010"]), 0)
            self.assertEqual(fetch.call_count, 4)
            for key, call in zip("ABCD", fetch.call_args_list):
                expected = " OR ".join(f"({q})" for q in self.rules["topics"][key]["queries"])
                self.assertEqual(call.args[0], expected)

    @patch.object(m, "fetch_topic_candidates")
    def test_later_topic_failure_does_not_publish_partial_library(self, fetch):
        fetch.side_effect = [[paper()], client.ArxivUnavailableError("HTTP 500")]
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(m.main(["--root", temp, "--date", "20261010"]), 1)
            self.assertFalse(m.library_path(Path(temp)).exists())

    @patch.object(client, "fetch_url_with_retry")
    def test_500_falls_back_only_when_enabled(self, fetch):
        import io
        from urllib.error import HTTPError
        fetch.side_effect = [HTTPError("url", 500, "Internal error", {}, io.BytesIO(b"search failed")), "<feed />"]
        self.assertEqual(client.fetch_query_with_fallback({"search_query": "x"}, fallback_server_errors=True), "<feed />")
        self.assertEqual(fetch.call_count, 2)
        fetch.reset_mock()
        fetch.side_effect = HTTPError("url", 500, "Internal error", {}, io.BytesIO(b"search failed"))
        with self.assertRaisesRegex(client.ArxivUnavailableError, "500: search failed"):
            client.fetch_query_with_fallback({"search_query": "x"})
        self.assertEqual(fetch.call_count, 1)


if __name__ == "__main__":
    unittest.main()
