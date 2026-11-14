# -*- coding: utf-8 -*-
"""On-demand certification viewing periods are not registration deadlines."""
from pathlib import Path
import unittest


class CertificationViewingPeriodTests(unittest.TestCase):
    def test_viewing_end_is_separate_from_application_deadline(self):
        template = (Path(__file__).resolve().parents[1] / "template.html").read_text(encoding="utf-8")
        self.assertIn('if (e.format === "オンデマンド" && e.end_date)', template)
        self.assertIn('var remaining = deadlineDays(e.end_date);', template)
        self.assertIn('"視聴期限：" + fullDate(e.end_date)', template)
        self.assertIn('remaining > 0 && remaining <= 14', template)
        self.assertIn('certRegistrationStatus(e.deadline, "参加申込締切")', template)
        self.assertNotIn('certRegistrationStatus(e.end_date, "参加申込締切")', template)
        self.assertIn('e.is_free === true ? "無料" : "未取得（公式確認）"', template)
        self.assertIn('"受講料：" + feeText', template)


if __name__ == "__main__":
    unittest.main()
