# -*- coding: utf-8 -*-
"""Crawler identity and access policy regression checks."""
import ast
import pathlib
import unittest

import config


class CrawlerPolicyTests(unittest.TestCase):
    def test_contact_is_identifiable_without_private_email(self):
        self.assertTrue(config.CONTACT.strip())
        self.assertIn(config.CONTACT, config.USER_AGENT)
        self.assertNotIn("not-set", config.USER_AGENT)

    def test_polite_fetch_policy_is_preserved(self):
        # Other tests temporarily set config.REQUEST_INTERVAL_SEC=0 to avoid
        # delays in mock fetches. Inspect the declared default, not the
        # shared mutable module attribute left by those unrelated tests.
        module = ast.parse((pathlib.Path(__file__).resolve().parents[1] / "config.py").read_text(encoding="utf-8"))
        assignments = [
            node.value for node in module.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "REQUEST_INTERVAL_SEC"
                    for target in node.targets)
        ]
        self.assertEqual(len(assignments), 1)
        self.assertGreaterEqual(ast.literal_eval(assignments[0]), 3)
        self.assertTrue(config.ROBOTS_TOKEN)

    def test_restricted_sources_remain_disabled(self):
        by_id = {source["id"]: source for source in config.SOURCES}
        for source_id in ("peppy", "eduone", "academy"):
            with self.subTest(source=source_id):
                self.assertFalse(by_id[source_id].get("enabled", True))


if __name__ == "__main__":
    unittest.main()
