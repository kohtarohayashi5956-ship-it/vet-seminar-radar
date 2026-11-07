import unittest

from quality import FIELDS, summarize_quality


class QualityTests(unittest.TestCase):
    def test_coverage_counts_after_deduplication(self):
        events = [
            {"start_date": "2026-12-01", "venue": "東京国際フォーラム", "topics": ["内科"], "price": None, "url": "https://example.org/a"},
            {"start_date": None, "topics": [], "price": "無料", "url": "https://example.org/b"},
        ]
        result = summarize_quality(events)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["field_presence"]["start_date"], 1)
        self.assertEqual(result["field_presence"]["topics"], 1)
        self.assertEqual(result["field_presence"]["venue"], 1)
        self.assertEqual(result["field_presence_pct"]["venue"], 50.0)
        self.assertEqual(result["field_presence"]["price"], 1)
        self.assertEqual(result["field_presence"]["url"], 2)
        self.assertEqual(result["field_presence_pct"]["start_date"], 50.0)
        self.assertEqual(result["field_presence_pct"]["url"], 100.0)

    def test_empty_list(self):
        result = summarize_quality([])
        self.assertEqual(result["total"], 0)
        self.assertEqual(set(result["field_presence"]), set(FIELDS))
        self.assertTrue(all(x == 0 for x in result["field_presence"].values()))
        self.assertTrue(all(x == 0.0 for x in result["field_presence_pct"].values()))


if __name__ == "__main__":
    unittest.main()
