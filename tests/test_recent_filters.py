# -*- coding: utf-8 -*-
"""Regression test for independent / combined recent change filters."""
import pathlib
import unittest

PAGE = pathlib.Path(__file__).resolve().parents[1] / "template.html"


class RecentFiltersTests(unittest.TestCase):
    def test_recent_changed_checkbox_is_wired_everywhere(self):
        html = PAGE.read_text(encoding="utf-8")
        self.assertIn('id="fChanged"', html)
        self.assertIn('"fNew", "fChanged", "fHidePast"', html)
        self.assertIn('$("fChanged").checked = false;', html)
        self.assertIn('deadlineDays(e.last_changed) >= -7', html)
        self.assertIn('deadlineDays(e.last_changed) <= 0', html)
        self.assertIn('!isNew;', html)
        self.assertIn('($("fNew").checked && isNew) || ($("fChanged").checked && isChanged)', html)


if __name__ == "__main__":
    unittest.main()
