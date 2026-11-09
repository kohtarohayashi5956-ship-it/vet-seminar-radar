# -*- coding: utf-8 -*-
"""Calendar-date validation regression tests for public seminar records."""
import unittest

from validate_public import valid_calendar_date


class PublicCalendarDateTests(unittest.TestCase):
    def test_existing_dates(self):
        for date in ("2026-11-09", "2028-02-29", "2027-01-01"):
            with self.subTest(date=date):
                self.assertTrue(valid_calendar_date(date))

    def test_impossible_dates(self):
        for date in ("2027-02-29", "2026-02-30", "2026-13-01",
                     "2026-00-01", "2026-04-31"):
            with self.subTest(date=date):
                self.assertFalse(valid_calendar_date(date))

    def test_malformed_or_missing_dates(self):
        for value in (None, "", "2026/11/09", "2026-1-09",
                      "2026-11-9", "2026-11-09T10:00:00", 20261109):
            with self.subTest(value=value):
                self.assertFalse(valid_calendar_date(value))


if __name__ == "__main__":
    unittest.main()
