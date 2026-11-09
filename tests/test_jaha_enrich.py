# -*- coding: utf-8 -*-
"""JAHA seminar deadline: never mistake registration start or cancellation date."""
import datetime
import unittest
from jaha_enrich import parse_jaha_detail, enrich_jaha, _url, _seniorcare_round_schedule

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

    def test_jaha_member_student_tiers_keep_correct_labels(self):
        page = (
            "2026年度開催スケジュール\n"
            "第3回 | 12月1～7日 | 子犬のケア\n"
            "受講料(税込)\n"
            "通常料金 | JAHA会員料金 | 学生料金\n"
            "一括申込 | 59,400円 | 52,800円 | 29,700円\n"
            "単回申込（再受講者向け） | 8,800円\n"
            "お申込み\n"
        )
        item = event("2026-12-01",
                     "https://www.jaha.or.jp/training/seminar/puppy/basic/")
        item["title"] = "ベーシックコース第3回"
        got = parse_jaha_detail(page, item)["price"]
        self.assertIn("一般 59,400円", got)
        self.assertIn("JAHA会員 52,800円", got)
        self.assertIn("学生 29,700円", got)
        self.assertIn("単回（再受講） 8,800円", got)

    def test_jaha_senior_care_fee_tiers_retain_one_off_and_series(self):
        page = (
            "2026年度 講座内容（全5回）\n"
            "第2回 | がんとケア | 12月9日 14:00-17:00\n"
            "受講料(税込)\n"
            "JAHA会員 | 会員外一般\n"
            "全5回一括 | 19,800円 | 27,500円\n"
            "単回申込 | 4,950円 | 7,150円\n"
            "お申込\n"
        )
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座・第2回"
        got = parse_jaha_detail(page, item)["price"]
        self.assertIn("全5回一括：JAHA会員 19,800円", got)
        self.assertIn("一般 27,500円", got)
        self.assertIn("単回：JAHA会員 4,950円", got)
        self.assertIn("一般 7,150円", got)

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

    def test_seniorcare_2026_numbered_course_matches_date_and_fees(self):
        page = (
            "2026年度 講座内容（全5回）\n"
            "第1回 | 老化に伴う行動の変化 | 2026年11月12日 14:00-16:30\n"
            "第2回 | 高齢動物のがんに関する知識\n"
            "12月9日（水）14:00-17:00\n"
            "第3回 | 整形疾患 | 2027年1月21日\n"
            "受講料(税込)\n"
            "JAHA会員\n会員外一般\n"
            "全5回一括\n19,800円\n27,500円\n"
            "単回申込\n4,950円\n7,150円\n"
            "お申込\n"
        )
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "【オンライン】動物病院スタッフのためのシニアケア講座・第２回"
        out = parse_jaha_detail(page, item)
        self.assertIn("19,800円", out["price"])
        self.assertNotIn("is_free", out)
        self.assertEqual(out["start_time"], "14:00")
        self.assertEqual(out["end_time"], "17:00")
        item["start_date"] = "2026-12-10"
        self.assertEqual(parse_jaha_detail(page, item), {})

    def test_seniorcare_explicit_single_session_signup_cutoff(self):
        page = (
            "2026年度 講座内容（全5回）\n"
            "第1回 | 老化に伴う行動変化 | 2026年11月12日 14:00-16:30\n"
            "第2回 | 高齢動物のがん | 12月9日 14:00-17:00\n"
            "受講料（税込）\n"
            "JAHA会員 19,800円\n"
            "単回申込の受付は、各回セミナー実施日の前日までとなります。\n"
        )
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "【オンライン】シニアケア講座 第2回"
        got = parse_jaha_detail(page, item)
        self.assertEqual(got["deadline"], "2026-12-08")

    def test_seniorcare_cutoff_not_assumed_without_policy_or_year(self):
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座 第2回"
        base = ("2026年度 講座内容（全5回）\n"
                "第2回 | 12月9日 14:00-17:00\n")
        self.assertNotIn("deadline", parse_jaha_detail(base, item))
        text = ("第2回 | 12月9日 14:00-17:00\n"
                "単回申込の受付は、各回セミナー実施日の前日までとなります。\n")
        self.assertNotIn("deadline", parse_jaha_detail(text, item))

    def test_seniorcare_cutoff_not_borrowed_for_other_course_or_round(self):
        page = ("2026年度 講座内容（全5回）\n"
                "第2回 | 12月9日 14:00-17:00\n"
                "単回申込の受付は、各回セミナー実施日の前日までとなります。\n")
        event_senior = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        event_senior["title"] = "シニアケア講座 第3回"
        self.assertNotIn("deadline", parse_jaha_detail(page, event_senior))
        event_other = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/puppy/basic/")
        event_other["title"] = "シニアケア講座 第2回"
        self.assertNotIn("deadline", parse_jaha_detail(page, event_other))

    def test_seniorcare_explicit_deadline_takes_priority(self):
        page = ("2026年度 講座内容（全5回）\n"
                "第2回 | 12月9日 14:00-17:00\n"
                "単回申込の受付は、各回セミナー実施日の前日までとなります。\n"
                "申込締切：2026年12月6日\n")
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座 第2回"
        self.assertEqual(parse_jaha_detail(page, item)["deadline"], "2026-12-06")

    def test_seniorcare_full_year_round_one_and_three_time_and_fee(self):
        page = (
            "2026年度 講座内容（全5回）\n"
            "第1回 | 老化に伴う行動変化 | 2026年11月12日(木) 14:00-16:30\n"
            "第2回 | 高齢動物のがん | 12月9日(水) 14:00-17:00\n"
            "第3回 | 整形疾患 | 2027年1月21日(木) 14:00-17:00\n"
            "受講料(税込)\n"
            "JAHA会員 | 会員外一般\n"
            "全5回一括 | 19,800円 | 27,500円\n"
            "単回申込 | 4,950円 | 7,150円\n"
        )
        for day, num, time_end in (
                ("2026-11-12", 1, "16:30"), ("2027-01-21", 3, "17:00")):
            item = event(day, "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
            item["title"] = f"【オンライン】シニアケア講座 第{num}回"
            got = parse_jaha_detail(page, item)
            self.assertEqual(got["start_time"], "14:00")
            self.assertEqual(got["end_time"], time_end)
            self.assertIn("19,800円", got["price"])
            self.assertIn("4,950円", got["price"])

    def test_seniorcare_round_date_no_neighbor_or_registration_borrowing(self):
        page = (
            "2026年度 講座内容（全5回）\n"
            "第1回 | 老化に伴う行動変化 | 2026年11月12日 14:00-16:30\n"
            "第2回 | 高齢動物のがん | 2026年12月9日 14:00-17:00\n"
            "申込締切：2027年1月21日 12:00\n"
        )
        item = event("2027-01-21",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座 第3回"
        self.assertEqual(parse_jaha_detail(page, item), {})

    def test_seniorcare_round_requires_printed_year_and_correct_round(self):
        page = ("2026年度 講座内容（全5回）\n"
                "第3回 | 整形疾患 | 1月21日 14:00-17:00\n")
        item = event("2027-01-21",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座 第3回"
        # The new *strict* fallback must not fill a shorthand year.
        # Existing numbered-schedule logic independently allows year
        # resolution from the 2026年度 course heading and remains unchanged.
        self.assertIsNone(_seniorcare_round_schedule(page.splitlines(), item))
        item["title"] = "シニアケア講座 第2回"
        self.assertIsNone(_seniorcare_round_schedule(page.splitlines(), item))

    def test_numbered_course_time_does_not_borrow_neighboring_round(self):
        page = ("2026年度 講座内容（全5回）\n"
                "第1回 | 老化に伴う行動の変化 | 2026年11月12日 14:00-16:30\n"
                "第2回 | がんとケア\n"
                "12月9日（水）\n"
                "第3回 | 整形疾患 | 2027年1月21日 14:00-17:00\n")
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座 第2回"
        out = parse_jaha_detail(page, item)
        self.assertNotIn("start_time", out)
        self.assertNotIn("end_time", out)

    def test_numbered_course_time_must_not_use_registration_clock(self):
        page = ("2026年度 講座内容（全5回）\n"
                "第2回 | がんとケア\n"
                "12月9日（水）\n"
                "申込締切:2026年12月9日 14:00-17:00\n")
        item = event("2026-12-09",
                     "https://www.jaha.or.jp/training/seminar/seniorcare_ol/")
        item["title"] = "シニアケア講座 第2回"
        out = parse_jaha_detail(page, item)
        self.assertNotIn("start_time", out)
        self.assertNotIn("end_time", out)

    def test_puppy_2026_2027_numbered_course_rollover(self):
        page = (
            "2026年度開催スケジュール\n"
            "第2回 | 11月1～7日 | 子犬の選び方\n"
            "第3回 | 12月1～7日 | 困った行動\n"
            "第4回 | 1月1～7日 | パピークラス\n"
            "受講料(税込)\n"
            "通常料金 | JAHA会員料金 | 学生料金\n"
            "一括申込 | 59,400円 | 52,800円 | 29,700円\n"
            "単回申込 | 8,800円\n"
            "お申込み\n"
        )
        item = event("2026-12-01",
                     "https://www.jaha.or.jp/training/seminar/puppy/basic/")
        item["title"] = "こいぬこねこの教育アドバイザー養成講座ベーシックコース第3回"
        self.assertIn("59,400円", parse_jaha_detail(page, item)["price"])
        item["start_date"], item["title"] = "2027-01-01", (
            "こいぬこねこの教育アドバイザー養成講座ベーシックコース第4回")
        self.assertIn("59,400円", parse_jaha_detail(page, item)["price"])
        item["start_date"] = "2026-01-01"
        self.assertEqual(parse_jaha_detail(page, item), {})

    def test_fee_skips_navigation_links_inside_valid_fee_section(self):
        page = ("2026年11月7日開催\n"
                "受講料\n"
                "（2回通し料金・税込）\n"
                "お知らせ <https://www.jaha.or.jp/info/>\n"
                "通常受講：一般料金19,800円、JAHA会員16,500円\n"
                "単発受講：会員18,700円／一般22,000円\n"
                "お申し込み\n"
                "キャンセル手数料1,000円\n")
        out = parse_jaha_detail(page, event())
        self.assertIn("19,800円", out["price"])
        self.assertIn("22,000円", out["price"])
        self.assertNotIn("1,000円", out["price"])

    def test_numbered_course_requires_matching_round_and_year(self):
        page = ("2026年度開催スケジュール\n"
                "第3回 | 12月1～7日 | 子犬\n"
                "受講料\n一括料金 50,000円\n")
        item = event("2026-12-01")
        item["title"] = "ベーシックコース第4回"
        self.assertEqual(parse_jaha_detail(page, item), {})
        item["title"] = "ベーシックコース第3回"
        item["start_date"] = "2027-12-01"
        self.assertEqual(parse_jaha_detail(page, item), {})

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

    def test_jaha_dog_lecture_full_course_and_single_price_tiers(self):
        text = (
            "講義３オンライン\n"
            "２０２６年１１月７日（土）１１月１４日（土）の２回に分けて配信\n"
            "パート１ １１月７日 14:00-17:00\n"
            "パート２ １１月１４日 14:00-17:00\n"
            "備考\n"
            "動物病院スタッフのみ単発受講可能\n"
            "受講料\n"
            "（２回通し料金・税込）\n"
            "通常受講：一般料金19,800円、JAHA会員16,500円、学生料金9,900円\n"
            "単発受講：一般料金22,000円、JAHA会員18,700円\n"
            "お申し込み\n"
        )
        for day in ("2026-11-07", "2026-11-14"):
            result = parse_jaha_detail(text, event(day))
            price = result["price"]
            self.assertIn("2回通し：一般 19,800円", price)
            self.assertIn("JAHA会員 16,500円", price)
            self.assertIn("学生 9,900円", price)
            self.assertIn("単発：一般 22,000円", price)
            self.assertIn("JAHA会員 18,700円", price)
            self.assertNotIn("is_free", result)

    def test_jaha_dog_lecture_does_not_use_just_the_note_fee(self):
        text = (
            "2026年11月7日 14:00-17:00 開催\n"
            "備考\n単発受講（会員18,700円／一般22,000円）\n"
            "受講料\n"
            "通常受講：一般料金19,800円、JAHA会員16,500円\n"
            "お申し込み\n"
        )
        got = parse_jaha_detail(text, event())
        self.assertNotIn("単発：", got.get("price", ""))

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

    def test_split_registration_heading_and_dated_value(self):
        page = ("2026年11月7日 14:00-17:00 開催\n"
                "受付期間\n"
                "2026年9月7日(月)～11月4日(水)17:00締切\n")
        self.assertEqual(parse_jaha_detail(page, event())["deadline"], "2026-11-04")

    def test_split_registration_deadline_full_year(self):
        page = ("2026年11月7日 14:00-17:00 開催\n"
                "お申込み締切\n"
                "2026年11月5日(木)\n")
        self.assertEqual(parse_jaha_detail(page, event())["deadline"], "2026-11-05")

    def test_split_registration_does_not_scan_next_section(self):
        page = ("2026年11月7日 14:00-17:00 開催\n"
                "受付期間\n"
                "お問い合わせ\n"
                "2026年11月1日(日)\n")
        self.assertNotIn("deadline", parse_jaha_detail(page, event()))

    def test_split_registration_rejects_cancellation_row(self):
        page = ("2026年11月7日 14:00-17:00 開催\n"
                "受付期間\n"
                "キャンセル期限 2026年11月1日(日)\n")
        self.assertNotIn("deadline", parse_jaha_detail(page, event()))

    def test_split_registration_no_inferred_year(self):
        page = ("2026年11月7日 14:00-17:00 開催\n"
                "受付期間\n"
                "11月1日(日)\n")
        self.assertNotIn("deadline", parse_jaha_detail(page, event()))

    def test_jaha_detail_rejects_userinfo_hostname(self):
        self.assertIsNone(_url(event(url="https://bad@example.com@www.jaha.or.jp/training/seminar/one/")))

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
