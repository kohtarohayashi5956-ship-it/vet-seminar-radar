# -*- coding: utf-8 -*-
"""JAHA three-part deep-dive bundled fees and signup dates."""
import unittest
from jaha_enrich import parse_jaha_detail, _deep3_fee_deadline

URL = "https://www.jaha.or.jp/training/seminar/vnseries/aigan26deep3/"
PAGE = """2026年度VNセミナー＜深掘りシリーズ＞
全3回が1セットのセミナーです
第1回：2026年12月7日（月）開催
第2回：2027年1月16日（土）開催
第3回：2027年2月23日（火）開催
《 セミナー開催日時 》
第1回：12月7日(月) 13:00～15:00
第2回：1月16日(土) 13:00～15:00
第3回：2月23日(火) 13:00～15:00
《 申込区分および受講料 》
参加区分 | JAHA会員料金 | 会員外料金
個人 申し込み（税込み） | 全3回分一括料金
8,250円 | 全3回分一括料金
14,850円
JAHA正会員 病院限定団体視聴
全3回分一括 団体視聴参加
40,755円
《 各区分での 申込受付期間 》
申し込み受付期間：2026年10月20日（火）13時～11月30日（月）15時まで
キャンセル規定
2026/12/1までの連絡はキャンセル料1,000円
"""

def event(date="2026-12-07",url=URL):
    return {"start_date":date,"url":url,"start_time":None,"end_time":None,
            "price":None,"deadline":None,"title":"VN緊急疾患シリーズ"}

class DeepDivePriceTests(unittest.TestCase):
    def test_bundled_tiers_and_deadline(self):
        for date in ("2026-12-07", "2027-01-16"):
            with self.subTest(date=date):
                result = parse_jaha_detail(PAGE,event(date))
                self.assertEqual(result.get("deadline"),"2026-11-30")
                self.assertIn("全3回一括",result.get("price",""))
                self.assertIn("JAHA会員 8,250円",result.get("price",""))
                self.assertIn("会員外 14,850円",result.get("price",""))
                self.assertIn("団体視聴 40,755円",result.get("price",""))

    def test_other_course_url_not_accepted(self):
        result = _deep3_fee_deadline(PAGE.splitlines(),event(
            url="https://www.jaha.or.jp/training/seminar/other/"))
        self.assertEqual(result,{})

    def test_wrong_date_not_accepted(self):
        self.assertEqual(_deep3_fee_deadline(
            PAGE.splitlines(),event("2026-12-08")),{})

    def test_cancellation_date_not_accepted(self):
        page = PAGE.replace("申し込み受付期間：2026年10月20日（火）13時～11月30日（月）15時まで",
                            "申込期間は未定")
        result = parse_jaha_detail(page,event())
        self.assertNotIn("deadline",result)

    def test_ambiguous_price_list_not_assigned(self):
        page = PAGE.replace("40,755円","40,755円\n追加受講 3,300円")
        result = _deep3_fee_deadline(page.splitlines(),event())
        self.assertNotIn("price",result)

if __name__=="__main__":
    unittest.main()
