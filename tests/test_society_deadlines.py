# -*- coding: utf-8 -*-
"""Do not confuse submission or exhibition deadlines with attendance deadlines."""
import datetime
import unittest
from free_extract import extract_free

NOW=datetime.date(2026,11,6)
PAGE="https://www.jsvd.jp/"

class SocietyDeadlineTests(unittest.TestCase):
    def test_only_symposium_attendance_deadline(self):
        text=(
          "第30回 日本獣医皮膚科学会学術大会\n"
          "日 程 | 2027 年 3 月 20 日（土）・21日（日）\n"
          "会 場 | TOC有明\n"
          "一般演題募集 | 2026 年 9 月 28 日（月）～2027 年 1 月 8 日（金）\n"
          "日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
          "犬と猫の皮膚真菌症 －検査と治療法について－\n"
          "日 程 | 2026 年 11 月 22 日（日）\n"
          "会 場 | 東京たま未来メッセ\n"
          "参加受付期間 | 2026 年 8 月 24 日（月）～ 11 月 22 日（日）15:00\n"
          "第30回 日本獣医皮膚科学会学術大会の演題募集終了\n")
        events=extract_free("日本獣医皮膚科学会",PAGE,"",text,NOW,{})
        by_date={e["start_date"]:e for e in events}
        self.assertEqual(len(events),2)
        self.assertIsNone(by_date["2027-03-20"]["deadline"])
        self.assertEqual(by_date["2026-11-22"]["deadline"],"2026-11-22")

    def test_reject_abstract_only(self):
        text=("第30回 日本獣医皮膚科学会学術大会\n"
              "日程 | 2027年3月20日・21日\n"
              "一般演題募集 | 2026年9月28日～2027年1月8日\n")
        e=extract_free("日本獣医皮膚科学会",PAGE,"",text,NOW,{})
        self.assertEqual(len(e),1)
        self.assertIsNone(e[0]["deadline"])

    def test_no_year_guess_or_other_event_leak(self):
        text=("日本医真菌学会・日本獣医皮膚科学会・ISHAM WG共催シンポジウム\n"
              "日程 | 2026年11月22日\n"
              "参加受付期間 | 8月24日～11月22日\n"
              "第30回 日本獣医皮膚科学会学術大会\n"
              "日程 | 2027年3月20日\n"
              "参加受付期間 | 2027年1月1日～3月1日\n")
        e=extract_free("日本獣医皮膚科学会",PAGE,"",text,NOW,{})
        self.assertEqual(len(e),2)
        self.assertIsNone([x for x in e if x["start_date"]=="2026-11-22"][0]["deadline"])

if __name__=="__main__":
    unittest.main()
