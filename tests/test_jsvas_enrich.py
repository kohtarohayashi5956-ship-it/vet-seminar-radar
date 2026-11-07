# -*- coding: utf-8 -*-
"""Only JSVAS course-specific official detail information is accepted."""
import datetime
import unittest
from jsvas_enrich import parse_jsvas_detail, enrich_jsvas

URL = "https://www.jsvas.net/lectures/chushikoku_261123.php"
TODAY = datetime.date(2026, 11, 7)

PAGE = """中国・四国地区講習会
事前申込｜定員100名（当日受付あり）
開催概要
日時
2026 年 11 月 23 日（月・祝） 10：00 〜 16：30
会場
岡山国際交流センター
参加費
本会会員・学生 無料
後援獣医師会会員 3,000円
上記会員以外の方 5,000円
パンフレット
参加登録
事前申込締切：2026 年 11 月 16 日（月）
プログラム
座学
10:10〜11:00
"""

def event(**kwargs):
    e = {"title":"2026年度 中国・四国地区講習会 血管作動薬",
         "start_date":"2026-11-23","url":URL,
         "start_time":None,"end_time":None,"price":None,
         "is_free":None,"deadline":None}
    e.update(kwargs)
    return e

class Fetcher:
    def __init__(self, text=PAGE):
        self.text=text
        self.calls=[]
    def get(self, url):
        self.calls.append(url)
        return "<main>" + "".join("<p>"+x+"</p>" for x in self.text.splitlines()) + "</main>"

class JSVASDetailTests(unittest.TestCase):
    def test_course_time_registration_deadline_and_tiered_price(self):
        result = parse_jsvas_detail(PAGE,event())
        self.assertEqual(result["start_time"],"10:00")
        self.assertEqual(result["end_time"],"16:30")
        self.assertEqual(result["deadline"],"2026-11-16")
        self.assertIn("3,000円",result["price"])
        self.assertIn("5,000円",result["price"])
        self.assertIn("無料",result["price"])
        self.assertNotIn("is_free",result)

    def test_exact_course_date_is_required(self):
        self.assertEqual(parse_jsvas_detail(PAGE,event(start_date="2026-11-22")),{})

    def test_announcement_and_registration_without_course_date(self):
        text="2026年11月23日 お知らせ\n事前申込締切：2026年11月16日"
        self.assertEqual(parse_jsvas_detail(text,event()),{})

    def test_multiple_schedules_are_rejected(self):
        text=PAGE+"\n日時\n2026年11月24日 09:00〜15:00"
        self.assertEqual(parse_jsvas_detail(text,event()),{})

    def test_existing_values_are_preserved(self):
        result=parse_jsvas_detail(PAGE,event(start_time="10:00", price="会員 1,000円",deadline="2026-11-12"))
        self.assertNotIn("start_time",result)
        self.assertNotIn("price",result)
        self.assertNotIn("deadline",result)
        self.assertEqual(result["end_time"],"16:30")

    def test_conflicting_start_time_not_overwritten(self):
        result=parse_jsvas_detail(PAGE,event(start_time="12:00"))
        self.assertNotIn("start_time",result)
        self.assertNotIn("end_time",result)

    def test_no_deadline_from_cancel_policy(self):
        page=PAGE.replace("事前申込締切：2026 年 11 月 16 日（月)","キャンセル期限：2026年11月16日")
        page=PAGE.replace("事前申込締切：2026 年 11 月 16 日（月）","キャンセル期限：2026年11月16日")
        self.assertNotIn("deadline",parse_jsvas_detail(page,event()))

    def test_fetch_once_and_reject_other_domain(self):
        f=Fetcher()
        rows=[event(),event(),event(url="https://evil.example/lectures/chushikoku_261123.php")]
        stats={}
        enrich_jsvas(rows,f,TODAY,stats)
        self.assertEqual(f.calls,[URL])
        self.assertEqual(stats["details_scanned"],1)
        self.assertEqual(stats["deadlines_found"],2)
        self.assertIsNone(rows[2]["deadline"])

    def test_blocked_fetch_preserves_original(self):
        class Blocked:
            def get(self,url):raise RuntimeError("robots denied")
        rows=[event()]
        status={}
        enrich_jsvas(rows,Blocked(),TODAY,status)
        self.assertIsNone(rows[0]["price"])
        self.assertEqual(status["detail_fetch_failed"],1)

if __name__ == "__main__":
    unittest.main()
