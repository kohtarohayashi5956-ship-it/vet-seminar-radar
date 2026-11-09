# -*- coding: utf-8 -*-
"""Crawler identity and access policy regression checks."""
import unittest

import config


class CrawlerPolicyTests(unittest.TestCase):
    def test_contact_is_identifiable_without_private_email(self):
        self.assertTrue(config.CONTACT.strip())
        self.assertIn(config.CONTACT, config.USER_AGENT)
        self.assertNotIn("not-set", config.USER_AGENT)

    def test_polite_fetch_policy_is_preserved(self):
        self.assertGreaterEqual(config.REQUEST_INTERVAL_SEC, 3)
        self.assertTrue(config.ROBOTS_TOKEN)

    def test_restricted_sources_remain_disabled(self):
        by_id = {source["id"]: source for source in config.SOURCES}
        for source_id in ("peppy", "eduone", "academy"):
            with self.subTest(source=source_id):
                self.assertFalse(by_id[source_id].get("enabled", True))


if __name__ == "__main__":
    unittest.main()
