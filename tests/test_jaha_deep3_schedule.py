# -*- coding: utf-8 -*-
import unittest
from jaha_enrich import parse_jaha_detail

URL = "https://www.jaha.or.jp/training/seminar/vnseries/aigan26deep3/"
PAGE = """2026年度VNセミナー 深掘りシリーズ
第1回：2026年12月7日（月）開催
第2回：2027年1月16日（土）開催
第3回：2027年2月23日（火）開催
《 セミナー開催日時 》
第1回： 12月7日(月) 13：00～15：00
第2回： 1月16日(土) 13：00～15：00
第3回： 2月23日(火) 13：00～15：00
《 配信形式 》
Zoom
申込受付期間：2026年10月20日13時～11月30日15時
"""

def event(date, url=URL):
    return {"url": url, "title": "2026年度VNセミナー緊急疾患・救急対応",
            "start_date": date, "start_time": None, "end_time": None,
            "deadline": None, "price": None}

class Deep3TimeTests(unittest.TestCase):
    def test_first_and_second_rounds(self):
        for date in ("2026-12-07", "2027-01-16"):
            with self.subTest(date=date):
                got = parse_jaha_detail(PAGE, event(date))
                self.assertEqual((got.get("start_time"), got.get("end_time")),
                                 ("13:00", "15:00"))

    def test_different_year_or_url_not_accepted(self):
        self.assertNotIn("start_time", parse_jaha_detail(PAGE, event("2026-01-16")))
        self.assertNotIn("start_time", parse_jaha_detail(PAGE, event(
            "2027-01-16", "https://www.jaha.or.jp/training/seminar/other/")))

    def test_duplicate_conflicting_time_rejected(self):
        page = PAGE.replace("《 配信形式 》",
                            "第1回： 12月7日(月) 09:00～11:00\n《 配信形式 》")
        self.assertNotIn("start_time", parse_jaha_detail(page, event("2026-12-07")))

    def test_registration_time_not_used(self):
        page = PAGE.replace("第1回： 12月7日(月) 13：00～15：00",
                            "第1回： 12月7日(月)")
        self.assertNotIn("start_time", parse_jaha_detail(page, event("2026-12-07")))

    def test_session_date_conflict_not_used(self):
        page = PAGE.replace("第1回： 12月7日(月) 13：00～15：00",
                            "第1回： 12月8日(火) 13：00～15：00")
        self.assertNotIn("start_time", parse_jaha_detail(page, event("2026-12-07")))

if __name__ == "__main__":
    unittest.main()
