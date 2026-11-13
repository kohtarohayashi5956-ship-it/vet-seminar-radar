# -*- coding: utf-8 -*-
"""JAHA dog-instructor prices: do not borrow tiers or adjacent seminars."""
import unittest

from jaha_enrich import _dog_lecture_fee, parse_jaha_detail

URL2 = "https://www.jaha.or.jp/owners/dog-training/kougi2_ol/"
URL3 = "https://www.jaha.or.jp/owners/dog-training/kougi3ol/"
FEES = """受講料
（２回通し料金・税込）
通常受講：一般料金19,800円、JAHA会員16,500円、学生料金9,900円
単発受講：一般料金22,000円、JAHA会員18,700円
JAHA入会のお手続きはこちら
"""
SPLIT = """受講料
（２回通し料金・税込）
通常受講：
一般料金19,800円、JAHA会員16,500円、学生料金9,900円
単発受講：
一般料金22,000円、JAHA会員18,700円
JAHA入会のお手続きはこちら
"""
SCHEDULE = """講義２はZoomによるオンライン開催です
2026年12月5日、12月12日の２回に分けて配信
パート１ 12月5日 14:00-17:00
パート２ 12月12日 14:00-17:00
"""


def event(number=2, url=URL2, date="2026-12-05"):
    return {"url": url, "title": f"家庭犬のしつけ方講座 講義{number}",
            "start_date": date, "price": None, "format": None,
            "start_time": None, "end_time": None, "deadline": None}


class DogLectureFeeTests(unittest.TestCase):
    def test_compact_rows(self):
        price = _dog_lecture_fee(FEES.splitlines(), event())
        self.assertEqual(price,
                         "2回通し：一般 19,800円／JAHA会員 16,500円／"
                         "学生 9,900円／単発：一般 22,000円／JAHA会員 18,700円")

    def test_split_rows(self):
        price = _dog_lecture_fee(SPLIT.splitlines(), event())
        self.assertEqual(price, _dog_lecture_fee(FEES.splitlines(), event()))
        out = parse_jaha_detail(SCHEDULE + SPLIT, event())
        self.assertEqual(out.get("price"), price)

    def test_label_amounts_in_separate_text_cells(self):
        fragmented = """受講料
通常受講
一般料金
19,800円
JAHA会員
16,500円
学生料金
9,900円
単発受講
一般料金
22,000円
JAHA会員
18,700円
お申し込み
"""
        self.assertEqual(_dog_lecture_fee(fragmented.splitlines(), event()),
                         _dog_lecture_fee(FEES.splitlines(), event()))

    def test_missing_student_amount_does_not_infer(self):
        fragmented = """受講料
通常受講
一般料金
19,800円
JAHA会員
16,500円
学生料金
単発受講
一般料金
22,000円
JAHA会員
18,700円
お申し込み
"""
        self.assertIsNone(_dog_lecture_fee(fragmented.splitlines(), event()))

    def test_lecture_three_uses_exact_official_page(self):
        self.assertEqual(_dog_lecture_fee(FEES.splitlines(),
                         event(3, URL3, "2026-11-14")),
                         _dog_lecture_fee(FEES.splitlines(), event()))

    def test_wrong_number_or_url_never_borrows(self):
        self.assertIsNone(_dog_lecture_fee(FEES.splitlines(), event(3, URL2)))
        self.assertIsNone(_dog_lecture_fee(FEES.splitlines(),
                          event(2, "https://www.jaha.or.jp/owners/dog-training/other/")))

    def test_missing_tier_is_not_guessed(self):
        bad = SPLIT.replace("単発受講：\n一般料金22,000円、JAHA会員18,700円", "")
        self.assertIsNone(_dog_lecture_fee(bad.splitlines(), event()))

    def test_stop_before_next_section(self):
        bad = SPLIT.replace("単発受講：\n一般料金22,000円、JAHA会員18,700円",
                            "JAHA入会のお手続きはこちら\n単発受講：\n一般料金22,000円、JAHA会員18,700円")
        self.assertIsNone(_dog_lecture_fee(bad.splitlines(), event()))

    def test_duplicate_fee_heading_is_ambiguous(self):
        self.assertIsNone(_dog_lecture_fee((FEES + FEES).splitlines(), event()))

    def test_duplicate_tier_amount_is_ambiguous(self):
        bad = FEES.replace("一般料金19,800円、JAHA会員16,500円",
                           "一般料金19,800円、一般料金20,000円、JAHA会員16,500円")
        self.assertIsNone(_dog_lecture_fee(bad.splitlines(), event()))

    def test_existing_fee_remains_unmodified(self):
        e = event()
        e["price"] = "公式別資料の料金"
        self.assertNotIn("price", parse_jaha_detail(SCHEDULE + FEES, e))


if __name__ == "__main__":
    unittest.main()
