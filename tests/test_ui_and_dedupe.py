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

    def test_jump_button_is_distinct_from_header_button(self):
        html = pathlib.Path("template.html").read_text(encoding="utf-8")
        self.assertIn('el("button", "jumpbtn"', html)
        self.assertIn('.jumpbtn {', html)
        self.assertIn("var hasCurrentMonth = upcoming.some", html)
        self.assertIn(".monthnav .iconbtn, .monthnav .textbtn", html)


if __name__ == "__main__":
    unittest.main()
