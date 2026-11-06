# -*- coding: utf-8 -*-
"""VETS TECH news articles: schedule year, privacy and status regressions."""
import datetime
import unittest
from free_extract import extract_free, _feed_event_schedule

TODAY = datetime.date(2026, 11, 6)
FEED = "https://vets-tech.jp/feed/"


def article(title, url, pub, content):
    return (f"=====\n記事タイトル: {title}\n記事URL: <{url}>\n"
            f"公開日: {pub}\n{content}\n")


class VetstechScheduleTests(unittest.TestCase):
    def test_full_year_date_on_same_line_as_schedule(self):
        text = article(
            "【ライブ】慢性腸症治療のその先",
            "https://vets-tech.jp/2026/10/27/a/",
            "2026-10-27",
            "日時 2026年11月11日（水）21:00～22:30\n参加費 無料\n"
            "他のセミナーは満席\n",
        )
        got = extract_free("VETS TECH", FEED, "", text, TODAY, {})
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["start_date"], "2026-11-11")
        self.assertEqual(got[0]["format"], "ライブ配信")
        self.assertIsNone(got[0]["status"])
        self.assertTrue(got[0]["is_free"])

    def test_yearless_date_anchored_to_posting_year(self):
        text = article(
            "【ライブ】血液塗抹の作り方",
            "https://vets-tech.jp/2026/10/22/b/",
            "2026-10-22",
            "開催概要\n日時\n11月5日（木）21:00～22:30\n申込締切：当日17:30\n",
        )
        got = extract_free("VETS TECH", FEED, "", text, TODAY, {})
        self.assertEqual(got[0]["start_date"], "2026-11-05")

    def test_yearless_event_crosses_new_year(self):
        self.assertEqual(
            _feed_event_schedule("日時\n1月17日（日）13:00～16:00", "2026-11-04"),
            "2027-01-17",
        )

    def test_publication_date_and_deadline_not_event_date(self):
        text = article(
            "【ライブ】犬猫のセミナー",
            "https://vets-tech.jp/2026/10/27/c/",
            "2026-10-27",
            "開催日時は後日お知らせします\n申込締切：2026年11月2日\n",
        )
        got = extract_free("VETS TECH", FEED, "", text, TODAY, {})
        self.assertIsNone(got[0]["start_date"])

    def test_unrelated_free_text_is_not_registration_price(self):
        text = article(
            "【録画】眼科検査の動画セミナー",
            "https://vets-tech.jp/2026/09/29/d/",
            "2026-09-29",
            "アンケート回答者には資料を無料で配布します。\n"
            "満席の実習もおすすめです。\n",
        )
        got = extract_free("VETS TECH", FEED, "", text, TODAY, {})
        self.assertEqual(got[0]["format"], "オンデマンド")
        self.assertIsNone(got[0]["status"])
        self.assertIsNone(got[0]["is_free"])

if __name__ == "__main__":
    unittest.main()
