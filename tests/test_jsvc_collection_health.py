# -*- coding: utf-8 -*-
"""JSVC registration completeness must appear in per-source collection health."""
import datetime
import pathlib
import unittest

from society_enrich import enrich_jsvc
from test_jsvc_registration_enrichment import EVENT, FakeFetcher


class JSVCCollectionHealthTests(unittest.TestCase):
    def test_completed_fetch_counts_proven_fields(self):
        stats = {}
        row = dict(EVENT)
        enrich_jsvc([row], FakeFetcher(), datetime.date(2026, 11, 13), stats)
        self.assertEqual(stats["certification_programs_found"], 1)
        self.assertEqual(stats["registration_details_scanned"], 1)
        self.assertEqual(stats["registration_prices_found"], 1)
        self.assertEqual(stats["registration_abstract_deadlines_found"], 1)
        self.assertNotIn("registration_detail_failed", stats)

    def test_failed_registration_is_explicit_and_nonfatal(self):
        stats = {}
        row = dict(EVENT)
        enrich_jsvc([row], FakeFetcher(missing=True),
                    datetime.date(2026, 11, 13), stats)
        self.assertEqual(stats["certification_programs_found"], 1)
        self.assertEqual(stats["registration_detail_failed"], 1)
        self.assertNotIn("registration_prices_found", stats)
        self.assertNotIn("registration_abstract_deadlines_found", stats)

    def test_health_export_has_all_registration_fields(self):
        source = (pathlib.Path(__file__).resolve().parents[1] / "run.py").read_text(
            encoding="utf-8"
        )
        for field in (
            "certification_programs_found",
            "registration_details_scanned",
            "registration_prices_found",
            "registration_abstract_deadlines_found",
            "registration_detail_failed",
        ):
            with self.subTest(field=field):
                self.assertIn(f'"{field}": stats.get("{field}", 0)', source)


if __name__ == "__main__":
    unittest.main()
