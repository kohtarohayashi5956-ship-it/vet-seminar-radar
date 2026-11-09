# -*- coding: utf-8 -*-
"""Regression checks for free-admission classification.

Keep prices for mixed member/free/paid tiers and do not fabricate a
zero-price seminar from a free membership, gift or trial.
"""
import unittest

from free_extract import _feed_price, _price


class SeminarPriceClassificationTests(unittest.TestCase):
    def test_explicit_free_admission(self):
        self.assertEqual(_price("受講料：無料"), ("受講料：無料", True))
        self.assertEqual(_feed_price("参加費：無料"), ("無料", True))

    def test_mixed_paid_and_free_tiers_are_not_free(self):
        value = "受講料：会員無料／一般 3,000円"
        self.assertEqual(_price(value), (value, None))
        self.assertEqual(_feed_price(value), ("会員無料／一般 3,000円", None))

    def test_free_membership_is_not_free_admission(self):
        self.assertEqual(_price("受講料：無料会員 5,000円"), ("受講料：無料会員 5,000円", None))
        self.assertEqual(_feed_price("受講料：無料会員 5,000円"), ("無料会員 5,000円", None))

    def test_unrelated_free_word_is_not_a_fee(self):
        self.assertEqual(_feed_price("無料プレゼント付き\n受講料：4,000円"), ("4,000円", None))
        self.assertEqual(_price("無料プレゼント付き\n受講料：4,000円"), ("受講料：4,000円", None))

    def test_unknown_fees_remain_unknown(self):
        self.assertEqual(_price("受講料は後日案内"), (None, None))
        self.assertEqual(_feed_price("受講料は後日案内"), (None, None))


if __name__ == "__main__":
    unittest.main()
