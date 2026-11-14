import json
import os
import sys
import tempfile
import unittest
from unittest import mock
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import render

class ReleaseSmoke(unittest.TestCase):
    def test_status_and_html_safety(self):
        with tempfile.TemporaryDirectory() as t:
            out=os.path.join(t, "index.html")
            render.write_html([], out, run_status={"warnings": ["robots制限"], "source_results": []})
            with open(out, encoding="utf-8") as f: s=f.read()
            self.assertIn("robots制限",s)
            self.assertIn("JST",s)
            self.assertNotIn('<script id="payload" type="application/json">null',s)
    def test_certification_list_can_expand_beyond_ten(self):
        with tempfile.TemporaryDirectory() as t:
            out = os.path.join(t, "index.html")
            render.write_html([], out)
            with open(out, encoding="utf-8") as f:
                html = f.read()
            self.assertIn('id="certMore" hidden', html)
            self.assertIn('aria-controls="certList"', html)
            self.assertIn('certExpanded ? entries : entries.slice(0, 10)', html)
            self.assertIn('certExpanded = !certExpanded; renderCertificationPanel()', html)

    def test_script_escaping(self):
        with tempfile.TemporaryDirectory() as t:
            out=os.path.join(t, "index.html")
            render.write_html([{"id":"a", "title":"</script><img src=x onerror=alert(1)>", "url": "https://example.org"}],out)
            with open(out,encoding="utf-8") as f: s=f.read()
            self.assertNotIn('</script><img src=x', s)
            self.assertIn('<\/script>', s)
