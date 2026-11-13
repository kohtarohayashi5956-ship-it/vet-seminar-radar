# -*- coding: utf-8 -*-
"""Mandatory materials fee belongs only to No.297 on-site participants."""
import unittest

from gakusai_enrich import _no297_material_fee, parse_gakusai

DETAIL = "https://www.gakusai.co.jp/vet/vet-seminar/35591/"
BASE = ("法人・個人会員 9,000円(税込9,900円)／"
        "一般獣医師 27,000円(税込29,700円)")
ROWS = """No.297 失敗しない腸管吻合 ミニドライラボ&セミナー
開催日時・会場
東京会場 2027年1月24日（日）10：00～16：00
駐健保会館
来場受講料
テキスト付き・ウェブ受講1ヶ月付き（2027.3/1〜3/31）
法人・個人会員 | 9,000円（税込9,900円）＋ミニドライラボ材料費 4,500円（税込4,950円）
一般獣医師 | 27,000円（税込29,700円）＋ミニドライラボ材料費 4,500円（税込4,950円）
※このセミナーは、申込時に下記材料費が加算されます。
ミニドライラボ材料費：4,500円（税込4,950円）
ウェブ受講料
法人・個人会員 | 9,000円（税込9,900円）
一般獣医師 | 27,000円（税込29,700円）
"""
def event():
    return {"title": "失敗しない腸管吻合 ミニドライラボ&セミナー",
            "url": DETAIL, "start_date": "2027-01-24", "format": "現地",
            "price": BASE, "start_time": "10:00", "end_time": "16:00"}


class No297FeeTests(unittest.TestCase):
    def test_mandatory_material_fee_added_to_existing_base_price(self):
        result = parse_gakusai(ROWS, event())
        self.assertIn("ミニドライラボ材料費 4,500円(税込4,950円)", result["price"])
        self.assertEqual(result["price"].count("材料費"), 2)
        self.assertIn("9,000円", result["price"])
        self.assertIn("27,000円", result["price"])

    def test_wrong_date_or_title_rejected(self):
        for change in ({"start_date": "2027-01-25"}, {"title": "別講座"}):
            self.assertIsNone(_no297_material_fee(ROWS.splitlines(),
                                                   dict(event(), **change)))

    def test_web_only_variant_not_on_site_materials(self):
        self.assertIsNone(_no297_material_fee(ROWS.splitlines(),
                          dict(event(), format="オンデマンド")))

    def test_missing_material_fee_does_not_guess(self):
        self.assertIsNone(_no297_material_fee(
            ROWS.replace("申込時に下記材料費が加算", "材料費について").splitlines(), event()))

    def test_existing_conflicting_price_not_overwritten(self):
        self.assertIsNone(_no297_material_fee(
            ROWS.splitlines(), dict(event(), price="独立に確認した料金 12,000円")))


if __name__ == "__main__":
    unittest.main()
