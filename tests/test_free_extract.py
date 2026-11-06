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
 def test_feed_publication_date_is_not_event_date(self):
  text="=====\n記事タイトル: 腫瘍のライブセミナー\n記事URL: <https://vets-tech.jp/a>\n公開日: 2026-11-02\n開催日は未定\n"
  r=extract_free("VETS TECH","https://vets-tech.jp/feed/","",text,TODAY,{})
  self.assertEqual(len(r),1)
  self.assertIsNone(r[0]["start_date"])
  self.assertFalse(r[0]["verified"])
if __name__=="__main__":unittest.main()
