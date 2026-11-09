# -*- coding: utf-8 -*-
"""Offline structural smoke checks for the v1.0 browser UI.

These checks deliberately do not claim to simulate a browser. They catch
missing control IDs and disconnected handlers before publication.
"""
import pathlib
import re
import unittest
from html.parser import HTMLParser


ROOT = pathlib.Path(__file__).resolve().parents[1]


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])


class TemplateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "template.html").read_text(encoding="utf-8")
        parser = IdCollector()
        parser.feed(cls.html)
        cls.ids = parser.ids

    def test_no_duplicate_ids(self):
        self.assertEqual(len(self.ids), len(set(self.ids)))

    def test_core_controls_exist(self):
        required = {
            "list", "monthLabel", "prev", "next", "today",
            "fAud", "fRegion", "fOnsite", "fLive", "fOnd",
            "fTopic", "fOrg", "fFree", "fNew", "fHidePast",
            "fGeneral", "fQ", "resetFilters", "resultSummary",
            "deadlineWindow", "deadlineList", "certDisclosure",
            "certShortcut", "certSearch", "certField", "certKind",
            "composer", "picked", "out", "copy", "regen", "clear",
        }
        self.assertFalse(required - set(self.ids))

    def test_new_filter_and_reset_are_connected(self):
        # Handler is registered via the shared checkbox array.
        self.assertIn('"fNew", "fHidePast"', self.html)
        self.assertIn('if ($("fNew").checked', self.html)
        self.assertIn('$("fNew").checked = false;', self.html)
        self.assertIn('$("resetFilters").addEventListener("click"', self.html)

    def test_summary_and_composer_remain_connected(self):
        self.assertIn('$("resultSummary").textContent', self.html)
        self.assertIn('function refreshComposer(', self.html)
        self.assertIn('function copyText()', self.html)
        self.assertIn('$("copy").addEventListener("click", copyText)', self.html)

    def test_certification_section_follows_main_results(self):
        self.assertLess(self.html.index('id="list"'), self.html.index('id="certDisclosure"'))

    def test_payload_marker_remains_for_safe_rendering(self):
        self.assertIn('/*__PAYLOAD__*/null', self.html)


if __name__ == "__main__":
    unittest.main()
