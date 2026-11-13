# -*- coding: utf-8 -*-
"""Regression checks for course-feed grouping and viewing-window labels."""
import pathlib
import unittest

TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "template.html"


class CertificationUiSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template = TEMPLATE.read_text(encoding="utf-8")

    def test_certification_course_sources_are_mapped_to_their_fields(self):
        self.assertIn('javnu_cert: "腎・泌尿器"', self.template)
        self.assertIn('jsvd_cert: "皮膚科"', self.template)
        self.assertIn('groups[e.source_id] || "その他"', self.template)

    def test_on_demand_course_dates_have_explicit_viewing_period_label(self):
        self.assertIn('e.format === "オンデマンド" && e.end_date ? "視聴期間：" + dateText(e)', self.template)
        self.assertIn('meta.appendChild(el("span", "cert-date"', self.template)


if __name__ == "__main__":
    unittest.main()
