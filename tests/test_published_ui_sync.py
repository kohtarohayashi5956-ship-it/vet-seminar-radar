# -*- coding: utf-8 -*-
"""Verify that rendering preserves the current HTML/CSS/JS template.

The test deliberately generates fresh output in a temporary directory.
Comparing against the committed index.html would incorrectly block
automatic collection before its HTML regeneration step.
"""
import json
import pathlib
import tempfile
import unittest

import render

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPEN = '<script id="payload" type="application/json">'
CLOSE = '</script>'
PLACEHOLDER = '/*__PAYLOAD__*/null'


class RenderedUiSyncTests(unittest.TestCase):
    def test_rendered_interface_matches_template(self):
        template = (ROOT / 'template.html').read_text(encoding='utf-8')
        self.assertEqual(template.count(PLACEHOLDER), 1)
        with tempfile.TemporaryDirectory() as tmp:
            output = pathlib.Path(tmp) / 'index.html'
            render.write_html([], str(output), demo=True)
            page = output.read_text(encoding='utf-8')
        start = page.index(OPEN) + len(OPEN)
        end = page.index(CLOSE, start)
        payload = json.loads(page[start:end])
        self.assertEqual(payload['events'], [])
        self.assertTrue(payload['demo'])
        reconstructed = page[:start] + PLACEHOLDER + page[end:]
        self.assertEqual(reconstructed, template)


if __name__ == '__main__':
    unittest.main()
