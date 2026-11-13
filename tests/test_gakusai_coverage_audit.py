# -*- coding: utf-8 -*-
"""Gakusai listing coverage: warnings, not inferred seminar records."""
import datetime
import pathlib
import unittest

from free_extract import extract_free
from gakusai_coverage import uncovered_gakusai_lectures

PAGE = "https://www.gakusai.co.jp/doubutu/seminar-comingup/"
TEXT = """2027 セミナー 開催スケジュール
1月
No.297 高木哲先生「失敗しない腸管吻合 ミニドライラボ&セミナー」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35591/>
1月24日（日）東京｜ウェブ受講（3月1日～）
3月
No.298 手島健次先生「明日から使える！ 犬と猫の局所麻酔セミナー」 »詳細はこちら <https://www.gakusai.co.jp/vet/vet-seminar/35589/>
3月7日（日）東京｜ウェブ受講（4月1日～）
No.299 日時が未掲載のセミナー
No.300 翌年のオンライン配信だけの案内
ウェブ受講（12月1日～）
MS153 腹部超音波実習
3月21日（日）東京
"""


class NumberedCoverageTests(unittest.TestCase):
    def test_complete_listing_is_not_flagged(self):
        got = extract_free("学際企画", PAGE, "", TEXT,
                           datetime.date(2026, 11, 13), {})
        self.assertEqual(uncovered_gakusai_lectures(TEXT, got), [])

    def test_missing_first_lecture_is_flagged(self):
        got = extract_free("学際企画", PAGE, "", TEXT,
                           datetime.date(2026, 11, 13), {})
        no297 = [x for x in got if "腸管吻合" not in x["title"]]
        self.assertEqual(uncovered_gakusai_lectures(TEXT, no297), ["297"])

    def test_web_date_and_undated_do_not_trigger(self):
        self.assertEqual(uncovered_gakusai_lectures(
            "2027 セミナー\nNo.299 日時が未掲載のセミナー\n"
            "No.300 ウェブ受講（3月1日～)\nMS153 実習\n3月21日 東京", []), [])

    def test_health_report_includes_gap_field(self):
        run = (pathlib.Path(__file__).resolve().parents[1] / "run.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("uncovered_gakusai_lectures(text, got)", run)
        self.assertIn('"listing_lectures_uncovered": stats.get(', run)


if __name__ == "__main__":
    unittest.main()
