# -*- coding: utf-8 -*-
"""On-demand ranges must be labelled as viewing periods for readers."""
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class OnDemandViewingPeriodUITests(unittest.TestCase):
    def test_cards_mark_recorded_date_ranges(self):
        html = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn('e.format === "オンデマンド" && e.start_date && e.end_date', html)
        self.assertIn('kvs.appendChild(kv("視聴期間", dateText(e)))', html)

    def test_shared_announcement_marks_viewing_period_not_event_day(self):
        html = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertIn('e.format === "オンデマンド" && multi ? "視聴期間：" : ""', html)
        self.assertIn('var line1 = "■ "', html)

    def test_only_on_demand_ranges_get_special_label(self):
        html = (ROOT / "template.html").read_text(encoding="utf-8")
        self.assertNotIn('kvs.appendChild(kv("視聴期間", md(e.start_date)))', html)


if __name__ == "__main__":
    unittest.main()
