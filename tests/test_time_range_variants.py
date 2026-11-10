# -*- coding: utf-8 -*-
"""Time-range punctuation variants must preserve strict clock validation."""
import unittest

from free_extract import _times


class TimeRangeVariantTests(unittest.TestCase):
    def test_ascii_time_range_unchanged(self):
        self.assertEqual(_times("開催日時：14:00～16:30"), ("14:00", "16:30"))

    def test_fullwidth_colons(self):
        self.assertEqual(_times("開催日時：14：00～16：30"), ("14:00", "16:30"))

    def test_mixed_colons(self):
        self.assertEqual(_times("日時：9：05〜11:20"), ("09:05", "11:20"))

    def test_invalid_hours_and_minutes(self):
        self.assertEqual(_times("開催日時：25：00～26：00"), (None, None))
        self.assertEqual(_times("開催日時：14：70～16：30"), (None, None))

    def test_single_time_is_not_guessed_as_range(self):
        self.assertEqual(_times("日時：14：00開始"), (None, None))


if __name__ == "__main__":
    unittest.main()
