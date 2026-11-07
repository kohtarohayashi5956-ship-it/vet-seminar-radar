# -*- coding: utf-8 -*-
"""Official VETS ACADEMY list cards: event isolation and date semantics."""
import datetime
import unittest

from free_extract import extract_free
from sources import vets_academy_pages

PAGE = "https://academy.eduone.jp/seminar"
TODAY = datetime.date(2026, 11, 7)

HTML = """
<html><body><main>
  <div class="card">
    <a href="/seminar/detail/10201">募集中</a>
    <a href="/seminar/detail/10201">高齢猫×高血圧 診断治療のロードマップ</a>
    <a href="/seminar/detail/10201">2026/12/21 ～2027/02/15</a>
    <a href="/seminar/detail/10201">オンデマンド</a>
    <a href="/seminar/detail/10201">獣医師</a>
  </div>
  <div class="card">
    <a href="/seminar/detail/10202">募集中</a>
    <a href="/seminar/detail/10202">決めつけ厳禁！MMVDじゃない犬の心疾患</a>
    <a href="/seminar/detail/10202">2026/12/02 20:00～</a>
    <a href="/seminar/detail/10202">LIVE</a>
    <a href="/seminar/detail/10202">獣医師</a>
  </div>
  <div class="card">
    <a href="/seminar/detail/10203">募集終了</a>
    <a href="/seminar/detail/10203">採血と留置を練習する実技講習</a>
    <a href="/seminar/detail/10203">2026/11/08 12:30～</a>
    <a href="/seminar/detail/10203">会場型</a>
    <a href="/seminar/detail/10203">動物看護</a>
    <a href="/seminar/detail/10203">無料</a>
  </div>
  <a href="/seminar/detail/invalid">不正なIDの講習</a>
  <a href="https://outside.example/seminar/detail/19999">外部サイトの講習</a>
</main></body></html>
"""


class Fetcher:
    def __init__(self, html=HTML):
        self.html = html
        self.calls = []

    def get(self, url):
        self.calls.append(url)
        return self.html


class AcademyListingTests(unittest.TestCase):
    def test_three_independent_cards_and_audiences(self):
        fetcher = Fetcher()
        url, text, _ = next(vets_academy_pages({"start_url": PAGE}, fetcher))
        self.assertEqual(url, PAGE)
        self.assertEqual(fetcher.calls, [PAGE])
        events = extract_free("VETS ACADEMY", PAGE, "", text, TODAY, {})
        self.assertEqual(len(events), 3)
        first, live, onsite = events
        self.assertEqual(first["start_date"], "2026-12-21")
        self.assertEqual(first["end_date"], "2027-02-15")
        self.assertEqual(first["format"], "オンデマンド")
        self.assertIsNone(first["start_time"])
        self.assertEqual(first["audience"], ["獣医師"])
        self.assertEqual(live["start_date"], "2026-12-02")
        self.assertEqual(live["start_time"], "20:00")
        self.assertEqual(live["format"], "ライブ配信")
        self.assertIsNone(live["end_date"])
        self.assertEqual(onsite["start_date"], "2026-11-08")
        self.assertEqual(onsite["start_time"], "12:30")
        self.assertEqual(onsite["audience"], ["動物看護師"])
        self.assertEqual(onsite["price"], "無料")
        self.assertTrue(onsite["is_free"])
        self.assertEqual(onsite["status"], "募集終了")
        self.assertTrue(all(e["verified"] for e in events))

    def test_ambiguous_dates_rejected(self):
        text = (
            'ACADEMY_CARD {"url":"https://academy.eduone.jp/seminar/detail/1",'
            '"title":"開催日の不明な院内教育セミナー",'
            '"schedule":"2026/11/10 ～2026/11/20 ～2026/12/03",'
            '"kind":"LIVE"}'
        )
        self.assertEqual(extract_free("VETS ACADEMY", PAGE, "", text, TODAY, {}), [])

    def test_wrong_domain_and_invalid_calendar(self):
        text = '\n'.join([
            'ACADEMY_CARD {"url":"https://evil.example/seminar/detail/1",'
            '"title":"正常に見える講義タイトル","schedule":"2026/11/12",'
            '"kind":"LIVE"}',
            'ACADEMY_CARD {"url":"https://academy.eduone.jp/seminar/detail/2",'
            '"title":"誤った開催日時の講義タイトル","schedule":"2026/13/42",'
            '"kind":"会場型"}',
        ])
        self.assertEqual(extract_free("VETS ACADEMY", PAGE, "", text, TODAY, {}), [])

    def test_only_official_anchor_labels_used(self):
        html = ('<a href="/seminar/detail/3">募集中</a>'
                '<a href="/seminar/detail/3">犬と猫の神経診療セミナー</a>'
                '<a href="/seminar/detail/3">2026/12/15 20:00～</a>'
                '<a href="/seminar/detail/3">LIVE</a>'
                '<div>申込締切 2026/12/01</div>'
                '<a href="/seminar/detail/4">募集終了</a>'
                '<a href="/seminar/detail/4">小動物整形外科セミナー</a>'
                '<a href="/seminar/detail/4">2026/12/18 10:00～</a>'
                '<a href="/seminar/detail/4">会場型</a>')
        _, text, _ = next(vets_academy_pages({"start_url": PAGE}, Fetcher(html)))
        events = extract_free("VETS ACADEMY", PAGE, "", text, TODAY, {})
        self.assertEqual([x["start_date"] for x in events],
                         ["2026-12-15", "2026-12-18"])
        self.assertTrue(all(x["deadline"] is None for x in events))


if __name__ == "__main__":
    unittest.main()
