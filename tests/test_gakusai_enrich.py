# -*- coding: utf-8 -*-
import datetime
import unittest
from gakusai_enrich import parse_gakusai, enrich_gakusai

URL = "https://www.gakusai.co.jp/vet/vet-seminar/35589/"
PAGE = """
No.298 明日から使える！犬と猫の局所麻酔セミナー
獣医 2027年3月7日
講師
手島 健次 先生
プログラム
1.局所麻酔薬の基礎と安全な使用法
開催日時・会場
東京会場 2027年3月7日（日）10：00～16：00
駐健保会館
東京都港区芝3-41-8
来場受講料
テキスト付き・ウェブ受講1ヶ月付き
法人・個人会員
9,000円（税込9,900円）ご入会はこちら
一般獣医師
27,000円（税込29,700円）
ウェブ受講料
法人・個人会員
77,000円（税込84,700円）
キャンセル期限
2027年2月20日
開催にあたって
"""
def ev(start="2027-03-07", time=None, url=URL):
    return dict(title="犬と猫の局所麻酔セミナー",start_date=start,start_time=time,
                end_time=None,format=None,url=url,price=None,venue=None,prefecture=None,
                is_free=None,deadline=None)

class FakeFetcher:
    def __init__(self, content): self.content=content; self.calls=[]
    def get(self,url):
        self.calls.append(url)
        return "<main><p>"+self.content.replace("\n","</p><p>")+"</p></main>"

class TestGakusaiEnrichment(unittest.TestCase):
    def test_schedule_price_and_venue(self):
        out=parse_gakusai(PAGE,ev())
        self.assertEqual(out["start_time"],"10:00")
        self.assertEqual(out["end_time"],"16:00")
        self.assertEqual(out["venue"],"駐健保会館")
        self.assertEqual(out["prefecture"],"東京都")
        self.assertIn("法人・個人会員 9,000円",out["price"])
        self.assertIn("一般獣医師 27,000円",out["price"])
        self.assertNotIn("77,000",out["price"])
        self.assertNotIn("deadline",out)

    def test_reject_mismatched_date_or_time(self):
        self.assertEqual(parse_gakusai(PAGE,ev(start="2027-03-08")),{})
        self.assertEqual(parse_gakusai(PAGE,ev(time="14:30")),{})
    def test_no_generic_tariff_or_web_fees(self):
        txt=("開催日時・会場\n東京会場 2027年3月7日 10:00～16:00\n"
             "駐健保会館\nウェブ受講料\n一般獣医師 99,000円")
        self.assertNotIn("price",parse_gakusai(txt,ev()))
    def test_only_detail_link_and_single_fetch(self):
        e1,e2=ev(),ev()
        invalid=ev(url="https://www.gakusai.co.jp/doubutu/seminar-comingup/")
        f=FakeFetcher(PAGE);stats={}
        enrich_gakusai([e1,e2,invalid],f,datetime.date(2026,11,6),stats)
        self.assertEqual(f.calls,[URL])
        self.assertEqual(stats["details_scanned"],1)
        self.assertEqual(stats["prices_found"],2)
    def test_error_fails_closed_preserving_listing(self):
        class Denied:
            def get(self,url): raise RuntimeError("robots denied")
        event=ev()
        enrich_gakusai([event],Denied(),datetime.date(2026,11,6),{})
        self.assertIsNone(event["price"])
        self.assertEqual(event["start_date"],"2027-03-07")

if __name__=="__main__":
    unittest.main()
