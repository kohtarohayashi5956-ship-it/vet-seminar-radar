# -*- coding: utf-8 -*-
"""Offline contract for multi-term specialty and certification-course lookup."""
from pathlib import Path
import unittest


class CertificationSearchTests(unittest.TestCase):
    def test_searches_all_official_course_and_specialty_fields(self):
        html = (Path(__file__).resolve().parents[1] / "template.html").read_text(encoding="utf-8")
        self.assertIn("var terms = norm(q).split(", html)
        self.assertIn("return terms.every(function (term)", html)
        self.assertIn("e.certification_program,", html)
        self.assertIn("e.source, e.organizer, e.speaker, certArea(e)", html)
        self.assertIn("var courseTerms = terms.filter(", html)
        self.assertIn("courseTerms.some(function (term)", html)
        self.assertIn("function certSearchMatch(e, q)", html)


if __name__ == "__main__":
    unittest.main()
