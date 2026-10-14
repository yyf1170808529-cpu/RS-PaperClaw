import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/rs-paper-pipeline/scripts"))
from services import maritime_validity as validity, maritime_v2 as v2
from test_maritime_v2 import record, paper


class ValidityTests(unittest.TestCase):
    def setUp(self):
        self.venues = {"journals": [{"id": "test", "name": "Test Journal", "issn": ["1234-5678"],
                                    "jcr_records": [record()]}]}
        _, self.policy = v2.assets()
        self.formal = {**paper(), "doi": "10.1234/test", "issn": ["1234-5678"], "venue": "Test Journal",
                       "venue_type": "journal", "publication_status": "published",
                       "publication_evidence": {"source": "Crossref", "type": "journal-article", "url": "https://api.crossref.org/works/10.1234/test"},
                       "assessment": {"level": "high"}}

    def test_repository_doi_is_not_a_journal(self):
        p = {**self.formal, "doi": "10.5281/zenodo.1", "venue": "Zenodo", "resource_metadata_type": "dataset"}
        p = v2.annotate(p, "repo", self.venues, self.policy)
        self.assertEqual(p["resource_type"], "dataset")
        self.assertFalse(p["quality"]["high_journal"])
        self.assertEqual(p["recommendation"]["bucket"], "candidate")

    def test_independent_formal_publication_survives_repository_copy(self):
        p = {**self.formal, "doi": "10.5281/zenodo.1", "resource_metadata_type": "dataset"}
        p = v2.annotate(p, "formal", self.venues, self.policy)
        self.assertEqual(p["resource_type"], "journal_article")
        self.assertEqual(p["recommendation"]["bucket"], "water")
        self.assertEqual(p["venue"], "Test Journal")

    def test_arxiv_without_journal_is_kept_and_water_requires_journal(self):
        p = {**paper(title="Vehicle object detection"), "assessment": {"level": "high"}}
        p = v2.annotate(p, "arxiv", self.venues, self.policy)
        self.assertEqual(p["resource_type"], "preprint")
        self.assertEqual(p["recommendation"]["bucket"], "land")
        conference = {**self.formal, "venue": "CVPR", "venue_type": "conference",
                      "publication_evidence": {"source": "Crossref", "type": "proceedings-article", "url": "https://example.test"}}
        p = v2.annotate(conference, "conf", self.venues, self.policy)
        self.assertTrue(p["quality"]["ccf_a"])
        self.assertEqual(p["recommendation"]["bucket"], "candidate")

    @patch.object(validity, "request")
    def test_deleted_restricted_transient_and_missing_are_distinct(self, request):
        p = {"doi": "10.5281/zenodo.23267832"}
        cases = [(410, '{"message":"The record has been deleted."}', "deleted"),
                 (403, "", "restricted"), (429, "", "restricted"), (500, "", "temporary"), (404, "", "temporary")]
        for code, body, expected in cases:
            request.return_value = (code, "https://zenodo.org/api/records/23267832", body)
            self.assertEqual(validity.check_record(p)["status"], expected)
        request.side_effect = TimeoutError()
        self.assertEqual(validity.check_record(p)["status"], "temporary")

    def test_withdrawn_excluded_but_timeout_does_not_clear_reading_or_translation(self):
        for status, bucket in [("withdrawn", "candidate"), ("temporary", "water"), ("restricted", "water")]:
            p = copy.deepcopy(self.formal)
            p.update(validity={"status": status}, reading={"state": "已精读", "analysis": "keep"}, translation={"status": "manual", "zh": "保留"})
            before = copy.deepcopy(p)
            v2.annotate(p, "test", self.venues, self.policy)
            self.assertEqual(p["recommendation"]["bucket"], bucket)
            for key in ("reading", "translation"):
                self.assertEqual(p[key], before[key])

    @patch.object(validity, "request", return_value=(200, "https://example.test", "{}"))
    def test_explicit_retraction_and_invalid_state_survives_timeout(self, request):
        self.assertEqual(validity.check_record({**self.formal, "is_retracted": True})["status"], "withdrawn")
        library = {"papers": {"p": {**self.formal, "validity": {"status": "deleted", "checked_at": "2020-01-01T00:00:00+00:00"}}}}
        request.side_effect = TimeoutError()
        validity.verify_records(library, ["p"], force=True)
        self.assertEqual(library["papers"]["p"]["validity"]["status"], "deleted")
        self.assertEqual(library["papers"]["p"]["validity"]["last_attempt"]["status"], "temporary")

    @patch.object(validity, "request", return_value=(200, "https://zenodo.org/api/records/1", json.dumps({"metadata": {"resource_type": {"type": "dataset"}, "access_right": "restricted"}})))
    def test_accessible_record_can_be_restricted_dataset(self, request):
        p = {"doi": "10.5281/zenodo.1"}
        self.assertEqual(validity.check_record(p)["status"], "accessible")
        self.assertEqual(validity.resource_type(p), "dataset")
        self.assertEqual(p["resource_access"], "restricted")


if __name__ == "__main__":
    unittest.main()
