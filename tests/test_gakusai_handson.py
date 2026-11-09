# -*- coding: utf-8 -*-
"""Official Gakusai hands-on fee sections: course-level, not general tariffs."""
import datetime
import re
import unittest
from gakusai_handson import _courses, enrich_handson, _booking_start_time, URL

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
        def linked(line):
            return re.sub(r"<(https://[^<>]+)>",
                          lambda match: '<a href="' + match.group(1) + '">申込先</a>',
                          line)
        return "<div>"+"".join("<p>"+linked(line)+"</p>" for line in self.text.splitlines())+"</div>"

class GakusaiHandsonTests(unittest.TestCase):
    def test_course_sections_are_isolated(self):
        parsed=_courses(TEXT)
        self.assertEqual(len(parsed),5)
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
        self.assertTrue(all("獣医師" in row.get("audience", []) for row in rows[:4]))
        self.assertNotIn("獣医師", rows[4].get("audience", []))

    def test_application_link_allowed_when_fee_not_published(self):
        page = TEXT.replace(
            "9月20日(月)東京会場申込",
            "9月20日(月)東京会場申込 <https://seminar.gakusai.co.jp/pending-course>"
        )
        row = event("末松正弘先生「呼吸器内視鏡検査・呼吸器外科の実習」","2027-09-20")
        stats = {}
        enrich_handson([row], Fetcher(page), TODAY, stats)
        self.assertIsNone(row["price"])
        self.assertEqual(row["detail_url"],
                         "https://seminar.gakusai.co.jp/pending-course")
        self.assertEqual(stats["handson_fees_found"], 0)
        self.assertEqual(stats["handson_applications_found"], 1)

    def test_existing_price_does_not_block_date_matched_application(self):
        row = event("末松正弘先生「呼吸器内視鏡検査・呼吸器外科の実習」","2027-09-20")
        row["price"] = "料金については主催者に確認"
        page = TEXT.replace(
            "9月20日(月)東京会場申込",
            "9月20日(月)東京会場申込 <https://seminar.gakusai.co.jp/pending-course>"
        )
        enrich_handson([row], Fetcher(page), TODAY, {})
        self.assertEqual(row["price"], "料金については主催者に確認")
        self.assertEqual(row["detail_url"],
                         "https://seminar.gakusai.co.jp/pending-course")

    def test_existing_audience_preserved_and_no_duplicate(self):
        row = event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17")
        row["audience"] = ["動物看護師", "獣医師"]
        enrich_handson([row], Fetcher(), TODAY, {})
        self.assertEqual(row["audience"], ["動物看護師", "獣医師"])

    def test_unmatched_course_does_not_infer_vet_audience(self):
        row = event("無関係な講義","2027-01-17")
        enrich_handson([row], Fetcher(), TODAY, {})
        self.assertNotIn("獣医師", row.get("audience", []))

    def test_split_html_table_cells_are_matched_inside_same_course(self):
        html = TEXT.replace(
            "会員獣医師 | 48,000円（税込52,800円）＋実習材料費 15,000円（税込16,500円）",
            "会員獣医師\n48,000円（税込52,800円）＋実習材料費 15,000円（税込16,500円）"
        ).replace(
            "一般獣医師 | 75,000円（税込82,500円）＋実習材料費 15,000円（税込16,500円）",
            "一般獣医師\n75,000円（税込82,500円）＋実習材料費 15,000円（税込16,500円）"
        )
        row=event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17")
        enrich_handson([row],Fetcher(html),TODAY,{})
        self.assertIn("会員 48,000円",row["price"])
        self.assertIn("一般 75,000円",row["price"])

    def test_split_cells_do_not_copy_next_course_or_membership_price(self):
        html = (
            "2027年 学際小動物セミナー\n"
            "MS154 心エコーの基本を見直す\n"
            "受講料\n"
            "会員獣医師\n"
            "ご入会はこちら\n"
            "一般獣医師\n75,000円（税込82,500円）\n"
            "2月7日(日)東京会場申込\n"
            "MS155 消化管縫合を極める!!\n"
            "受講料\n会員獣医師\n48,000円\n"
            "一般獣医師\n75,000円\n"
            "3月14日(日)大阪会場申込\n"
        )
        row=event("新実誠矢「心エコーの基本を見直す」","2027-02-07")
        enrich_handson([row],Fetcher(html),TODAY,{})
        self.assertIsNone(row["price"])

    def test_same_course_same_day_official_application_url(self):
        rows=[
            event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17"),
            event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-03-21"),
        ]
        enrich_handson(rows,Fetcher(),TODAY,{})
        self.assertEqual(rows[0]["detail_url"], "https://seminar.gakusai.co.jp/bar")
        self.assertEqual(rows[1]["detail_url"], "https://seminar.gakusai.co.jp/foo")

    def test_booking_identity_remains_but_analytics_tokens_are_removed(self):
        page = TEXT.replace(
            "https://seminar.gakusai.co.jp/bar",
            "https://seminar.gakusai.co.jp/reservations/add?"
            "event_id=3152&usage_timestamp_from=2027%2F01%2F17+10%3A00"
            "&_gl=analytics&_ga=tracker&utm_source=mail"
        )
        row=event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17")
        enrich_handson([row],Fetcher(page),TODAY,{})
        link=row["detail_url"]
        self.assertIn("event_id=3152",link)
        self.assertIn("usage_timestamp_from=2027%2F01%2F17",link)
        self.assertNotIn("_gl=",link)
        self.assertNotIn("_ga=",link)
        self.assertNotIn("utm_",link)

    def test_booking_start_timestamp_exactly_matches_event_date(self):
        url = ("https://seminar.gakusai.co.jp/reservations/add?"
               "event_id=3152&usage_timestamp_from=2027%2F01%2F17+10%3A00")
        self.assertEqual(_booking_start_time(url, "2027-01-17"), "10:00")
        self.assertIsNone(_booking_start_time(url, "2027-01-18"))
        self.assertIsNone(_booking_start_time(url.replace("10%3A00", "25%3A00"), "2027-01-17"))
        self.assertIsNone(_booking_start_time(url.replace("01%2F17", "02%2F30"), "2027-02-30"))
        self.assertIsNone(_booking_start_time(url + "&usage_timestamp_from=2027%2F01%2F17+11%3A00", "2027-01-17"))
        self.assertIsNone(_booking_start_time(url.replace("event_id=3152", "event_id=3152&event_id=3153"), "2027-01-17"))
        self.assertIsNone(_booking_start_time(url.replace("seminar.gakusai.co.jp", "seminar.gakusai.co.jp.evil.test"), "2027-01-17"))
        self.assertIsNone(_booking_start_time(url.replace("event_id=3152", "event_id=abc"), "2027-01-17"))

    def test_verified_official_booking_time_fills_only_start(self):
        page = TEXT.replace(
            "https://seminar.gakusai.co.jp/bar",
            "https://seminar.gakusai.co.jp/reservations/add?"
            "event_id=3152&usage_timestamp_from=2027%2F01%2F17+10%3A00")
        row = event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」", "2027-01-17")
        stats = {}
        enrich_handson([row], Fetcher(page), TODAY, stats)
        self.assertEqual(row["start_time"], "10:00")
        self.assertIsNone(row.get("end_time"))
        self.assertEqual(stats["handson_start_times_found"], 1)

    def test_booking_timestamp_never_overwrites_or_crosses_courses(self):
        page = TEXT.replace(
            "https://seminar.gakusai.co.jp/bar",
            "https://seminar.gakusai.co.jp/reservations/add?"
            "event_id=3152&usage_timestamp_from=2027%2F01%2F18+10%3A00")
        row = event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」", "2027-01-17")
        enrich_handson([row], Fetcher(page), TODAY, {})
        self.assertIsNone(row.get("start_time"))
        page = page.replace("2027%2F01%2F18", "2027%2F01%2F17")
        row["start_time"] = "11:00"
        enrich_handson([row], Fetcher(page), TODAY, {})
        self.assertEqual(row["start_time"], "11:00")
        bad = event("別の外科学講習", "2027-01-17")
        enrich_handson([bad], Fetcher(page), TODAY, {})
        self.assertIsNone(bad.get("start_time"))

    def test_application_url_rejects_foreign_domain_and_userinfo(self):
        page = TEXT.replace("https://seminar.gakusai.co.jp/bar",
                            "https://seminar.gakusai.co.jp.evil.example/bar")
        row=event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17")
        enrich_handson([row],Fetcher(page),TODAY,{})
        self.assertNotIn("detail_url", row)
        page = TEXT.replace("https://seminar.gakusai.co.jp/bar",
                            "https://bad.example@seminar.gakusai.co.jp/bar")
        row=event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17")
        enrich_handson([row],Fetcher(page),TODAY,{})
        self.assertNotIn("detail_url",row)

    def test_existing_official_detail_url_preserved(self):
        row=event("小川名巧先生「2027 Dr.小川名の腹部超音波塾」","2027-01-17")
        row["detail_url"]="https://www.gakusai.co.jp/vet/vet-seminar/12345/"
        enrich_handson([row],Fetcher(),TODAY,{})
        self.assertEqual(row["detail_url"],
                         "https://www.gakusai.co.jp/vet/vet-seminar/12345/")

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
