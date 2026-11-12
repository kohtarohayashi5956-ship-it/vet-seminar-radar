# -*- coding: utf-8 -*-
"""Conservatively recover a same-event wrapped Gakusai time range."""
import unittest

from gakusai_enrich import parse_gakusai


EVENT = {
    "start_date": "2027-03-07",
    "start_time": None,
    "end_time": None,
    "format": "現地",
    "price": None,
    "venue": None,
    "audience": [],
}


def detail(schedule):
    return ("開催日時・会場\n" + schedule +
            "\n来場受講料\n一般獣医師 27,000円\nウェブ受講料\n")


class GakusaiWrappedTimeTests(unittest.TestCase):
    def test_exact_date_wrapped_range(self):
        result = parse_gakusai(detail(
            "東京会場 2027年3月7日（日）\n10:00～16:00\n駐健保会館"
        ), dict(EVENT))
        self.assertEqual((result.get("start_time"), result.get("end_time")),
                         ("10:00", "16:00"))

    def test_fullwidth_clock_wrapped_range(self):
        result = parse_gakusai(detail(
            "東京会場 2027年3月7日（日）\n10：00～16：00"
        ), dict(EVENT))
        self.assertEqual((result.get("start_time"), result.get("end_time")),
                         ("10:00", "16:00"))

    def test_different_date_never_borrows(self):
        result = parse_gakusai(detail(
            "東京会場 2027年3月8日（月）\n10:00～16:00"
        ), dict(EVENT))
        self.assertEqual(result, {})

    def test_other_labelled_time_never_borrows(self):
        result = parse_gakusai(detail(
            "東京会場 2027年3月7日（日）\n受付時間 9:00～10:00"
        ), dict(EVENT))
        self.assertIsNone(result.get("start_time"))

    def test_several_dates_never_borrows(self):
        result = parse_gakusai(detail(
            "東京会場 2027年3月7日（日）、2027年3月8日（月）\n10:00～16:00"
        ), dict(EVENT))
        self.assertEqual(result, {})

    def test_existing_clock_is_never_overwritten(self):
        event = dict(EVENT, start_time="09:00")
        result = parse_gakusai(detail(
            "東京会場 2027年3月7日（日）\n10:00～16:00"
        ), event)
        self.assertEqual(result, {})


if __name__ == "__main__":
    unittest.main()
