# -*- coding: utf-8 -*-
"""Require dated, event-specific schedule evidence for all VETS TECH times."""
import datetime
import unittest

from free_extract import _feed, _feed_schedule_times


class DatedScheduleTimesTests(unittest.TestCase):
    def test_single_start_unchanged(self):
        self.assertEqual(_feed_schedule_times(
            "開催日時：2026年11月26日（木）21:00開始\n申込締切：当日17:30",
            "2026-11-26"), ("21:00", None))

    def test_range_anchored_to_event_date(self):
        self.assertEqual(_feed_schedule_times(
            "申込受付時間：09:00～18:00\n開催日時：2026年11月26日（木）21：00～22：30",
            "2026-11-26"), ("21:00", "22:30"))

    def test_range_on_following_line(self):
        self.assertEqual(_feed_schedule_times(
            "開催日時：2026年11月26日\n21:00～22:30\n申込締切：当日17:30",
            "2026-11-26"), ("21:00", "22:30"))

    def test_date_on_following_line(self):
        self.assertEqual(_feed_schedule_times(
            "開催日時：\n2026年11月26日 21:00",
            "2026-11-26"), ("21:00", None))

    def test_only_deadline_and_registration_time(self):
        self.assertEqual(_feed_schedule_times(
            "開催日時：2026年11月26日\n申込締切：当日17:30\n受付時間：09:00～18:00",
            "2026-11-26"), (None, None))

    def test_different_event_date_rejected(self):
        self.assertEqual(_feed_schedule_times(
            "日時：2026年11月25日 21:00～22:30",
            "2026-11-26"), (None, None))

    def test_multiple_dated_sessions_not_collapsed(self):
        self.assertEqual(_feed_schedule_times(
            "日時：2026年11月26日 10:00～12:00、2026年11月27日 14:00～16:00",
            "2026-11-26"), (None, None))

    def test_several_independent_times_not_guessed(self):
        self.assertEqual(_feed_schedule_times(
            "日時：2026年11月26日 10:00、14:00",
            "2026-11-26"), (None, None))

    def test_feed_does_not_take_unrelated_early_range(self):
        feed = (
            "=====\n"
            "記事タイトル: 【ライブ】腫瘍学ウェビナー\n"
            "記事URL: <https://vets-tech.jp/2026/11/01/example/12345/>\n"
            "公開日: 2026-11-01\n"
            "申込受付時間：09:00～18:00\n"
            "開催日時：2026年11月26日（木）21:00～22:30\n"
        )
        events = _feed(feed, "https://vets-tech.jp/feed/",
                       datetime.date(2026, 11, 10))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["start_date"], "2026-11-26")
        self.assertEqual(events[0]["start_time"], "21:00")
        self.assertEqual(events[0]["end_time"], "22:30")


if __name__ == "__main__":
    unittest.main()
