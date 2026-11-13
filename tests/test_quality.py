import unittest

from quality import FIELDS, summarize_quality, summarize_quality_by_source


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

    def test_source_quality_groups_are_exact_and_not_double_counted(self):
        rows = [
            {"source_id": "jaha", "start_date": "2026-11-11", "price": "10,000円", "venue": None},
            {"source_id": "jaha", "start_date": "2026-12-01", "price": None, "venue": "東京"},
            {"source_id": "jbvp", "start_date": "2027-03-01", "price": None, "venue": "京都"},
        ]
        got = summarize_quality_by_source(rows)
        self.assertEqual(list(got), ["jaha", "jbvp"])
        self.assertEqual(got["jaha"]["total"], 2)
        self.assertEqual(got["jaha"]["field_presence"]["price"], 1)
        self.assertEqual(got["jaha"]["field_presence_pct"]["price"], 50.0)
        self.assertEqual(got["jbvp"]["field_presence"]["venue"], 1)
        self.assertEqual(got["jbvp"]["field_presence_pct"]["venue"], 100.0)

    def test_empty_list(self):
        result = summarize_quality([])
        self.assertEqual(result["total"], 0)
        self.assertEqual(set(result["field_presence"]), set(FIELDS))
        self.assertTrue(all(x == 0 for x in result["field_presence"].values()))
        self.assertTrue(all(x == 0.0 for x in result["field_presence_pct"].values()))

    def test_official_detail_url_is_detected_without_guessing_from_registration_link(self):
        from quality import _review_link_type
        event = {"source_id": "gakusai", "url": "https://www.gakusai.co.jp/doubutu/seminar-comingup/",
                 "detail_url": "https://www.gakusai.co.jp/vet/vet-seminar/35591/"}
        self.assertEqual(_review_link_type(event), "individual_detail")
        event["detail_url"] = "https://seminar.gakusai.co.jp/reservations/add?event_id=3151"
        self.assertEqual(_review_link_type(event), "listing_or_other")
        event["detail_url"] = "https://evil.example/vet/vet-seminar/35591/"
        self.assertEqual(_review_link_type(event), "listing_or_other")


if __name__ == "__main__":
    unittest.main()
