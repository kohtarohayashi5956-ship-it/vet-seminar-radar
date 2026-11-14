# -*- coding: utf-8 -*-
"""Upcoming published seminar completeness triage."""
import unittest

from quality import summarize_actionable_upcoming


class UpcomingTriageTests(unittest.TestCase):
    def test_near_term_missing_fields_and_on_demand_applicability(self):
        events = [
            {"id": "live", "source_id": "jaha", "start_date": "2026-11-16",
             "format": "ライブ配信", "price": None, "deadline": None,
             "start_time": None},
            {"id": "recorded", "source_id": "javnu_cert", "start_date": "2026-11-17",
             "format": "オンデマンド", "price": None, "deadline": None,
             "start_time": None},
            {"id": "later", "source_id": "jaha", "start_date": "2027-02-01"},
            {"id": "unknown-date", "source_id": "vetstech", "start_date": None},
        ]
        result = summarize_actionable_upcoming(events, "2026-11-14")
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["by_source"], {"jaha": 1, "javnu_cert": 1})
        self.assertIn("start_time", result["events"][0]["missing"])
        self.assertNotIn("start_time", result["events"][1]["missing"])

    def test_both_end_dates_inclusive_and_missing_date_excluded(self):
        items = [
            {"id": "now", "start_date": "2026-11-14", "format": None},
            {"id": "last", "start_date": "2026-11-28", "format": None},
            {"id": "past", "start_date": "2026-11-13", "format": None},
            {"id": "future", "start_date": "2026-11-29", "format": None},
        ]
        result = summarize_actionable_upcoming(items, "2026-11-14")
        self.assertEqual([x["id"] for x in result["events"]], ["now", "last"])

    def test_fully_documented_event_excluded(self):
        items = [{"id": "ok", "start_date": "2026-11-16",
                  "format": "ライブ配信", "price": "有料", "deadline": "2026-11-15",
                  "start_time": "20:00"}]
        self.assertEqual(summarize_actionable_upcoming(items, "2026-11-14")["total"], 0)


if __name__ == "__main__":
    unittest.main()
