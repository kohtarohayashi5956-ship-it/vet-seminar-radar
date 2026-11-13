# -*- coding: utf-8 -*-
"""Published event clocks must be precise and tied to a known date."""
import unittest

from validate_public import valid_clock_time, validate_event_clock


class PublishedClockValidationTests(unittest.TestCase):
    def test_valid_24_hour_times(self):
        for value in ("00:00", "09:05", "13:00", "23:59"):
            with self.subTest(value=value):
                self.assertTrue(valid_clock_time(value))

    def test_reject_invalid_and_imprecise_times(self):
        for value in ("25:00", "12:60", "9:00", "13：00", "13時", "", None, 1300):
            with self.subTest(value=value):
                self.assertFalse(valid_clock_time(value))

    def test_dated_event_with_single_start(self):
        validate_event_clock({"start_date": "2026-12-07",
                              "start_time": "13:00", "end_time": None})

    def test_dated_event_with_start_and_end(self):
        validate_event_clock({"start_date": "2026-12-07",
                              "start_time": "13:00", "end_time": "15:00"})

    def test_reject_end_without_start(self):
        with self.assertRaisesRegex(AssertionError, "end time without start"):
            validate_event_clock({"start_date": "2026-12-07",
                                  "start_time": None, "end_time": "15:00"})

    def test_reject_start_without_date(self):
        with self.assertRaisesRegex(AssertionError, "without event date"):
            validate_event_clock({"start_date": None,
                                  "start_time": "13:00", "end_time": None})

    def test_reject_bad_start_or_end(self):
        for start, end in (("13:80", None), ("13:00", "26:00")):
            with self.subTest(start=start, end=end):
                with self.assertRaisesRegex(AssertionError, "invalid published clock"):
                    validate_event_clock({"start_date": "2026-12-07",
                                          "start_time": start, "end_time": end})

    def test_overnight_event_is_not_assumed_wrong(self):
        validate_event_clock({"start_date": "2026-12-07",
                              "start_time": "23:00", "end_time": "01:00"})


if __name__ == "__main__":
    unittest.main()
