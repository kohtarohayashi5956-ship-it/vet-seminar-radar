# -*- coding: utf-8 -*-
"""Change-tracking regression tests: a re-crawl is not necessarily an update."""
import datetime
import unittest

from merge import FIELDS, event_id, update_store


class ChangeTrackingTests(unittest.TestCase):
    def test_new_unchanged_and_modified_event(self):
        src = {"id": "jaha", "name": "JAHA"}
        date = datetime.date(2026, 11, 14)
        event = {key: None for key in FIELDS}
        event.update(title="犬の循環器講習", start_date="2026-12-15",
                     url="https://www.jaha.or.jp/training/seminar/example/",
                     price="5,000円")
        store = {}
        update_store(store, [event], src, None, date)
        key = event_id("jaha", event["title"], event["start_date"])
        self.assertEqual(store[key]["first_seen"], "2026-11-14")
        self.assertIsNone(store[key]["last_changed"])
        update_store(store, [dict(event)], src, None, date + datetime.timedelta(days=1))
        self.assertIsNone(store[key]["last_changed"])
        changed = dict(event, price="6,000円")
        update_store(store, [changed], src, None, date + datetime.timedelta(days=2))
        self.assertEqual(store[key]["changed_fields"], ["price"])
        self.assertEqual(store[key]["last_changed"], "2026-11-16")
        update_store(store, [dict(changed)], src, None, date + datetime.timedelta(days=3))
        self.assertEqual(store[key]["last_changed"], "2026-11-16")
        self.assertEqual(store[key]["changed_fields"], ["price"])
        self.assertEqual(store[key]["first_seen"], "2026-11-14")


if __name__ == "__main__":
    unittest.main()
