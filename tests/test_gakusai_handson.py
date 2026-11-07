# -*- coding: utf-8 -*-
"""Official Gakusai hands-on fee sections: course-level, not general tariffs."""
import datetime
import unittest
from gakusai_handson import _courses, enrich_handson, URL

TODAY=datetime.date(2026,11,7)
TEXT = """
2027年 学際小動物セミナー
会員先行！予約受付中
MS153 小川名巧先生「2027 Dr.小川名の腹部超音波塾」 | 3月21日(日)東京 / 1月17日(日)大阪
MS154 新実誠矢先生「心エコーの基本を見直す」 | 2月7日(日)東京
MS153 2027 dr.小川名の腹部超音波塾
プログラム・詳細
受講料
テキスト付き
会員獣医師 | 48,000円（税込52,800円）＋実習材料費 15,000円（税込16,500円）
ご入会はこちら
一般獣医師 | 75,000円（税込82,500円）＋実習材料費 15,000円（税込16,500円）
3月21日(日)東京会場申込 <https://seminar.gakusai.co.jp/foo>
1月17日(日)大阪会場申込 <https://seminar.gakusai.co.jp/bar>
MS154 心エコーの基本を見直す
プログラム・詳細
受講料
会員獣医師 | 48,000円（税込52,800円）＋実習材料費 15,000円（税込16,500円）
一般獣医師 | 75,000円（税込82,500円）＋実習材料費 15,000円（税込16,500円）
2月7日(日)東京会場申込 <https://seminar.gakusai.co.jp/f>
MS160 呼吸器内視鏡検査・呼吸器外科の実習
受講料
会員獣医師 | 調整中
一般獣医師 | 調整中
9月20日(月)東京会場申込
MS161 軟部外科実習2027 ウェットラボ in 宮崎大学
受講料
会員獣医師 | 165,000円（税込181,500円）＋実習材料費128,000円（税込140,800円）
一般獣医師 | 195,000円（税込214,500円）＋実習材料費128,000円（税込140,800円）
10月10日(日)11日(月)宮崎会場申込
MS162 麻酔管理実習2027 ウェットラボ in 宮崎大学
受講料
会員獣医師 | 78,000円（税込85,800円）＋実習材料費58,000円（税込63,800円）
一般獣医師 | 108,000円（税込118,800円）＋実習材料費58,000円（税込63,800円）
10月10日(日)11日(月)宮崎会場申込
"""

def event(title,day):
    return {"title":title,"start_date":day, "url":"https://www.gakusai.co.jp/doubutu/seminar-comingup/",
            "source_id":"gakusai","price":None,"format":None,"venue":None,"prefecture":None}

class Fetcher:
    def __init__(self,text=TEXT):self.text=text;self.calls=[]
    def get(self,url):
        self.calls.append(url)
        return "<div>"+"".join("<p>"+line+"</p>" for line in self.text.splitlines())+"</div>"

class GakusaiHandsonTests(unittest.TestCase):
    def test_course_sections_are_isolated(self):
        parsed=_courses(TEXT)
        self.assertEqual(len(parsed),4)
        self.assertEqual(parsed[0]["id"],"153")
        self.assertEqual(parsed[0]["dates"],[("2027-03-21","東京"),("2027-01-17","大阪")])

    def test_unique_title_and_date_prices(self):
        rows=[
            event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17"),
            event("新実 誠矢「心エコーの基本を見直す」","2027-02-07"),
            event("鳥巣先生・金子先生・山本先生・岡寺先生「軟部外科実習2027 ウェットラボ in 宮崎大学」","2027-10-10"),
            event("永延清和先生・吉田貢太先生「麻酔管理実習2027 ウェットラボ in 宮崎大学」","2027-10-10"),
            event("末松正弘先生「呼吸器内視鏡検査・呼吸器外科の実習」","2027-09-20"),
        ]
        stats={}
        f=Fetcher()
        enrich_handson(rows,f,TODAY,stats)
        self.assertEqual(f.calls,[URL])
        self.assertIn("48,000円",rows[0]["price"])
        self.assertIn("実習材料費 15,000円",rows[0]["price"])
        self.assertEqual(rows[0]["prefecture"],"大阪府")
        self.assertIn("48,000円",rows[1]["price"])
        self.assertIn("165,000円",rows[2]["price"])
        self.assertNotIn("78,000円",rows[2]["price"])
        self.assertIn("78,000円",rows[3]["price"])
        self.assertNotIn("165,000円",rows[3]["price"])
        self.assertIsNone(rows[4]["price"])
        self.assertEqual(stats["handson_fees_found"],4)

    def test_no_cross_date_and_no_generic_tariff(self):
        rows=[
            event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-02-21"),
            event("完全に無関係な整形外科実習","2027-02-07"),
        ]
        enrich_handson(rows,Fetcher(),TODAY,{})
        self.assertTrue(all(x["price"] is None for x in rows))

    def test_existing_fee_is_never_replaced(self):
        row=event("新実誠矢「心エコーの基本を見直す」","2027-02-07")
        row["price"]="公式詳細ページ 40,000円"
        enrich_handson([row],Fetcher(),TODAY,{})
        self.assertEqual(row["price"],"公式詳細ページ 40,000円")

    def test_robots_denial_is_safely_ignored(self):
        class Denied:
            def get(self,url):raise PermissionError("robots denied")
        row=event("新実誠矢「心エコーの基本を見直す」","2027-02-07")
        stats={}
        enrich_handson([row],Denied(),TODAY,stats)
        self.assertIsNone(row["price"])
        self.assertEqual(stats["handson_fetch_failed"],1)

    def test_wrong_year_is_rejected(self):
        page=TEXT.replace("2027年 学際小動物セミナー","2026年 学際小動物セミナー")
        row=event("新実誠矢「心エコーの基本を見直す」","2027-02-07")
        enrich_handson([row],Fetcher(page),TODAY,{})
        self.assertIsNone(row["price"])

if __name__=="__main__":unittest.main()
