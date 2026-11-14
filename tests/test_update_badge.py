# -*- coding: utf-8 -*-
"""The information-update badge must not claim official organizer changes."""
from pathlib import Path
import unittest


class UpdateBadgeTests(unittest.TestCase):
    def test_changed_fields_are_labeled_and_qualified(self):
        html = (Path(__file__).resolve().parents[1] / "template.html").read_text(encoding="utf-8")
        self.assertIn('var changed = (e.changed_fields || []).map(', html)
        for label in ('price: "受講料"', 'start_time: "開始時刻"',
                      'deadline: "参加申込締切"', 'abstract_deadline: "演題募集締切"'):
            self.assertIn(label, html)
        self.assertIn("主催者による変更とは断定できません", html)
        self.assertIn('revised.setAttribute("aria-label"', html)


if __name__ == "__main__":
    unittest.main()
