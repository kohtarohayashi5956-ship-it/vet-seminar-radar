# -*- coding: utf-8 -*-
"""PEPPY detail source isolation and ambiguity regression tests."""
import datetime
import unittest

from free_extract import extract_free
from peppy_enrich import parse_peppy_detail, enrich_peppy

TODAY = datetime.date(2026, 11, 9)
URL = "https://www.peppy.jp/seminar/895"
PAGE = """OCEP年次大会
開催日時
2026年11月18日 (水)
9:00-16:00
会場
コングレスクエア日本橋 ホールC会場
申込期間
2026年9月14日 (月) ～ 2026年11月16日 (月)
受講料
8,000円(税込)
受講対象
獣医師・動物看護師
"""
def event(**override):
    row = dict(title="OCEP年次大会",url=URL,start_date="2026-11-18",
               format="現地",start_time=None,end_time=None,price=None,
               deadline=None,venue=None,is_free=None)
    row.update(override)
    return row


class Fake:
    def __init__(self, text=PAGE):
        self.text = text
        self.calls = []
    def get(self, url):
        self.calls.append(url)
        return "<main>" + "".join("<p>" + x + "</p>" for x in self.text.splitlines()) + "</main>"


class PeppyEnrichmentTests(unittest.TestCase):
    def test_one_session_detail(self):
        got = parse_peppy_detail(PAGE, event())
        self.assertEqual(got["start_time"], "09:00")
        self.assertEqual(got["end_time"], "16:00")
        self.assertEqual(got["deadline"], "2026-11-16")
        self.assertEqual(got["price"], "8,000円(税込)")
        self.assertIn("日本橋", got["venue"])

    def test_multi_session_rejected(self):
        text=PAGE.replace("9:00-16:00", "9:00-16:00\n2026年11月25日 9:00-16:00")
        self.assertEqual(parse_peppy_detail(text,event()),{})

    def test_wrong_date_rejected(self):
        self.assertEqual(parse_peppy_detail(PAGE,event(start_date="2026-11-19")),{})

    def test_previous_information_preserved(self):
        got=parse_peppy_detail(PAGE,event(start_time="09:00",end_time="16:30",
                 price="既存の料金",deadline="2026-11-15",venue="既存会場"))
        self.assertNotIn("start_time",got)
        self.assertNotIn("end_time",got)
        self.assertNotIn("price",got)
        self.assertNotIn("deadline",got)
        self.assertNotIn("venue",got)

    def test_schedule_conflict_rejects_times(self):
        got=parse_peppy_detail(PAGE,event(start_time="10:00"))
        self.assertNotIn("start_time",got)
        self.assertNotIn("end_time",got)

    def test_registration_dates_not_used_as_course_dates(self):
        text=PAGE.replace("2026年11月18日 (水)","開催日未定")
        self.assertEqual(parse_peppy_detail(text,event()),{})

    def test_same_url_once_denied_preserves(self):
        rows=[event(),event()]
        f=Fake()
        stats={}
        enrich_peppy(rows,f,TODAY,stats)
        self.assertEqual(f.calls,[URL])
        self.assertEqual(stats["details_scanned"],1)
        self.assertEqual(stats["deadlines_found"],2)
        self.assertTrue(all(e["start_time"]=="09:00" for e in rows))
        bad=event()
        bad["url"]="https://example.com/seminar/895"
        enrich_peppy([bad],f,TODAY,{})
        self.assertIsNone(bad["price"])

    def test_existing_listing_parser_with_official_date_card(self):
        text=("CARD[web] 2026年11月12日 (木)～2026年11月26日 (木) "
              "ゼロから始めるコンポジットレジン修復 受付中 獣医師 "
              "<https://www.peppy.jp/seminar/890>")
        got=extract_free("PEPPY","https://www.peppy.jp/seminar","",text,TODAY,{})
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["start_date"],"2026-11-12")
        self.assertEqual(got[0]["end_date"],"2026-11-26")
        self.assertEqual(got[0]["format"],"ライブ配信")


if __name__=="__main__":
    unittest.main()
