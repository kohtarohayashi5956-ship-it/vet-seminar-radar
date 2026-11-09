# -*- coding: utf-8 -*-
"""Registration deadline evidence must be confined to its own field."""
import unittest

from free_extract import _explicit_deadline, _feed


class DeadlineEvidenceTests(unittest.TestCase):
    def test_date_same_line(self):
        self.assertEqual(
            _explicit_deadline("申込締切：2026年12月1日\n開催日時：2026年12月10日"),
            "2026-12-01",
        )

    def test_year_date_on_following_line(self):
        self.assertEqual(
            _explicit_deadline("申込締切：\n2026年12月1日\n開催日時：2026年12月10日"),
            "2026-12-01",
        )

    def test_event_date_following_empty_deadline_is_not_deadline(self):
        self.assertIsNone(
            _explicit_deadline("申込締切：\n開催日時：2026年12月10日"),
        )

    def test_explicit_same_day_signup_deadline(self):
        self.assertEqual(
            _explicit_deadline("日時：11月11日（水）21:00～22:30\n申込締切：当日17:30",
                               "2026-11-11"),
            "2026-11-11",
        )

    def test_same_day_requires_verified_event_date(self):
        self.assertIsNone(_explicit_deadline("申込締切：当日17:30"))
        self.assertIsNone(_explicit_deadline("申込締切：当日17:30", "2026-02-30"))

    def test_unlabelled_same_day_does_not_imply_deadline(self):
        self.assertIsNone(
            _explicit_deadline("開催日時：2026年11月11日\n当日17:30開場", "2026-11-11"),
        )

    def test_vets_tech_feed_article_same_day_deadline(self):
        # End-to-end feed regression: publication date is not event date,
        # but the explicitly stated event date anchors 当日.
        feed = (
            "=====\n"
            "記事タイトル: 【ライブ】腫瘍科医からみた慢性腸症治療のその先\n"
            "記事URL: <https://vets-tech.jp/2026/10/27/example/12345/>\n"
            "公開日: 2026-10-27\n"
            "日時：11月11日（水）21:00～22:30\n"
            "申込締切：当日17:30\n"
            "参加費：無料\n"
        )
        import datetime
        events = _feed(feed, "https://vets-tech.jp/feed/", datetime.date(2026, 11, 9))
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["start_date"], "2026-11-11")
        self.assertEqual(events[0]["deadline"], "2026-11-11")
        self.assertEqual(events[0]["price"], "無料")

    def test_signup_deadline_is_not_carried_to_next_article(self):
        import datetime
        feed = (
            "=====\n"
            "記事タイトル: 【ライブ】慢性腸症セミナー\n"
            "記事URL: <https://vets-tech.jp/2026/10/27/example/12345/>\n"
            "公開日: 2026-10-27\n"
            "開催日時：2026年11月11日 21:00\n"
            "申込締切：当日17:30\n"
            "=====\n"
            "記事タイトル: 【ライブ】次の眼科セミナー\n"
            "記事URL: <https://vets-tech.jp/2026/10/28/example/12346/>\n"
            "公開日: 2026-10-28\n"
            "開催日時：2026年11月12日 21:00\n"
        )
        events = _feed(feed, "https://vets-tech.jp/feed/", datetime.date(2026, 11, 9))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["deadline"], "2026-11-11")
        self.assertIsNone(events[1]["deadline"])

    def test_other_dates_not_deadlines(self):
        self.assertIsNone(
            _explicit_deadline("録画配信：2026年12月10日\nキャンセル期限：2026年12月1日"),
        )


if __name__ == "__main__":
    unittest.main()
