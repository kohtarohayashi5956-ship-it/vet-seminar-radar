# -*- coding: utf-8 -*-
"""Certification diagnostics must not infer missing fees, dates or clock times."""
import unittest
from quality import summarize_certification_quality


class CertificationQualityTests(unittest.TestCase):
    def test_counts_appropriate_fields_by_source(self):
        items = [
            {"source_id": "javnu_cert", "certification_program": "講座05",
             "format": "オンデマンド", "start_date": "2026-10-01",
             "end_date": "2026-12-15", "price": None, "deadline": None},
            {"source_id": "jsvc", "certification_note": "認定医講習会",
             "format": "現地", "start_date": "2026-12-19",
             "start_time": "10:00", "price": "10,000円", "deadline": None},
            {"source_id": "jbvp", "title": "認定とは無関係", "price": "無料"},
        ]
        report = summarize_certification_quality(items)
        self.assertEqual(report["total"], 2)
        self.assertEqual(list(report["by_source"]), ["javnu_cert", "jsvc"])
        kidney = report["by_source"]["javnu_cert"]
        self.assertEqual(kidney["on_demand"], 1)
        self.assertEqual(kidney["not_applicable"]["start_time"], 1)
        self.assertEqual(kidney["known"]["end_date"], 1)
        self.assertEqual(kidney["known"]["start_time"], 0)
        self.assertEqual(kidney["known"]["price"], 0)
        self.assertEqual(kidney["known"]["deadline"], 0)
        heart = report["by_source"]["jsvc"]
        self.assertEqual(heart["known"]["start_time"], 1)
        self.assertEqual(heart["known"]["price"], 1)

    def test_empty_report(self):
        report = summarize_certification_quality([])
        self.assertEqual(report["total"], 0)
        self.assertEqual(report["by_source"], {})


if __name__ == "__main__":
    unittest.main()
