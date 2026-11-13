# -*- coding: utf-8 -*-
"""Verified JAHA dates and time corrections must be strictly scoped."""
import copy
import unittest

from verified_corrections import apply_verified_corrections

URL = "https://www.jaha.or.jp/training/seminar/vnseries/aigan26deep3/"
ID = "89d5e9b970d0"

def event(start="2026-12-07", url=URL, start_time=None, end_time=None):
    return {"id": ID, "source_id": "jaha", "start_date": start,
            "url": url, "start_time": start_time, "end_time": end_time}

class VerifiedTimeTests(unittest.TestCase):
    def test_verified_two_times_filled(self):
        store = {ID: event()}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [ID])
        self.assertEqual(conflicts, [])
        self.assertEqual(store[ID]["start_time"], "13:00")
        self.assertEqual(store[ID]["end_time"], "15:00")

    def test_existing_correct_time_is_idempotent(self):
        store = {ID: event(start_time="13:00", end_time="15:00")}
        self.assertEqual(apply_verified_corrections(store), ([], []))

    def test_existing_conflicting_time_cannot_be_overwritten(self):
        store = {ID: event(start_time="09:00")}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [])
        self.assertEqual(conflicts, [ID])
        self.assertEqual(store[ID]["start_time"], "09:00")
        self.assertIsNone(store[ID]["end_time"])

    def test_wrong_date_cannot_be_changed(self):
        store = {ID: event(start="2026-12-08")}
        _, conflicts = apply_verified_corrections(store)
        self.assertEqual(conflicts, [ID])
        self.assertIsNone(store[ID]["start_time"])

    def test_wrong_url_cannot_be_changed(self):
        store = {ID: event(url="https://www.jaha.or.jp/other/")}
        _, conflicts = apply_verified_corrections(store)
        self.assertEqual(conflicts, [ID])
        self.assertIsNone(store[ID]["start_time"])

    def test_existing_deadline_correction_still_works(self):
        old_id = "a27c399a72d1"
        item = {"id": old_id, "source_id": "vetstech",
                "start_date": "2026-11-11", "deadline": None,
                "url": "https://vets-tech.jp/2026/10/27/vets-tech-web-seminar-vol83/116565/"}
        store = {old_id: item}
        filled, conflicts = apply_verified_corrections(store)
        self.assertEqual(filled, [old_id])
        self.assertEqual(conflicts, [])
        self.assertEqual(item["deadline"], "2026-11-11")

if __name__ == "__main__":
    unittest.main()
