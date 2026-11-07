# -*- coding: utf-8 -*-
"""JAHA seminar deadline: never mistake registration start or cancellation date."""
import datetime
import unittest
from jaha_enrich import parse_jaha_detail, enrich_jaha, _url

DATE=datetime.date(2026,11,6)
URL="https://www.jaha.or.jp/owners/dog-training/kougi3ol/"
PAGE = """
講義３【オンライン】
２０２６年１１月７日（土曜日）１１月１４日（土曜日）の２回に分けて配信
パート１ １１月７日（土曜日）14:00-17:00
パート２ １１月１４日（土曜日）14:00-17:00
受講料
通常受講：一般料金19,800円、JAHA会員16,500円
お申し込み
オンライン申込
受付期間：2026年9月7日～11月4日（水）17：00
キャンセル規定
URL送信前のキャンセルは手数料1,000円
"""

def event(day="2026-11-07",url=URL):
    return {"title":"家庭犬のしつけ方講座インストラクター養成コース講義３",
            "start_date":day,"url":url,"deadline":None}

class Fake:
    def __init__(self,html=PAGE): self.html=html;self.calls=[]
    def get(self,url):
        self.calls.append(url)
        return "<main><p>"+self.html.replace("\n","</p><p>")+"</p></main>"

class TestJahaDeadlines(unittest.TestCase):
    def test_registration_range_start_and_explicit_end(self):
        self.assertEqual(parse_jaha_detail(PAGE,event()),{"deadline":"2026-11-04"})

    def test_explicit_single_date_schedule_times(self):
        text = ("2026年11月7日 14:00〜17:00 開催\\n"
                "受付期間：2026年9月7日～11月4日")
        self.assertEqual(
            parse_jaha_detail(text, event()),
            {"deadline": "2026-11-04", "start_time": "14:00", "end_time": "17:00"}
        )

    def test_multiple_schedule_dates_do_not_assign_times(self):
        text = ("2026年11月7日 / 11月14日 14:00〜17:00\\n"
                "受付期間：2026年9月7日～11月4日")
        result = parse_jaha_detail(text, event())
        self.assertNotIn("start_time", result)
        self.assertNotIn("end_time", result)

    def test_conflicting_existing_start_time_not_overwritten(self):
        text = "2026年11月7日 14:00〜17:00 開催"
        item = event()
        item["start_time"] = "15:00"
        result = parse_jaha_detail(text, item)
        self.assertNotIn("start_time", result)
        self.assertNotIn("end_time", result)

    def test_registration_time_not_mistaken_for_course_time(self):
        text = ("2026年11月7日開催\\n"
                "受付期間：2026年9月7日～11月4日 14:00〜17:00")
        result = parse_jaha_detail(text, event())
        self.assertNotIn("start_time", result)

    def test_no_dates_from_unrelated_section(self):
        line="受付期間：2026年9月7日～11月4日（水）17:00"
        self.assertEqual(parse_jaha_detail(line,event()),{})

    def test_conflicting_program_date_not_accepted(self):
        self.assertEqual(parse_jaha_detail(PAGE,event("2026-11-15")),{})

    def test_registration_has_no_inferred_year(self):
        text="2026年11月7日開催\n受付期間：9月7日～11月4日"
        self.assertEqual(parse_jaha_detail(text,event()),{})

    def test_payment_and_cancellation_not_deadline(self):
        text=("2026年11月7日開催\nキャンセル締切：2026年11月4日\n"
              "お振込期限：2026年11月3日")
        self.assertEqual(parse_jaha_detail(text,event()),{})

    def test_one_fetch_per_url(self):
        f=Fake()
        rows=[event(),event()]
        stats={}
        enrich_jaha(rows,f,DATE,stats)
        self.assertEqual(f.calls,[URL])
        self.assertEqual([x["deadline"] for x in rows],
                         ["2026-11-04","2026-11-04"])
        self.assertEqual(stats["details_scanned"],1)

    def test_robots_failure_preserves_existing_data(self):
        class Blocked:
            def get(self,url): raise RuntimeError("robots prohibited")
        row=event();stats={}
        enrich_jaha([row],Blocked(),DATE,stats)
        self.assertEqual(stats["detail_fetch_failed"],1)
        self.assertIsNone(row["deadline"])

    def test_page_only_and_foreign_links_excluded(self):
        self.assertIsNone(_url(event(url="https://www.jaha.or.jp/seminar-calendar/top/")))
        self.assertIsNone(_url(event(url="https://not-jaha.or.jp/owners/dog-training/kougi3ol/")))

    def test_other_jaha_registration_range(self):
        text=("こいぬこねこの教育アドバイザー養成講座\n"
              "2026年11月1日（日）第2回\n"
              "受付期間：2026年7月24日～9月24日（木）17：00締切")
        self.assertEqual(parse_jaha_detail(text,event("2026-11-01")),
                         {"deadline":"2026-09-24"})

if __name__=="__main__":
    unittest.main()
