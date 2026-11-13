# -*- coding: utf-8 -*-
"""JAHA VN deep-dive live delivery requires an exact course date and section."""
import unittest
from jaha_enrich import parse_jaha_detail, _deep3_live_delivery

URL = "https://www.jaha.or.jp/training/seminar/vnseries/aigan26deep3/"
PAGE = """2026年度VNセミナー＜深掘りシリーズ＞
全3回が１セットのセミナー
第1回：2026年12月7日（月）開催
第2回：2027年1月16日（土）開催
第3回：2027年2月23日（火）開催
《 セミナー開催日時 》
第1回：12月7日(月) 13:00～15:00
第2回：1月16日(土) 13:00～15:00
第3回：2月23日(火) 13:00～15:00
《 配信形式 》
Zoomミーティングを使用したライブ配信
ウェブ会議アプリ「Zoom」を使って配信します。
《 見返し配信配信について 》
動画配信サービスを利用した見返し配信
"""

def event(date="2026-12-07", url=URL, fmt=None):
    return {"url": url, "start_date": date, "format": fmt,
            "title": "VNセミナー深掘りシリーズ緊急疾患・救急対応",
            "start_time": None, "end_time": None, "price": None, "deadline": None}


class DeepDiveLiveDeliveryTests(unittest.TestCase):
    def test_both_published_dates_are_live(self):
        for date in ("2026-12-07", "2027-01-16"):
            with self.subTest(date=date):
                self.assertEqual(parse_jaha_detail(PAGE, event(date)).get("format"),
                                 "ライブ配信")

    def test_wrong_date_not_classified(self):
        self.assertIsNone(_deep3_live_delivery(PAGE.splitlines(), event("2026-12-08")))

    def test_other_url_not_classified(self):
        self.assertIsNone(_deep3_live_delivery(PAGE.splitlines(), event(
            url="https://www.jaha.or.jp/training/seminar/vnseries/other/")))

    def test_replay_without_live_section_not_classified(self):
        page = PAGE.replace("Zoomミーティングを使用したライブ配信",
                            "録画配信")
        self.assertIsNone(_deep3_live_delivery(page.splitlines(), event()))

    def test_duplicate_delivery_heading_is_ambiguous(self):
        page = PAGE + "\n《 配信形式 》\n現地開催"
        self.assertIsNone(_deep3_live_delivery(page.splitlines(), event()))

    def test_existing_format_untouched(self):
        self.assertNotIn("format", parse_jaha_detail(
            PAGE, event(fmt="ライブ配信")))


if __name__ == "__main__":
    unittest.main()
