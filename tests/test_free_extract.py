# -*- coding: utf-8 -*-
import datetime
import os
import sys
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extract import html_to_text
from free_extract import extract_free
TODAY=datetime.date(2026,11,6)
class FreeTests(unittest.TestCase):
 def test_jaha_no_ai(self):
  url="https://www.jaha.or.jp/seminar-calendar/"
  html='<h2>2026年11月</h2><table><tr><td>11/6</td><td>金</td><td>獣医師</td><td>受付中</td><td><a href="/training/endo">犬猫の内分泌セミナー2026</a></td><td>東京都</td></tr></table>'
  text=html_to_text(html,url)
  rows=extract_free("JAHA",url,"",text,TODAY,{})
  self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]["start_date"],"2026-11-06")
  self.assertTrue(rows[0]["verified"])
 def test_gakusai_no_webcast_date_leak(self):
  url="https://www.gakusai.co.jp/doubutu/seminar-comingup/"
  text="2026 セミナー 開催スケジュール\nNo.295 藤田先生「耳科手術の勘どころ」\n»詳細はこちら <https://www.gakusai.co.jp/295/>\n11月22日（日）東京｜ウェブ受講（2027年1月1日～）"
  r=extract_free("学際企画",url,"",text,TODAY,{})
  self.assertEqual([x["start_date"] for x in r],["2026-11-22"])
 def test_gakusai_inline_official_detail_on_heading(self):
  page="https://www.gakusai.co.jp/doubutu/seminar-comingup/"
  text=('2027 セミナー 開催スケジュール\n'
        'No.297 高木哲先生「失敗しない腸管吻合」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35591/>\n'
        '1月24日（日）東京｜ウェブ受講（3月1日～）')
  items=extract_free("学際企画",page,"",text,datetime.date(2026,11,7),{})
  self.assertEqual(len(items),1)
  self.assertEqual(items[0]["start_date"],"2027-01-24")
  self.assertEqual(items[0]["url"],"https://www.gakusai.co.jp/vet/vet-seminar/35591/")

 def test_gakusai_unpublished_link_not_invented_and_no_cross_card_leak(self):
  page="https://www.gakusai.co.jp/doubutu/seminar-comingup/"
  text=('2027 セミナー 開催スケジュール\n'
        'No.300 高橋先生「椎間板ヘルニア診療」 »詳細はこちら\n'
        '7月18日（日）東京\n'
        'No.301 原先生「骨腫瘍外科」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35599/>\n'
        '8月1日（日）東京')
  items=extract_free("学際企画",page,"",text,datetime.date(2026,11,7),{})
  self.assertEqual(len(items),2)
  self.assertEqual(items[0]["url"],page)
  self.assertEqual(items[1]["url"],"https://www.gakusai.co.jp/vet/vet-seminar/35599/")

 def test_gakusai_rejects_external_and_generic_detail_url(self):
  page="https://www.gakusai.co.jp/doubutu/seminar-comingup/"
  text=('2027 セミナー 開催スケジュール\n'
        'No.302 講習のタイトルがここにある »詳細はこちら <https://evil.example/vet/vet-seminar/999/>\n'
        '9月12日（日）東京\n'
        'No.303 別の講習のタイトルです »詳細はこちら <https://www.gakusai.co.jp/doubutu/seminar-comingup/>\n'
        '10月17日（日）東京')
  items=extract_free("学際企画",page,"",text,datetime.date(2026,11,7),{})
  self.assertEqual([x["url"] for x in items],[page,page])

 def test_feed_publication_date_is_not_event_date(self):
  text="=====\n記事タイトル: 腫瘍のライブセミナー\n記事URL: <https://vets-tech.jp/a>\n公開日: 2026-11-02\n開催日は未定\n"
  r=extract_free("VETS TECH","https://vets-tech.jp/feed/","",text,TODAY,{})
  self.assertEqual(len(r),1)
  self.assertIsNone(r[0]["start_date"])
  self.assertFalse(r[0]["verified"])
if __name__=="__main__":unittest.main()
