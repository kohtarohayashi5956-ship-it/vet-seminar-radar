# -*- coding: utf-8 -*-
"""Regression coverage for bounded official-detail collection and diagnostics."""
import datetime
import unittest
from unittest.mock import patch

from gakusai_enrich import enrich_gakusai, parse_gakusai


class FakeFetcher:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return "<html><body><p>No schedule published yet</p></body></html>"


def event(number, date="2027-01-24"):
    return {
        "title": "検証用講習",
        "start_date": date,
        "url": f"https://www.gakusai.co.jp/vet/vet-seminar/{number}/",
        "format": None,
        "price": None,
        "start_time": None,
    }


class GakusaiBacklogTests(unittest.TestCase):
    def test_bounded_crawl_reports_deferred_unique_urls(self):
        items = [event(35591 + i) for i in range(15)]
        # A duplicate link must not create another fetch or count as backlog.
        items.append(event(35591))
        fetcher, stats = FakeFetcher(), {}
        with patch("gakusai_enrich.LIMIT", 12):
            result = enrich_gakusai(items, fetcher, datetime.date(2026, 11, 14), stats)
        self.assertIs(result, items)
        self.assertEqual(stats["detail_candidates"], 15)
        self.assertEqual(stats["details_scanned"], 12)
        self.assertEqual(stats["detail_deferred"], 3)
        self.assertEqual(len(fetcher.urls), 12)
        self.assertEqual(len(set(fetcher.urls)), 12)

    def test_robots_or_network_failure_is_never_filled_by_guess(self):
        class Denied:
            def get(self, url):
                raise PermissionError("detail page not available")

        items = [event(35591)]
        stats = {}
        enrich_gakusai(items, Denied(), datetime.date(2026, 11, 14), stats)
        self.assertEqual(stats["detail_fetch_failed"], 1)
        self.assertEqual(stats["detail_deferred"], 0)
        self.assertIsNone(items[0]["price"])
        self.assertIsNone(items[0]["start_time"])

    def test_no_upcoming_detail_links_has_zero_backlog(self):
        items = [event(35591, "2026-10-01")]
        stats = {}
        fetcher = FakeFetcher()
        enrich_gakusai(items, fetcher, datetime.date(2026, 11, 14), stats)
        self.assertEqual(stats["detail_candidates"], 0)
        self.assertEqual(stats["detail_deferred"], 0)
        self.assertEqual(fetcher.urls, [])


    def test_ambiguous_same_day_sessions_not_assigned(self):
        source = (
            "開催日時・会場\\n"
            "2027年1月24日 東京会場 10:00～12:00\\n"
            "2027年1月24日 大阪会場 14:00～16:00\\n"
            "来場受講料\\n"
            "一般獣医師 9,000円\\n"
        )
        self.assertEqual(parse_gakusai(source, event(35591)), {})

    def test_conflicting_end_time_not_overwritten(self):
        source = (
            "開催日時・会場\\n"
            "2027年1月24日 東京会場 10:00～12:00\\n"
            "来場受講料\\n"
            "一般獣医師 9,000円\\n"
        )
        item = event(35591)
        item["end_time"] = "13:00"
        parsed = parse_gakusai(source, item)
        self.assertNotIn("end_time", parsed)
        self.assertEqual(parsed.get("start_time"), "10:00")

    def test_unique_same_day_session_still_fills_time(self):
        source = (
            "開催日時・会場\\n"
            "2027年1月24日 東京会場 10:00～12:00\\n"
            "来場受講料\\n"
            "一般獣医師 9,000円\\n"
        )
        result = parse_gakusai(source, event(35591))
        self.assertEqual(result.get("start_time"), "10:00")
        self.assertEqual(result.get("end_time"), "12:00")


if __name__ == "__main__":
    unittest.main()
