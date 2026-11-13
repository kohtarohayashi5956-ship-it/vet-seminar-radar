# -*- coding: utf-8 -*-
"""Annual JSVD certification is one year-round streamed course, not 6 fake lectures."""
import datetime
import unittest
from free_extract import extract_free

URL = "https://www.jsvd.jp/certifiedphysicians/certifiedphysician.html"
PAGE = """認定医制度について
日本獣医皮膚科学会 認定医講習
〖新制度の概要〗
配信期間：3月21日 ～ 翌年3月20日
内容更新：1年間で合計6講義を更新予定
受講料 ：年間一律 18,000円（中途返金不可）
申込時期：通年
次年度以降は自動更新
第15回 日本獣医皮膚科学会認定医試験
試験実施日 2026年10月18日
受験申請期間 2026年8月1日〜8月31日
"""


def extract(page=PAGE, url=URL, date=datetime.date(2026, 11, 13)):
    return extract_free("JSVD認定医講習", url, "", page, date, {})


class DermatologyCertificationTests(unittest.TestCase):
    def test_one_current_yearly_course(self):
        events = extract()
        self.assertEqual(len(events), 1)
        e = events[0]
        self.assertEqual(e["start_date"], "2026-03-21")
        self.assertEqual(e["end_date"], "2027-03-20")
        self.assertEqual(e["format"], "オンデマンド")
        self.assertEqual(e["price"], "年間一律 18,000円")
        self.assertEqual(e["deadline"], None)
        self.assertIsNone(e["start_time"])
        self.assertIsNone(e["end_time"])
        self.assertTrue(e["certification_note"])
        # The source is a general certification policy page, not an\n        # event-specific application page. Keep the review flag.\n        self.assertFalse(e["verified"])

    def test_year_rollover_before_and_after_march_21(self):
        a = extract(date=datetime.date(2027, 3, 20))[0]
        b = extract(date=datetime.date(2027, 3, 21))[0]
        self.assertEqual((a["start_date"], a["end_date"]),
                         ("2026-03-21", "2027-03-20"))
        self.assertEqual((b["start_date"], b["end_date"]),
                         ("2027-03-21", "2028-03-20"))

    def test_no_six_synthetic_lecture_cards(self):
        self.assertEqual(len(extract()), 1)

    def test_missing_price_rejected(self):
        self.assertEqual(extract(PAGE.replace("18,000円", "未定")), [])

    def test_missing_viewing_window_rejected(self):
        self.assertEqual(extract(PAGE.replace("翌年3月20日", "未定")), [])

    def test_wrong_url_rejected(self):
        self.assertEqual(extract(url="https://www.jsvd.jp/certifiedphysicians/other"), [])

    def test_exam_deadline_not_registration_deadline(self):
        e = extract()[0]
        self.assertIsNone(e["deadline"])
        self.assertEqual(e["end_date"], "2027-03-20")


if __name__ == "__main__":
    unittest.main()
