# -*- coding: utf-8 -*-
"""Release guardrails for stored public event data.

Run without network access. These tests intentionally check structural
contradictions, not whether third-party published information is correct.
"""
import datetime
import json
import pathlib
import re
import unittest
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PublicEventDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads((ROOT / "data" / "events.json").read_text(encoding="utf-8"))
        cls.events = list(data["events"].values())

    def test_events_have_provenance_and_url(self):
        for e in self.events:
            with self.subTest(event=e.get("id")):
                self.assertTrue(e.get("title"))
                self.assertTrue(e.get("first_seen"))
                self.assertTrue(e.get("source_id"))
                u = urlparse(e.get("url") or "")
                self.assertIn(u.scheme, ("http", "https"))
                self.assertTrue(u.netloc)

    def test_all_explicit_dates_are_calendar_dates(self):
        fields = ("start_date", "end_date", "deadline", "abstract_deadline",
                  "early_registration_deadline", "first_seen", "last_seen")
        for e in self.events:
            for field in fields:
                value = e.get(field)
                if value:
                    with self.subTest(event=e.get("id"), field=field):
                        self.assertEqual(datetime.date.fromisoformat(value).isoformat(), value)

    def test_paid_amount_is_not_marked_unconditionally_free(self):
        for e in self.events:
            if e.get("is_free") is True:
                with self.subTest(event=e.get("id")):
                    self.assertIsNone(
                        re.search(r"[0-9０-９][0-9０-９,，]*\s*円", e.get("price") or "")
                    )

    def test_registration_deadline_not_after_course_start(self):
        for e in self.events:
            if e.get("deadline") and e.get("start_date"):
                with self.subTest(event=e.get("id")):
                    self.assertLessEqual(e["deadline"], e["start_date"])


if __name__ == "__main__":
    unittest.main()
