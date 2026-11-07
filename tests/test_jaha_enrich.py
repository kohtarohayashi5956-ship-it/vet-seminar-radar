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
    def test_jaha_explicit_tiered_fees_on_date_matched_course(self):
        out = parse_jaha_detail(PAGE, event())
        self.assertEqual(
            out["price"],
            "通常受講:一般料金19,800円、JAHA会員16,500円"
        )
        self.assertNotIn("is_free", out)
        self.assertEqual(out["deadline"], "2026-11-04")
        self.assertEqual(out["start_time"], "14:00")
        self.assertEqual(out["end_time"], "17:00")

    def test_jaha_fee_table_with_split_labels_and_cell_rows(self):
        page = (
            "2026年11月7日 開催\n"
            "受講料・お申込み <https://www.jaha.or.jp/#fee>\n"
            "受講料(税込)\n"
            "JAHA会員\n会員外一般\n学生\n"
            "申し込み区分\nオンライン受講料金\n"
            "全5回一括\n19,800円\n27,500円\n"
            "単回申込\n4,950円\n7,150円\n"
            "お申込み\n"
        )
        out = parse_jaha_detail(page, event())
        self.assertIn("19,800円", out["price"])
        self.assertIn("27,500円", out["price"])
        self.assertNotIn("is_free", out)

    def test_jaha_fee_navigation_only_is_not_a_fee_section(self):
        page = (
            "2026年11月7日 開催\n"
            "受講料・お申込 <https://www.jaha.or.jp/#fees>\n"
            "キャンセル規定\n手数料1,000円\n"
        )
        out = parse_jaha_detail(page, event())
        self.assertNotIn("price", out)

    def test_jaha_fee_cannot_capture_cancellation_after_heading(self):
        page = (
            "2026年11月7日 開催\n"
            "受講料（税込）\n"
            "本講座の料金はお問い合わせください\n"
            "キャンセル規定\n手数料1,000円\n"
        )
        out = parse_jaha_detail(page, event())
        self.assertNotIn("price", out)

    def test_jaha_fee_requires_matching_course_date(self):
        self.assertEqual(parse_jaha_detail(PAGE, event("2026-11-08")), {})

    def test_jaha_fee_not_from_cancellation_or_unlabelled_money(self):
        text = ("2026年11月7日 14:00〜17:00 開催\n"
                "キャンセル手数料:1,000円\n"
                "一般 50,000円\n")
        out = parse_jaha_detail(text, event())
        self.assertNotIn("price", out)

    def test_jaha_mixed_free_and_paid_is_not_free(self):
        text = ("2026年11月7日 14:00〜17:00 開催\n"
                "受講料\n会員無料\n一般10,000円\n"
                "お申し込み\n")
        out = parse_jaha_detail(text, event())
        self.assertEqual(out["price"], "一般10,000円")
        self.assertNotIn("is_free", out)

    def test_jaha_explicit_inline_paid_fee(self):
        text = ("2026年11月7日 14:00〜17:00 開催\n"
                "受講料：会員5,000円、一般8,000円\n")
        result = parse_jaha_detail(text, event())
        self.assertEqual(result["price"], "会員5,000円、一般8,000円")
        self.assertNotIn("is_free", result)

    def test_jaha_existing_fee_preserved(self):
        item = event()
        item["price"] = "既存の料金区分"
        out = parse_jaha_detail(PAGE, item)
        self.assertNotIn("price", out)

    def test_jaha_explicit_free_without_paid_tier(self):
        text = ("2026年11月7日 14:00〜17:00 開催\n"
                "参加費:無料\n"
                "申込期限:2026年11月6日\n")
        out = parse_jaha_detail(text, event())
        self.assertEqual(out["price"], "無料")
        self.assertTrue(out["is_free"])

    def test_registration_range_start_and_explicit_end(self):
        self.assertEqual(parse_jaha_detail(PAGE,event()), {
            "deadline": "2026-11-04",
            "price": "通常受講:一般料金19,800円、JAHA会員16,500円",
            "start_time": "14:00",
            "end_time": "17:00",
        })

    def test_multi_session_course_second_date_gets_own_time(self):
        result = parse_jaha_detail(PAGE, event("2026-11-14"))
        self.assertEqual(result["start_time"], "14:00")
        self.assertEqual(result["end_time"], "17:00")
        self.assertEqual(result["price"], "通常受講:一般料金19,800円、JAHA会員16,500円")

    def test_multi_session_time_not_taken_from_registration(self):
        page = (
            "2026年11月7日、11月14日に配信\n"
            "受付期間：2026年11月14日 14:00〜17:00\n"
        )
        self.assertEqual(parse_jaha_detail(page, event("2026-11-14")), {})

    def test_multi_session_time_requires_explicit_year_anchor(self):
        page = (
            "11月7日、11月14日に配信\n"
            "パート2 11月14日 14:00〜17:00\n"
        )
        self.assertEqual(parse_jaha_detail(page, event("2026-11-14")), {})

    def test_multi_session_no_cross_year_inference(self):
        page = (
            "2026年12月28日、1月4日に配信\n"
            "パート2 1月4日 14:00〜17:00\n"
        )
        self.assertEqual(parse_jaha_detail(page, event("2027-01-04")), {})

    def test_multi_session_reject_conflicting_times(self):
        page = (
            "2026年11月7日、11月14日に配信\n"
            "パート2 11月14日 14:00〜17:00\n"
            "パート2 11月14日 16:00〜19:00\n"
        )
        out = parse_jaha_detail(page, event("2026-11-14"))
        self.assertNotIn("start_time", out)
        self.assertNotIn("end_time", out)

    def test_explicit_single_date_schedule_times(self):
        text = ("2026年11月7日 14:00〜17:00 開催\n"
                "受付期間：2026年9月7日～11月4日")
        self.assertEqual(
            parse_jaha_detail(text, event()),
            {"deadline": "2026-11-04", "start_time": "14:00", "end_time": "17:00"}
        )

    def test_multiple_schedule_dates_do_not_assign_times(self):
        text = ("2026年11月7日 / 11月14日 14:00〜17:00\n"
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
        text = ("2026年11月7日開催\n"
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
        self.assertEqual(stats["fee_label_pages"], 1)
        self.assertEqual(stats["fee_amount_pages"], 1)
        self.assertEqual(stats["fee_parsed_pages"], 1)
        self.assertEqual(stats["fee_detail_checks"][0]["path"],
                         "/owners/dog-training/kougi3ol/")
        self.assertTrue(stats["fee_detail_checks"][0]["fee_section"])
        self.assertIn("2026-11-07",
                      stats["fee_detail_checks"][0]["corroborated_dates"])

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
