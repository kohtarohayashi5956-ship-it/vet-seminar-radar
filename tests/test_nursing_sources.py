# -*- coding: utf-8 -*-
"""JVNA and Dourinken official schedules; isolate registration and abstract dates."""
import datetime
import unittest
from free_extract import extract_free
from extract import html_to_text

TODAY=datetime.date(2026,11,7)
JVNA="https://www.jvna.or.jp/16thkangotaikai/"
DOURINKEN="https://dourinken.com/taikai/guide/"


class NursingCongressTests(unittest.TestCase):
    def test_jvna_congress_attendance_deadline_not_abstract(self):
        text=(
          "第16回 動物看護大会\n"
          "第16回 動物看護大会 概要・参加申込【事前登録制】\n"
          "開催日時\n2026年12月6日（日）10時～17時\n"
          "会場\n学校法人宮﨑学園\n大阪ペピイ動物看護専門学校\n"
          "参加費\n会員区分 実習なし 実習あり\n"
          "JVNA正会員 5,500円 8,800円\n"
          "JVNA準会員 8,800円 ―\n非会員 16,500円 ―\n"
          "申込期限\n2026年11月29日（日）まで\n"
          "動物看護研究演題募集（終了）\n"
          "■申込〆切\n2026年9月4日（金）12時\n"
          "■抄録〆切\n2026年10月23日（金）12時\n")
        ev=extract_free("日本愛玩動物看護師会",JVNA,"",text,TODAY,{})
        self.assertEqual(len(ev),1)
        e=ev[0]
        self.assertEqual(e["start_date"],"2026-12-06")
        self.assertEqual(e["start_time"],"10:00")
        self.assertEqual(e["end_time"],"17:00")
        self.assertEqual(e["venue"],"大阪ペピイ動物看護専門学校")
        self.assertEqual(e["deadline"],"2026-11-29")
        self.assertIn("5,500円",e["price"])
        self.assertIn("16,500円",e["price"])
        self.assertIsNone(e["abstract_deadline"])
        self.assertIsNone(e["is_free"])

    def test_jvna_never_substitutes_abstract_submission(self):
        text=("第16回 動物看護大会\n"
              "開催日時\n2026年12月6日\n"
              "動物看護研究演題募集（終了）\n申込〆切\n2026年9月4日\n")
        ev=extract_free("日本愛玩動物看護師会",JVNA,"",text,TODAY,{})
        self.assertEqual(len(ev),1)
        self.assertIsNone(ev[0]["deadline"])

    def test_jvna_does_not_infer_date_from_fee_or_registration(self):
        text=("第16回 動物看護大会\n会場\n大阪ペピイ動物看護専門学校\n"
              "申込期限\n2026年11月29日\n")
        self.assertEqual(extract_free("日本愛玩動物看護師会",JVNA,"",text,TODAY,{}),[])


class ClinicalMedicineMeetingTests(unittest.TestCase):
    def test_reiwa_next_year_is_2027_not_past_meeting(self):
        text=("学会案内\n"
              "第47回動物臨床医学会年次大会\n"
              "日 時:令和8年10月24日(土)、25日(日)\n"
              "会 場:大阪府立国際会議場〔グランキューブ大阪〕\n"
              "第47回動物臨床医学会年次大会 終了のご報告と御礼\n"
              "来年の御案内\n"
              "第48回動物臨床医学会年次大会\n"
              "日 時:令和9年10月30日(土)、31日(日)\n"
              "会 場:大阪府立国際会議場〔グランキューブ大阪〕\n"
              "開催概要\n一般口演\n症例検討\n"
              "大会期間中、認定医資格試験開催\n")
        ev=extract_free("動物臨床医学会",DOURINKEN,"",text,TODAY,{})
        self.assertEqual(len(ev),1)
        e=ev[0]
        self.assertEqual(e["start_date"],"2027-10-30")
        self.assertEqual(e["end_date"],"2027-10-31")
        self.assertEqual(e["venue"],"大阪府立国際会議場（グランキューブ大阪）")
        self.assertEqual(e["topics"],["学会・大会"])
        self.assertIsNone(e["deadline"])
        self.assertIsNone(e["abstract_deadline"])
        self.assertEqual(e["audience"],["獣医師","動物看護師","学生"])

    def test_no_future_meeting_from_old_47th(self):
        text=("第47回動物臨床医学会年次大会\n"
              "日 時:令和8年10月24日(土)、25日(日)\n"
              "会 場:大阪府立国際会議場\n")
        self.assertEqual(extract_free("動物臨床医学会",DOURINKEN,"",text,TODAY,{}),[])

    def test_new_notice_without_era_date_stays_empty(self):
        text=("来年の御案内\n"
              "第48回動物臨床医学会年次大会\n"
              "日 時:10月30日、31日\n"
              "会 場:大阪府立国際会議場\n")
        self.assertEqual(extract_free("動物臨床医学会",DOURINKEN,"",text,TODAY,{}),[])


if __name__=="__main__":
    unittest.main()
