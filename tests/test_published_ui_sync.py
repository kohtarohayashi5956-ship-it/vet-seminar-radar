# -*- coding: utf-8 -*-
"""Ensure the committed public HTML is synchronized with the UI template.

The event JSON is allowed to differ from the template placeholder, but
the CSS, HTML and JavaScript must match exactly. This prevents silently
publishing an old interface when a template-only change is committed.
"""
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPEN = '<script id="payload" type="application/json">'
CLOSE = '</script>'
PLACEHOLDER = '/*__PAYLOAD__*/null'


class PublishedUiSyncTests(unittest.TestCase):
    def test_published_interface_matches_template(self):
        template = (ROOT / 'template.html').read_text(encoding='utf-8')
        page = (ROOT / 'index.html').read_text(encoding='utf-8')
        self.assertEqual(template.count(PLACEHOLDER), 1)
        start = page.index(OPEN) + len(OPEN)
        end = page.index(CLOSE, start)
        payload = json.loads(page[start:end])
        self.assertIsInstance(payload.get('events'), list)
        sanitized_page = page[:start] + PLACEHOLDER + page[end:]
        self.assertEqual(
            sanitized_page, template,
            'Published index.html is out of sync with template.html; regenerate HTML.'
        )


if __name__ == '__main__':
    unittest.main()
