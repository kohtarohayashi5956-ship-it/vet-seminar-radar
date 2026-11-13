# -*- coding: utf-8 -*-
"""Format evidence and diagnostics for event delivery type."""
import unittest

from free_extract import _fmt
from quality import summarize_quality, summarize_review_candidates


class DeliveryFormatTests(unittest.TestCase):
    def test_explicit_face_to_face_in_title(self):
        self.assertEqual(_fmt("【対面】ボランティア講習会"), "現地")
        self.assertEqual(_fmt("［対面］看護実習"), "現地")

    def test_wet_lab(self):
        self.assertEqual(_fmt("整形外科 Wet Lab"), "現地")
        self.assertEqual(_fmt("整形外科 Wet & Dry Lab"), "現地")

    def test_no_unfounded_format_assumption(self):
        self.assertIsNone(_fmt("猫の歯科セミナー"))

    def test_ondemand_start_time_not_flagged(self):
        rows = [{"id": "a", "source_id": "jaha",
                 "format": "オンデマンド", "start_date": "2027-01-01",
                 "start_time": None, "price": "1000円",
                 "deadline": "2026-12-01", "url": "https://example.org/a"}]
        result = summarize_review_candidates(rows)
        jaha = result["source_summary"]["jaha"]
        self.assertEqual(jaha["missing"]["start_time"], 0)
        self.assertEqual(jaha["not_applicable"]["start_time"], 1)
        self.assertEqual(result["review_candidate_total"], 0)
        self.assertEqual(summarize_quality(rows)["field_presence"]["start_time"], 0)

    def test_unclassified_start_time_still_reviewed(self):
        rows = [{"id": "b", "source_id": "jaha",
                 "format": None, "start_date": "2027-01-01",
                 "start_time": None, "price": "1000円",
                 "deadline": "2026-12-01", "url": "https://example.org/b"}]
        result = summarize_review_candidates(rows)
        jaha = result["source_summary"]["jaha"]
        self.assertEqual(jaha["missing"]["start_time"], 1)
        self.assertEqual(jaha["missing"]["format"], 1)
        self.assertEqual(jaha["not_applicable"]["start_time"], 0)

    def test_format_coverage(self):
        rows = [{"format": "現地"}, {"format": None}, {"format": "オンデマンド"}]
        self.assertEqual(summarize_quality(rows)["field_presence"]["format"], 2)
        self.assertEqual(summarize_quality(rows)["field_presence_pct"]["format"], 66.7)


if __name__ == "__main__":
    unittest.main()
