# -*- coding: utf-8 -*-
"""Upcoming published seminar completeness triage."""
import unittest

from quality import summarize_actionable_upcoming, summarize_quality


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

    def test_applicable_start_time_rate_ignores_recordings(self):
        events = [
            {"format": "オンデマンド", "start_time": None},
            {"format": "オンデマンド", "start_time": None},
            {"format": "ライブ配信", "start_time": "20:00"},
            {"format": "現地", "start_time": None},
        ]
        quality = summarize_quality(events)
        self.assertEqual(quality["field_presence_pct"]["start_time"], 25.0)
        self.assertEqual(
            quality["applicable_start_time"],
            {"eligible": 2, "known": 1, "pct": 50.0, "excluded_on_demand": 2},
        )

    def test_all_on_demand_has_no_live_time_denominator(self):
        result = summarize_quality([{"format": "オンデマンド"}])
        self.assertEqual(result["applicable_start_time"]["eligible"], 0)
        self.assertEqual(result["applicable_start_time"]["pct"], 0.0)

    def test_active_recording_started_earlier_is_included(self):
        items = [
            {"id": "active", "source_id": "javnu_cert",
             "start_date": "2026-10-01", "end_date": "2026-11-25",
             "format": "オンデマンド", "price": None, "deadline": None},
            {"id": "expired", "source_id": "javnu_cert",
             "start_date": "2026-10-01", "end_date": "2026-11-13",
             "format": "オンデマンド", "price": None, "deadline": None},
            {"id": "unconfirmed", "source_id": "javnu_cert",
             "start_date": "2026-10-01", "end_date": None,
             "format": "オンデマンド", "price": None, "deadline": None},
            {"id": "old_live", "source_id": "jaha",
             "start_date": "2026-10-01", "end_date": "2026-12-01",
             "format": "ライブ配信", "price": None},
        ]
        result = summarize_actionable_upcoming(items, "2026-11-14")
        self.assertEqual([row["id"] for row in result["events"]], ["active"])
        self.assertNotIn("start_time", result["events"][0]["missing"])
        self.assertEqual(result["events"][0]["review_date"], "2026-11-25")
        self.assertEqual(result["events"][0]["review_date_type"], "視聴期限")

    def test_live_session_precedes_long_running_recording(self):
        items = [
            {"id": "recorded", "start_date": "2026-10-01",
             "end_date": "2026-11-27", "format": "オンデマンド"},
            {"id": "live", "start_date": "2026-11-15",
             "format": "ライブ配信"},
        ]
        result = summarize_actionable_upcoming(items, "2026-11-14")
        self.assertEqual([row["id"] for row in result["events"]],
                         ["live", "recorded"])
        self.assertEqual(result["events"][0]["review_date_type"], "開催開始")

    def test_distant_recording_expiry_is_not_imminent(self):
        items = [
            {"id": "distant", "start_date": "2026-10-01",
             "end_date": "2027-03-01", "format": "オンデマンド"},
            {"id": "soon", "start_date": "2026-10-01",
             "end_date": "2026-11-28", "format": "オンデマンド"},
            {"id": "beyond", "start_date": "2026-10-01",
             "end_date": "2026-11-29", "format": "オンデマンド"},
        ]
        result = summarize_actionable_upcoming(items, "2026-11-14")
        self.assertEqual([row["id"] for row in result["events"]], ["soon"])

    def test_fully_documented_event_excluded(self):
        items = [{"id": "ok", "start_date": "2026-11-16",
                  "format": "ライブ配信", "price": "有料", "deadline": "2026-11-15",
                  "start_time": "20:00"}]
        self.assertEqual(summarize_actionable_upcoming(items, "2026-11-14")["total"], 0)


if __name__ == "__main__":
    unittest.main()
