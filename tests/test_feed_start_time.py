# -*- coding: utf-8 -*-
"""Conservative VETS TECH start time evidence tests."""
import datetime
import unittest

from free_extract import _feed, _feed_explicit_start_time


class FeedStartTimeTests(unittest.TestCase):
    def test_labelled_single_time_with_full_year_date(self):
        self.assertEqual(_feed_explicit_start_time(
            "開催日時：2026年11月26日（木）21:00開始\n申込締切：当日17:30",
            "2026-11-26"), "21:00")

    def test_labelled_single_time_with_month_day(self):
        self.assertEqual(_feed_explicit_start_time(
            "日時：11月26日（木）21：00\n受付締切：当日17:30",
            "2026-11-26"), "21:00")

    def test_mismatched_date_rejected(self):
        self.assertIsNone(_feed_explicit_start_time(
            "日時：2026年11月27日 21:00", "2026-11-26"))

    def test_deadline_time_is_not_event_start(self):
        self.assertIsNone(_feed_explicit_start_time(
            "開催日時：2026年11月26日\n申込締切：当日17:30",
            "2026-11-26"))

    def test_cancellation_and_recording_expiry_not_start(self):
        self.assertIsNone(_feed_explicit_start_time(
            "開催日時：2026年11月26日\n視聴期限：21:00",
            "2026-11-26"))

    def test_multiple_times_are_not_guessed(self):
        self.assertIsNone(_feed_explicit_start_time(
            "日時：2026年11月26日 13:00～17:00",
            "2026-11-26"))

    def test_feed_integration_single_time(self):
        feed = (
            "=====\n"
            "記事タイトル: 【ライブ】慢性腸症セミナー\n"
            "記事URL: <https://vets-tech.jp/2026/11/01/example/12345/>\n"
            "公開日: 2026-11-01\n"
            "開催日時：2026年11月26日（木）21:00開始\n"
            "申込締切：当日17:30\n"
        )
        events = _feed(feed, "https://vets-tech.jp/feed/",
                       datetime.date(2026, 11, 10))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["start_date"], "2026-11-26")
        self.assertEqual(events[0]["start_time"], "21:00")
        self.assertEqual(events[0]["deadline"], "2026-11-26")


if __name__ == "__main__":
    unittest.main()
