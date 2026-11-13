# -*- coding: utf-8 -*-
"""Official JAVNU curriculum viewing windows: exact dates and course numbers."""
import datetime
import unittest

from free_extract import extract_free

URL = "https://www.javnu.jp/certification/schedule/"
TODAY = datetime.date(2026, 11, 13)
PAGE = """現在の講習会スケジュール
第3期（2026年度〜）で現在行っている認定講習会のスケジュールです。
2026年6月8日〜8月15日
配信終了
オンライン認定講習会（第3期カリキュラム）
01
泌尿器の発生とその異常および解剖・組織
2026年10月1日〜12月15日
配信中
オンライン認定講習会（第3期カリキュラム）
05
腎泌尿器の画像診断 1
華園 究 先生
2026年10月1日〜12月15日
配信中
オンライン認定講習会（第3期カリキュラム）
06
腎泌尿器の画像診断 2
2026年12月1日〜2027年2月15日
配信予定
オンライン認定講習会（第3期カリキュラム）
07
腎泌尿器系の病理組織診断 1：細胞診、腎生検
08
腎泌尿器系の病理組織診断 2：組織診
2027年1月10日〜2028年3月31日
配信予定
オンライン認定講習会（第3期カリキュラム）
12
腎臓の病気 3：尿細管間質疾患、中毒・薬剤性腎障害
27
時事トピック（第1回）
学会について
27
会長あいさつ
"""


def parse(page=PAGE, url=URL, day=TODAY):
    stats = {}
    found = extract_free("JAVNU認定講習会", url, "", page, day, stats)
    return found, stats


class JavnuScheduleTests(unittest.TestCase):
    def test_six_current_or_future_courses(self):
        out, stats = parse()
        self.assertEqual(len(out), 6)
        self.assertEqual(stats["javnu_certification_courses"], 6)
        self.assertEqual([e["certification_program"].split("：")[0]
                          for e in out],
                         ["第3期カリキュラム05", "第3期カリキュラム06",
                          "第3期カリキュラム07", "第3期カリキュラム08",
                          "第3期カリキュラム12", "第3期カリキュラム27"])
        self.assertEqual(out[0]["start_date"], "2026-10-01")
        self.assertEqual(out[0]["end_date"], "2026-12-15")
        self.assertEqual(out[2]["start_date"], "2026-12-01")
        self.assertEqual(out[2]["end_date"], "2027-02-15")
        self.assertEqual(out[-1]["end_date"], "2028-03-31")
        self.assertTrue(all(e["format"] == "オンデマンド" for e in out))
        self.assertTrue(all(e["start_time"] is None and
                            e["deadline"] is None for e in out))
        self.assertTrue(all("認定講習会" in e["certification_note"] for e in out))

    def test_completed_period_removed(self):
        out, _ = parse()
        self.assertNotIn("カリキュラム01", " ".join(e["title"] for e in out))

    def test_no_wrong_domain_or_page(self):
        out, _ = parse(url="https://www.javnu.jp/news/")
        self.assertEqual(out, [])

    def test_no_course_without_number(self):
        out, _ = parse(PAGE.replace("\n07\n", "\n講師\n"))
        self.assertEqual(len(out), 5)

    def test_registration_or_other_dates_not_mistaken(self):
        page = PAGE.replace(
            "2026年12月1日〜2027年2月15日",
            "2026年12月1日〜2027年2月15日\n申し込み締切：2026年11月30日"
        )
        out, _ = parse(page)
        self.assertTrue(all(e["deadline"] is None for e in out))

    def test_missing_schedule_marker_rejected(self):
        out, _ = parse(PAGE.replace("現在の講習会スケジュール",
                                    "ほかのページ"))
        self.assertEqual(out, [])

    def test_invalid_date_range_not_accepted(self):
        out, _ = parse(PAGE.replace("2026年10月1日〜12月15日",
                                    "2026年10月45日〜12月15日"))
        self.assertEqual(len(out), 4)


if __name__ == "__main__":
    unittest.main()
