# -*- coding: utf-8 -*-
"""Exact source-specific extraction for two new professional societies."""
import datetime
import unittest
from extract import html_to_text
from free_extract import extract_free
from merge import update_store

TODAY=datetime.date(2026,11,7)
LECTURES="https://www.jsvas.net/lectures/index.php"
CONFERENCE="https://www.jsvas.net/conference/2026-113.php"
JCVIM="https://www.jcvim.org/index.html"

class NewSources(unittest.TestCase):
    def test_jsvas_lectures_multiple_and_distinct(self):
        html="""
        <main><a href="/lectures/chushikoku_261123.php">講習会 2026年度 中国・四国地区講習会 どうすりゃええんじゃろう？ 血管作動薬 講師 三木 悠矢 先生（株式会社Cirrus） 日時 2026 年 11 月 23 日（月） 会場 岡山国際交流センター</a>
        <a href="/lectures/tokyo_261115.php">講習会 2026年度 東京地区講習会 臨床現場をアップデート：ACVAA 2025麻酔・鎮静モニタリングガイドライン 講師 井芹 俊恵 先生（東京農工大学） 日時 2026 年 11 月 15 日（日） 会場 東京大学弥生講堂一条ホール</a>
        <a href="/lectures/kanto_261108.php">講習会 2026年度 関東地区講習会 専門医が教える管腔臓器縫合のコツ 講師 岩田 泰介 先生 日時 2026年11月8日（日） 会場 ライトキューブ宇都宮</a>
        <a href="/lectures/tohoku_261018.php">講習会 2026年度 東北地区講習会 神経ブロックの実際 講師 伊丹 貴晴 先生 日時 2026年10月18日（日） 会場 仙台市</a>
        </main>"""
        text=html_to_text(html,LECTURES)
        got=extract_free("日本獣医麻酔外科学会",LECTURES,"",text,TODAY,{})
        self.assertEqual(len(got),3)
        dates={e["start_date"] for e in got}
        self.assertEqual(dates,{"2026-11-08","2026-11-15","2026-11-23"})
        am=next(e for e in got if e["start_date"]=="2026-11-23")
        self.assertIn("血管作動薬",am["title"])
        self.assertEqual(am["speaker"],"三木 悠矢")
        self.assertEqual(am["venue"],"岡山国際交流センター")
        self.assertEqual(am["url"],"https://www.jsvas.net/lectures/chushikoku_261123.php")
        self.assertTrue(am["verified"])
        self.assertIsNone(am["deadline"])

    def test_jsvas_conference_hybrid_and_end_date(self):
        text=("2026年度 第113回\n日本獣医麻酔外科学会学術集会\n"
              "開催期間\n2026年12月18日（金）〜20日（日）\n"
              "形式\nハイブリッド開催\n"
              "会場\nコングレスクエア グラングリーン大阪\n"
              "参加登録期間\n事前登録：2026年10月16日～11月30日\n"
              "直前登録：2026年12月1日～2027年2月26日\n")
        got=extract_free("日本獣医麻酔外科学会",CONFERENCE,"",text,TODAY,{})
        self.assertEqual(len(got),1)
        ev=got[0]
        self.assertEqual(ev["start_date"],"2026-12-18")
        self.assertEqual(ev["end_date"],"2026-12-20")
        self.assertEqual(ev["format"],"ハイブリッド")
        self.assertEqual(ev["venue"],"コングレスクエア グラングリーン大阪")
        self.assertIsNone(ev["deadline"])  # archived video != in-person deadline

    def test_video_streaming_start_must_not_replace_congress_end(self):
        # Official pages also print the same opening date for video streaming.
        text=("2026年度 第113回\\n日本獣医麻酔外科学会学術集会\\n"
              "形式\\nハイブリッド開催\\n"
              "開催期間\\n2026年12月18日（金）〜20日（日）\\n"
              "動画配信期間\\n2026年12月18日より順次公開〜2027年2月28日まで\\n"
              "会場\\nコングレスクエア グラングリーン大阪\\n")
        got=extract_free("日本獣医麻酔外科学会",CONFERENCE,"",text,TODAY,{})
        self.assertEqual(len(got),1)
        self.assertEqual(got[0]["start_date"],"2026-12-18")
        self.assertEqual(got[0]["end_date"],"2026-12-20")

    def test_jsvas_title_cannot_be_taken_from_old_navigation(self):
        text=("第113回 学術集会\n開催期間\n2026年12月18日～20日\n"
              "会場\nコングレスクエア グラングリーン大阪\n"
              "第110回 日本獣医麻酔外科学会学術集会\n")
        self.assertEqual(extract_free("日本獣医麻酔外科学会",CONFERENCE,"",text,TODAY,{}),[])

    def test_jcvim_official_2027_not_old_2026_registrations(self):
        text=("2026.08.26\n"
              "第23回日本獣医内科学アカデミー学術大会（JCVIM2027）のご案内\n"
              "会期：2027年2月19日(金)～2月21日(日)\n"
              "会場：パシフィコ横浜ノース\n"
              "参加登録は大会サイトで確認\n"
              "2026.03.27\n"
              "第22回日本獣医内科学アカデミー学術大会（JCVIM2026）の案内\n"
              "参加登録締切：2026年3月29日\n")
        got=extract_free("JCVIM",JCVIM,"",text,TODAY,{})
        self.assertEqual(len(got),1)
        e=got[0]
        self.assertEqual(e["start_date"],"2027-02-19")
        self.assertEqual(e["end_date"],"2027-02-21")
        self.assertEqual(e["venue"],"パシフィコ横浜ノース")
        self.assertEqual(e["prefecture"],"神奈川県")
        self.assertIsNone(e["deadline"])
        self.assertIsNone(e["abstract_deadline"])
        self.assertEqual(e["detail_url"],"https://smartconf.jp/content/jcvim2027/outline")
        store={}
        update_store(store,got,{"id":"jcvim","name":"JCVIM"},None,TODAY)
        self.assertEqual(next(iter(store.values()))["detail_url"],e["detail_url"])

    def test_jcvim_announcement_without_schedule_does_not_invent(self):
        text=("第23回日本獣医内科学アカデミー学術大会（JCVIM2027）のご案内\n"
              "会場：パシフィコ横浜ノース\n"
              "過去の参加登録締切：2026年3月29日")
        self.assertEqual(extract_free("JCVIM",JCVIM,"",text,TODAY,{}),[])

    def test_no_registered_event_from_sponsor_deadline(self):
        text=("2026年度 第113回 日本獣医麻酔外科学会学術集会\n"
              "協賛企業の出展申込締切：2026年12月1日")
        self.assertEqual(extract_free("日本獣医麻酔外科学会",CONFERENCE,"",text,TODAY,{}),[])

if __name__=="__main__": unittest.main()
