# -*- coding: utf-8 -*-
"""Recorded JAHA puppy lectures must not be presented as live classes."""
import unittest
from jaha_enrich import parse_jaha_detail

URL = "https://www.jaha.or.jp/training/seminar/puppy/basic/"
PAGE = """2026年度開催スケジュール
第1回 | 10月1～7日 | オリエンテーション
第2回 | 11月1～7日 | 子犬の選び方
第3回 | 12月1～7日 | 子犬の困った行動
第4回 | 1月1～7日 | パピークラス
第5回 | 2月1～7日 | 子猫の困った行動
第6回 | 3月1～7日 | こねこ塾
第7回 | 3月10日（水）13-15時 | リアルタイム配信
第１回～第６回は録画配信
第７回のみZoomによるリアルタイム配信
"""


def event(date, title="ベーシックコース第3回", url=URL, fmt=None):
    return {"url": url, "start_date": date, "end_date": None,
            "title": title, "format": fmt, "price": None, "deadline": None,
            "start_time": None, "end_time": None}


class PuppyDeliveryTests(unittest.TestCase):
    def test_recording_for_the_three_future_rounds(self):
        for date, round_no in (("2026-12-01", 3), ("2027-01-01", 4),
                               ("2027-02-01", 5)):
            with self.subTest(round_no=round_no):
                out = parse_jaha_detail(PAGE, event(
                    date, f"こいぬこねこ教育アドバイザー ベーシックコース第{round_no}回"))
                self.assertEqual(out.get("format"), "オンデマンド")
                self.assertIsNone(out.get("start_time"))

    def test_round_seven_is_live_not_recorded(self):
        self.assertNotIn("format", parse_jaha_detail(
            PAGE, event("2027-03-10", "ベーシックコース第7回")))

    def test_different_url_cannot_use_statement(self):
        self.assertNotIn("format", parse_jaha_detail(
            PAGE, event("2026-12-01", url="https://www.jaha.or.jp/training/seminar/other/")))

    def test_wrong_date_cannot_borrow_neighbor(self):
        self.assertNotIn("format", parse_jaha_detail(
            PAGE, event("2026-12-02")))

    def test_missing_evidence_leaves_unclassified(self):
        page = PAGE.replace("第１回～第６回は録画配信", "")
        self.assertNotIn("format", parse_jaha_detail(
            page, event("2026-12-01")))

    def test_existing_delivery_format_kept(self):
        self.assertNotIn("format", parse_jaha_detail(
            PAGE, event("2026-12-01", fmt="オンデマンド")))


if __name__ == "__main__":
    unittest.main()
