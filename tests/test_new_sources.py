# -*- coding: utf-8 -*-
import datetime
import unittest
from free_extract import extract_free
from extract import html_to_text

TODAY = datetime.date(2026, 11, 6)

class NewSourcesTests(unittest.TestCase):
    def test_peppy_separate_cards_and_series(self):
        text = (
          "CARD[web] 2026年11月12日 (木)～2026年11月26日 (木) "
          "ゼロから始めるコンポジットレジン修復 受付中 獣医師 "
          "<https://www.peppy.jp/seminar/890>\n"
          "CARD[onsite] 2026年11月18日 (水) "
          "OCEP年次大会2026 受付中 動物看護師 "
          "<https://www.peppy.jp/seminar/895>\n")
        r = extract_free("PEPPY","https://www.peppy.jp/seminar","",text,TODAY,{})
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0]["start_date"], "2026-11-12")
        self.assertEqual(r[0]["end_date"], "2026-11-26")
        self.assertEqual(r[1]["start_date"], "2026-11-18")
        self.assertEqual(r[0]["format"], "ライブ配信")
        self.assertEqual(r[1]["format"], "現地")

    def test_eduone_requires_own_schedule(self):
        page = "https://eduone.jp/lecture/200010"
        text = ("TITLE: 知っているようで説明できないワンヘルス講演会\n"
                f"URL: <{page}>\nBODY:\n講演会概要\n"
                "開催日時\n2026年11月24日（火）20:00 ～ 2026年11月24日（火）21:00\n"
                "対象 獣医師\n受講料\n無料\n")
        r = extract_free("EDUWARD Press", page, "", text, TODAY, {})
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["start_date"],"2026-11-24")
        self.assertEqual(r[0]["is_free"],True)

    def test_eduone_no_misread_of_registration_deadline(self):
        page = "https://eduone.jp/lecture/200010"
        text = (f"TITLE: 動物の講演会\nURL: <{page}>\nBODY:\n"
                "申込期間 2026年11月10日 ～ 2026年11月20日\n")
        r = extract_free("EDUWARD Press", page, "", text, TODAY, {})
        self.assertEqual(r, [])

    def test_jbvp_meeting_dates(self):
        page = "https://www.jbvp.org/vn/"
        text = ("第7回 名古屋地区大会\n日程：\n2027年2月28日(日)\n"
                "会場：ウインクあいち\n第20回 京都地区大会\n"
                "日程：\n2027年3月7日(日)\n会場：京都\n"
                "2026年3月1日開催された過去の大会\n")
        r = extract_free("JBVP",page,"",text,TODAY,{})
        self.assertEqual(len(r), 2)
        self.assertEqual([x["start_date"] for x in r],
                         ["2027-02-28","2027-03-07"])

if __name__ == "__main__":
    unittest.main()
