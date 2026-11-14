# -*- coding: utf-8 -*-
"""Official lecturer lines belong only to the immediately preceding JAVNU course."""
import datetime
import unittest
from free_extract import _javnu_certification

URL = "https://www.javnu.jp/certification/schedule/"


class JavnuSpeakersTests(unittest.TestCase):
    def test_extracts_adjacent_lecturer_without_borrowing_other_names(self):
        page = "\n".join([
            "現在の講習会スケジュール", "第3期（2026年度〜）",
            "2026年10月1日〜12月15日", "配信中",
            "オンライン認定講習会（第3期カリキュラム）",
            "05", "腎泌尿器の画像診断 1",
            "華園 究 先生（ライフメイト動物医療センター）",
            "06", "腎泌尿器の画像診断 2",
            "前半：華園 究 先生（ライフメイト動物医療センター） 後半：山﨑 寛文 先生（日本動物高度医療センター）",
            "2027年1月10日〜2028年3月31日", "配信予定",
            "オンライン認定講習会（第3期カリキュラム）",
            "27", "時事トピック（第1回）", "講師調整中",
            "学会について",
        ])
        rows = _javnu_certification(page, URL, datetime.date(2026, 11, 14), {})
        self.assertEqual(len(rows), 3)
        speakers = {r["title"].split("：")[0][-2:]: r.get("speaker") for r in rows}
        self.assertIn("華園 究 先生", speakers["05"])
        self.assertIn("山﨑 寛文 先生", speakers["06"])
        self.assertIsNone(speakers["27"])
        self.assertTrue(all(r["deadline"] is None for r in rows))


if __name__ == "__main__":
    unittest.main()
