# -*- coding: utf-8 -*-
"""The JAVNU programme-fee page must never be confused with course fees."""
from pathlib import Path
import unittest


class JavnuOfficialFeeLinkTests(unittest.TestCase):
    def test_official_programme_fee_link_is_separate(self):
        html = (Path(__file__).resolve().parents[1] / "template.html").read_text(encoding="utf-8")
        self.assertIn('if (e.source_id === "javnu_cert")', html)
        self.assertIn('fees.href = "https://www.javnu.jp/certification/fee/"', html)
        self.assertIn("認定制度の費用を確認（講座受講料とは別）", html)
        self.assertIn('var feeText = e.price || (e.is_free === true ? "無料" : "未取得（公式確認）");', html)
        self.assertNotIn('e.price = "10,000円"', html)


if __name__ == "__main__":
    unittest.main()
