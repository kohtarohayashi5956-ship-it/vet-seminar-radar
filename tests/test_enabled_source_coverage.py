# -*- coding: utf-8 -*-
"""The enabled commercial teaching sources must use explicit safe adapters."""
import datetime
import unittest
import config
from sources import pages_for
from free_extract import extract_free

NOW = datetime.date(2026, 11, 9)

class Dummy:
    def __init__(self, html):
        self.html = html
        self.calls = []
    def get(self, url):
        self.calls.append(url)
        return self.html


class SourceCoverageTests(unittest.TestCase):
    def test_all_three_sources_enabled_and_specific(self):
        sources = {s["id"]: s for s in config.SOURCES}
        self.assertEqual(sources["peppy"]["kind"], "peppy_list")
        self.assertEqual(sources["academy"]["kind"], "vets_academy_list")
        self.assertEqual(sources["eduone"]["kind"], "eduone_lecture")
        for name in ("peppy", "academy", "eduone"):
            self.assertTrue(sources[name]["enabled"])

    def test_eduward_listing_without_official_detail_does_not_invent(self):
        source = {"kind": "eduone_lecture", "start_url": "https://eduone.jp/lecture/",
                  "max_details": 3}
        f = Dummy('<main><h1>WEB講演会</h1><p>2026年11月24日 無料</p></main>')
        pages = list(pages_for(source, f, 3))
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0][1], "")
        self.assertIn("詳細リンクなし", pages[0][2])
        self.assertEqual(f.calls, ["https://eduone.jp/lecture/"])

    def test_academy_cards_stay_event_specific(self):
        source = {"kind": "vets_academy_list", "start_url": "https://academy.eduone.jp/seminar"}
        html = ('<a href="/seminar/detail/10288">募集中</a>'
                '<a href="/seminar/detail/10288">シニアペットに寄り添う認知症対策</a>'
                '<a href="/seminar/detail/10288">2026/11/30 ～2027/01/25</a>'
                '<a href="/seminar/detail/10288">オンデマンド</a>'
                '<a href="/seminar/detail/10288">動物看護</a>')
        url, text, hint = next(pages_for(source, Dummy(html), 3))
        result = extract_free("VETS ACADEMY", url, hint, text, NOW, {})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start_date"], "2026-11-30")
        self.assertEqual(result[0]["end_date"], "2027-01-25")
        self.assertIsNone(result[0]["deadline"])

if __name__ == "__main__":
    unittest.main()
