# -*- coding: utf-8 -*-
"""No cross-session detail leakage; life-tail free enrichment from official format."""
import datetime
import unittest
from detail_enrich import parse_lifetail_detail, enrich_lifetail

DATE = datetime.date(2026, 11, 6)
URL = "https://life-tail.com/seminars/1772/"
EXAMPLE = """
第1回 | ＜午前の部＞内視鏡の基本操作を身に着ける操作技能アップセミナーin博多
この講座には優先期間があります
開催日時
2027年01月21日 (木) 10:00〜13:00
シリーズ
全2回
会場
エイムアテイン博多駅前貸会議室 5G
Google map
定員
8名
受講料
無料会員: 50,000円/人
プライム会員: 30,000円/人
申込期間
プライム会員優先申込
・2026/11/11 15:00 まで
一般申込（全ての会員）
・2026/11/11 15:00 ~ 2027/01/15 18:00
備考
今月のみ対象外
"""
def event(url=URL, start="2027-01-21", time="10:00"):
    return {"title":"内視鏡実習","url":url,"start_date":start,
            "start_time":time,"end_date":None,"format":"現地",
            "price":None,"is_free":None,"deadline":None,"venue":None}

class FakeFetcher:
    def __init__(self,html): self.html=html; self.calls=[]
    def get(self,url): self.calls.append(url); return "<main>"+"<p>"+self.html.replace("\n","</p><p>")+"</p></main>"

class EnrichmentTests(unittest.TestCase):
    def test_fees_and_final_registration_deadline(self):
        p = parse_lifetail_detail(EXAMPLE, event())
        self.assertEqual(p["deadline"], "2027-01-15")
        self.assertEqual(p["price"], "無料会員 50,000円／プライム会員 30,000円")
        self.assertIsNone(p["is_free"])
        self.assertIn("博多駅前", p["venue"])

    def test_different_day_or_time_is_rejected(self):
        self.assertEqual(parse_lifetail_detail(EXAMPLE, event(start="2027-01-22")), {})
        self.assertEqual(parse_lifetail_detail(EXAMPLE, event(time="14:30")), {})

    def test_incomplete_page_does_not_invent_deadline(self):
        txt = "開催日時\n2027年01月21日 10:00〜13:00\n申込期間\n公開日から受付\n備考"
        out = parse_lifetail_detail(txt, event())
        self.assertNotIn("deadline", out)

    def test_price_tiers_are_not_free(self):
        out=parse_lifetail_detail(EXAMPLE,event())
        self.assertIsNone(out["is_free"])

    def test_same_url_only_fetched_once(self):
        f=FakeFetcher(EXAMPLE)
        events=[event(),event()]
        stat={}
        result=enrich_lifetail(events,f,DATE,stat)
        self.assertEqual(len(f.calls),1)
        self.assertEqual(result[0]["deadline"],"2027-01-15")
        self.assertEqual(stat["details_scanned"],1)

    def test_blocked_detail_preserves_event(self):
        class Blocked:
            def get(self,url): raise RuntimeError("robots.txt disallowed")
        it=event()
        out=enrich_lifetail([it],Blocked(),DATE,{})
        self.assertEqual(out[0]["start_date"],"2027-01-21")
        self.assertIsNone(out[0]["deadline"])

    def test_other_domain_and_non_detail_url_not_fetched(self):
        f=FakeFetcher(EXAMPLE)
        es=[event("https://life-tail.com/seminars/"),event("https://example.net/seminars/222/")]
        enrich_lifetail(es,f,DATE,{})
        self.assertEqual(f.calls, [])

if __name__=="__main__":unittest.main()
