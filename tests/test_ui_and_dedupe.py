# -*- coding: utf-8 -*-
"""Regression coverage for source dedupe and the empty-month UI."""
import pathlib
import unittest

import merge


class RadarUiAndDedupeTests(unittest.TestCase):
    def _e(self, title, eid, time="10:00", source="lifetail"):
        return {
            "id": eid, "source_id": source, "source": source,
            "title": title, "start_date": "2027-01-21",
            "end_date": None, "start_time": time, "end_time": None,
            "topics": [], "audience": [], "verified": True,
            "url": "https://example.org/session/" + eid,
        }

    def test_two_sessions_from_same_provider_are_not_collapsed(self):
        a = self._e("博多内視鏡セミナー 午前の部", "morning", "10:00")
        b = self._e("博多内視鏡セミナー 午後の部", "afternoon", "14:30")
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 2)

    def test_same_day_same_provider_identical_title_but_distinct_url(self):
        a = self._e("犬猫の実習セミナー", "session-one")
        b = self._e("犬猫の実習セミナー", "session-two")
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 2)

    def test_different_sources_same_title_and_date_can_merge(self):
        a = self._e("犬猫の実習セミナー", "a", "10:00", "lifetail")
        b = self._e("犬猫の実習セミナー", "b", "10:00", "partner")
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 1)

    def test_different_sources_different_time_do_not_merge(self):
        a = self._e("犬猫の実習セミナー", "a", "10:00", "lifetail")
        b = self._e("犬猫の実習セミナー", "b", "14:30", "partner")
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 2)

    def test_same_url_same_date_same_time_duplicate_display_once(self):
        a = self._e("満席 海外実習inバンコク｜外科実習 第1回 德永 暁 先生", "a")
        b = self._e("満席 海外実習inバンコク｜外科実習 第1回 / 德永 暁 先生", "b")
        a["url"] = "https://life-tail.com/seminars/1761/?utm_source=listing"
        b["url"] = "https://life-tail.com/seminars/1761/"
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 1)

    def test_same_url_different_dates_are_separate_series_sessions(self):
        a = self._e("犬猫の栄養学講座", "one")
        b = self._e("犬猫の栄養学講座", "two")
        a["url"] = b["url"] = "https://life-tail.com/seminars/1700/"
        b["start_date"] = "2027-02-21"
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 2)

    def test_same_url_different_times_remain_independent(self):
        a = self._e("内視鏡実習 午前", "one", "10:00")
        b = self._e("内視鏡実習 午後", "two", "14:30")
        a["url"] = b["url"] = "https://life-tail.com/seminars/1800/"
        self.assertEqual(len(merge.dedupe_cross_source([a, b])), 2)

    def test_series_label_and_compact_title_hook(self):
        html = pathlib.Path("template.html").read_text(encoding="utf-8")
        self.assertIn("function otherSessions(e)", html)
        self.assertIn("同じ講座の別日程", html)
        self.assertIn("function displayTitle(e)", html)

    def test_jump_button_is_distinct_from_header_button(self):
        html = pathlib.Path("template.html").read_text(encoding="utf-8")
        self.assertIn('el("button", "jumpbtn"', html)
        self.assertIn('.jumpbtn {', html)
        self.assertIn("var hasCurrentMonth = upcoming.some", html)
        self.assertIn(".monthnav .iconbtn, .monthnav .textbtn", html)


if __name__ == "__main__":
    unittest.main()
