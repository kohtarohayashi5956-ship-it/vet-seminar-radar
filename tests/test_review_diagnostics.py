# -*- coding: utf-8 -*-
"""Review diagnostics reflect missing values, not unverified source claims."""
import unittest

from quality import summarize_review_candidates


class ReviewDiagnosticsTests(unittest.TestCase):
    def test_source_counts_and_link_evidence(self):
        rows = [
            {"id": "a", "source_id": "gakusai", "start_date": "2027-03-07",
             "start_time": None, "price": "1,000円", "deadline": None,
             "url": "https://www.gakusai.co.jp/vet/vet-seminar/35589/"},
            {"id": "b", "source_id": "gakusai", "start_date": "2027-07-18",
             "start_time": None, "price": None, "deadline": None,
             "url": "https://www.gakusai.co.jp/doubutu/seminar-comingup/"},
        ]
        result = summarize_review_candidates(rows)
        x = result["source_summary"]["gakusai"]
        self.assertEqual(x["total"], 2)
        self.assertEqual(x["missing"]["start_time"], 2)
        self.assertEqual(x["missing"]["price"], 1)
        self.assertEqual(x["missing_with_detail_link"]["start_time"], 1)
        self.assertEqual(x["missing_without_confirmed_detail_link"]["start_time"], 1)
        self.assertEqual(result["priority_review"][0]["id"], "a")
        self.assertEqual(result["priority_review"][0]["link_type"],
                         "individual_detail")

    def test_missing_date_is_high_priority(self):
        rows = [
            {"id": "dated", "source_id": "jaha", "start_date": "2027-01-01",
             "start_time": None, "url": "https://www.jaha.or.jp/training/seminar/a/"},
            {"id": "undated", "source_id": "other", "start_date": None,
             "url": "https://example.org/"},
        ]
        result = summarize_review_candidates(rows, limit=1)
        self.assertEqual(result["priority_review"][0]["id"], "undated")
        self.assertEqual(result["review_candidate_total"], 2)

    def test_non_source_data_is_not_exposed(self):
        result = summarize_review_candidates([
            {"id": "abc", "source_id": "jaha", "start_date": None,
             "title": "Personal title", "internal_notes": "secret",
             "url": "https://www.jaha.or.jp/training/seminar/course/"}
        ])
        priority = str(result["priority_review"])
        self.assertNotIn("Personal title", priority)
        self.assertNotIn("secret", priority)

    def test_empty_collection_and_clamped_limit(self):
        self.assertEqual(summarize_review_candidates([])["review_candidate_total"], 0)
        self.assertEqual(summarize_review_candidates([])["source_summary"], {})
        self.assertEqual(summarize_review_candidates([
            {"id": "a", "source_id": "jaha"}], limit=-1)["priority_review"], [])

    def test_unknown_source_never_claims_detail(self):
        result = summarize_review_candidates([
            {"id": "x", "source_id": "other", "start_date": "2027-01-01",
             "url": "https://example.org/event/123"}
        ])
        self.assertEqual(result["priority_review"][0]["link_type"], "unclassified")


if __name__ == "__main__":
    unittest.main()
