# -*- coding: utf-8 -*-
"""Gakusai hands-on course format must follow explicit card titles."""
import datetime
import unittest
from free_extract import _gakusai

PAGE = "https://www.gakusai.co.jp/doubutu/seminar-comingup/"
TODAY = datetime.date(2026, 11, 13)


def cards(*titles):
    rows = ["2027年 セミナー"]
    for i, title in enumerate(titles, 1):
        rows.extend([f"No. {i} {title}", f"2027年 {i}月 15日"])
    return "\n".join(rows)


class GakusaiWetLabTests(unittest.TestCase):
    def test_explicit_wet_lab(self):
        got = _gakusai(cards(
            "原康先生 小型犬の頸部椎間板ヘルニアに対する外科治療：Wet Lab"
        ), PAGE, TODAY)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["format"], "現地")

    def test_explicit_wet_and_dry_lab(self):
        got = _gakusai(cards(
            "原康先生 小型犬の膝蓋骨脱臼整復：Wet & Dry Lab"
        ), PAGE, TODAY)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["format"], "現地")

    def test_general_seminar_not_inferred_in_person(self):
        got = _gakusai(cards("猫の画像診断セミナー"), PAGE, TODAY)
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["format"])

    def test_separate_card_has_no_format_leak(self):
        got = _gakusai(cards("Wet Lab 整形外科実習", "猫の歯科セミナー"),
                       PAGE, TODAY)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["format"], "現地")
        self.assertIsNone(got[1]["format"])


if __name__ == "__main__":
    unittest.main()
