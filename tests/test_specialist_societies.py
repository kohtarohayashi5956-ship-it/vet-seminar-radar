# -*- coding: utf-8 -*-
"""Conservative official specialist-society date extraction."""
import datetime
import unittest
from free_extract import extract_free, _range_end

TODAY=datetime.date(2026,11,6)

class SocietyTests(unittest.TestCase):
    def test_javnu_future_meeting(self):
        text=("第19回 日本獣医腎泌尿器学会学術集会・総会\n"
              "会期：2027年8月21日（土）〜22日（日）\n"
              "会場：ベルサール飯田橋ファースト")
        ev=extract_free("JAVNU","https://www.javnu.jp/","",text,TODAY,{})
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["start_date"],"2027-08-21")
        self.assertEqual(ev[0]["end_date"],"2027-08-22")

    def test_jsvd_ignores_submission_deadline(self):
        text=("第30回 日本獣医皮膚科学会学術大会\n"
              "日程 | 2027 年 3 月 20 日（土）・21日（日）\n"
              "一般演題募集 | 2026 年 9 月 28 日 ～ 2027 年 1 月 8 日")
        ev=extract_free("日本獣医皮膚科学会","https://www.jsvd.jp/","",text,TODAY,{})
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["start_date"],"2027-03-20")
        self.assertEqual(ev[0]["end_date"],"2027-03-21")

    def test_jvcs_undated_next_meeting_is_omitted(self):
        text=("第35回日本獣医がん学会\n日 時：2027年1月30日(土)、31日(日)\n"
              "場 所：ホテルニューオータニ大阪\n"
              "第36回日本獣医がん学会\n日 時：2027年7月予定\n")
        ev=extract_free("日本獣医がん学会","https://www.jvcs.jp/society/","",text,TODAY,{})
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["start_date"],"2027-01-30")

    def test_jsvc_meeting(self):
        text=("第125回日本獣医循環器学会定例大会\n開催案内\n"
              "会期\n2026年12月19日（土）・20日（日）\n"
              "会場\nパピヨン24ガスホール")
        ev=extract_free("日本獣医循環器学会","https://www.jsvc.jp/meeting/regular/conf125/","",text,TODAY,{})
        self.assertEqual(len(ev),1)
        self.assertEqual(ev[0]["end_date"],"2026-12-20")

    def test_range_day(self):
        self.assertEqual(_range_end("2027年4月1日～6月30日","2027-04-01"),"2027-06-30")

if __name__=="__main__": unittest.main()
