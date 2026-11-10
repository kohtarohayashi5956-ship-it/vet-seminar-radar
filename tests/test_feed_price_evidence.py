# -*- coding: utf-8 -*-
"""Do not confuse free live entry with paid extras or free membership tiers."""
import unittest

from free_extract import _feed_price


class FeedPriceEvidenceTests(unittest.TestCase):
    def test_free_with_replay_period(self):
        self.assertEqual(
            _feed_price("参加費\n無料（見逃し配信10日間）\n※資料販売1,500円"),
            ("無料", True))

    def test_explicit_free_with_replay_weeks(self):
        self.assertEqual(
            _feed_price("参加費：無料（見逃し配信2週間）"),
            ("無料", True))

    def test_free_membership_is_not_event_free(self):
        price, is_free = _feed_price("参加費：無料会員2,000円／有料会員1,500円")
        self.assertIsNone(is_free)
        self.assertIn("2,000円", price)

    def test_paid_price_in_same_field_takes_precedence(self):
        price, is_free = _feed_price("参加費：無料体験あり、通常2,000円")
        self.assertIsNone(is_free)
        self.assertIn("2,000円", price)

    def test_unlabelled_promotion_is_not_fee(self):
        self.assertEqual(_feed_price("無料資料プレゼント\n別途案内"), (None, None))

    def test_other_replay_duration_does_not_imply_free(self):
        self.assertEqual(_feed_price("見逃し配信2週間"), (None, None))


if __name__ == "__main__":
    unittest.main()
