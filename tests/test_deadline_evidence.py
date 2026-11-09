# -*- coding: utf-8 -*-
"""Registration deadline evidence must be confined to its own field."""
import unittest

from free_extract import _explicit_deadline


class DeadlineEvidenceTests(unittest.TestCase):
    def test_date_same_line(self):
        self.assertEqual(
            _explicit_deadline("申込締切：2026年12月1日\n開催日時：2026年12月10日"),
            "2026-12-01",
        )

    def test_year_date_on_following_line(self):
        self.assertEqual(
            _explicit_deadline("申込締切：\n2026年12月1日\n開催日時：2026年12月10日"),
            "2026-12-01",
        )

    def test_event_date_following_empty_deadline_is_not_deadline(self):
        self.assertIsNone(
            _explicit_deadline("申込締切：\n開催日時：2026年12月10日"),
        )

    def test_other_dates_not_deadlines(self):
        self.assertIsNone(
            _explicit_deadline("録画配信：2026年12月10日\nキャンセル期限：2026年12月1日"),
        )


if __name__ == "__main__":
    unittest.main()
