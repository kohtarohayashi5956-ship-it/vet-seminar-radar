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

def test_peppy_linked_card_dates_and_source_isolation(self):
  page="https://www.peppy.jp/seminar"
  text=(
   "CARD[web] 2026年11月11日 (水)～2027年3月17日 (水) 愛玩動物看護師のための救急講座2026（全5回） 受付中 <https://www.peppy.jp/seminar/901>\n"
   "CARD[onsite] 2026年11月18日 (水) OCEP年次大会2026　獣医歯科看護の未来 受付中 <https://www.peppy.jp/seminar/902>\n"
   "CARD[web] 2026年12月20日 (日) 偽の講習イベント 受付中 <https://evil.example/seminar/999>"
  )
  got=extract_free("PEPPY",page,"",text,TODAY,{})
  self.assertEqual(len(got),2)
  self.assertEqual(got[0]["start_date"],"2026-11-11")
  self.assertEqual(got[0]["end_date"],"2027-03-17")
  self.assertEqual(got[0]["format"],"ライブ配信")
  self.assertEqual(got[1]["start_date"],"2026-11-18")
  self.assertEqual(got[1]["format"],"現地")
  self.assertTrue(all(e["url"].startswith("https://www.peppy.jp/seminar/") for e in got))

 def test_peppy_invalid_dates_and_non_detail_links(self):
  page="https://www.peppy.jp/seminar"
  text=(
   "CARD[web] 2026年13月44日 架空の日時をもつ看護講習 <https://www.peppy.jp/seminar/910>\n"
   "CARD[web] 2026年11月19日 リンク先不明の看護セミナー <https://www.peppy.jp/seminar>\n"
  )
  self.assertEqual(extract_free("PEPPY",page,"",text,TODAY,{}),[])

 def test_feed_publication_date_is_not_event_date(self):
  text="=====\n記事タイトル: 腫瘍のライブセミナー\n記事URL: <https://vets-tech.jp/a>\n公開日: 2026-11-02\n開催日は未定\n"
  r=extract_free("VETS TECH","https://vets-tech.jp/feed/","",text,TODAY,{})
  self.assertEqual(len(r),1)
  self.assertIsNone(r[0]["start_date"])
  self.assertFalse(r[0]["verified"])
if __name__=="__main__":unittest.main()
