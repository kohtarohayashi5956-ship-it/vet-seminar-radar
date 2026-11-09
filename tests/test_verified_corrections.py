# -*- coding: utf-8 -*-
"""Regression checks for conservative, source-verified corrections."""
import copy
import unittest

from verified_corrections import apply_verified_corrections

EID = "a27c399a72d1"
BASE = {
    "id": EID,
    "source_id": "vetstech",
    "start_date": "2026-11-11",
    "deadline": None,
    "url": "https://vets-tech.jp/2026/10/27/vets-tech-web-seminar-vol83/116565/?utm_source=rss",
}


class VerifiedCorrectionTests(unittest.TestCase):
    def test_replenishes_verified_deadline_after_recollection(self):
        store = {EID: copy.deepcopy(BASE)}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [EID])
        self.assertEqual(conflicts, [])
        self.assertEqual(store[EID]["deadline"], "2026-11-11")

    def test_no_overwrite_when_source_has_conflicting_deadline(self):
        item = copy.deepcopy(BASE)
        item["deadline"] = "2026-11-10"
        store = {EID: item}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [])
        self.assertEqual(conflicts, [EID])
        self.assertEqual(item["deadline"], "2026-11-10")

    def test_no_override_wrong_date(self):
        item = copy.deepcopy(BASE)
        item["start_date"] = "2026-11-12"
        store = {EID: item}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [])
        self.assertEqual(conflicts, [EID])
        self.assertIsNone(item["deadline"])

    def test_no_override_wrong_url(self):
        item = copy.deepcopy(BASE)
        item["url"] = "https://vets-tech.jp/another-seminar/"
        store = {EID: item}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [])
        self.assertEqual(conflicts, [EID])
        self.assertIsNone(item["deadline"])

    def test_idempotent_when_already_correct(self):
        item = copy.deepcopy(BASE)
        item["deadline"] = "2026-11-11"
        store = {EID: item}
        self.assertEqual(apply_verified_corrections(store), ([], []))


if __name__ == "__main__":
    unittest.main()
