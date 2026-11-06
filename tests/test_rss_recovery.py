# -*- coding: utf-8 -*-
"""Malformed RSS must not permanently interrupt a previously working source."""
import unittest
from sources import feed_pages
from extract import html_to_text

FEED="https://vets-tech.jp/feed/"

class FakeFetcher:
    def __init__(self, value): self.value=value
    def get(self,url):
        if url != FEED:
            raise ValueError("unexpected detail request")
        return self.value

class RSSRecoveryTests(unittest.TestCase):
    def test_valid_item_in_malformed_feed(self):
        xml = """<?xml version="1.0"?><rss><channel>
          <item><title>【ライブ】犬猫の臨床セミナー</title>
          <link>https://vets-tech.jp/post/1/</link>
          <pubDate>Thu, 05 Nov 2026 10:00:00 +0000</pubDate>
          <category>セミナー</category>
          <description><![CDATA[日時: 2026年11月11日21:00開催]]></description>
          </item><invalid></channel></rss>"""
        src={"id":"vetstech","kind":"wp_feed","feed":FEED,"category_contains":"セミナー",
             "max_age_days":120,"max_items":40}
        out=list(feed_pages(src,FakeFetcher(xml)))
        self.assertEqual(len(out),1)
        self.assertIn("犬猫の臨床セミナー",out[0][1])
        self.assertIn("2026年11月11日",out[0][1])
    def test_html_with_no_rss_items_is_not_accepted(self):
        src={"id":"vetstech","feed":FEED,"category_contains":"セミナー",
             "max_age_days":120}
        with self.assertRaises(ValueError):
            list(feed_pages(src,FakeFetcher("<html><h1>Error</h1></html>")))

if __name__=="__main__":unittest.main()
