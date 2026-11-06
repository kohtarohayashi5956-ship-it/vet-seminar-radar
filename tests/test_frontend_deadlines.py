# -*- coding: utf-8 -*-
"""Browser-level regressions: fee classification and deadline day arithmetic."""
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

HTML = pathlib.Path("template.html").read_text(encoding="utf-8")


def function_source(name):
    start = HTML.index("function " + name + "(")
    opening = HTML.index("{", start)
    depth = 0
    for i in range(opening, len(HTML)):
        if HTML[i] == "{":
            depth += 1
        elif HTML[i] == "}":
            depth -= 1
            if depth == 0:
                return HTML[start:i+1]
    raise AssertionError("JS function never closed: " + name)


class DeadlineInterfaceTests(unittest.TestCase):
    def test_panel_does_not_depend_on_calendar_month(self):
        self.assertIn('id="deadlineWindow"', HTML)
        self.assertIn('id="deadlineList"', HTML)
        self.assertIn("renderDeadlinePanel();", HTML)
        fn = function_source("renderDeadlinePanel")
        self.assertNotIn("mStart", fn)
        self.assertNotIn("mEnd", fn)
        self.assertIn("passes(e)", fn)
        self.assertIn("e.deadline", fn)
        self.assertIn("e.start_date", fn)

    def test_client_side_javascript_parses(self):
        if not shutil.which("node"):
            self.skipTest("node unavailable")
        main = re.search(r"<script>\s*([\s\S]*?)</script>", HTML)
        self.assertIsNotNone(main)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", encoding="utf-8") as f:
            f.write(main.group(1))
            f.flush()
            result = subprocess.run(["node", "--check", f.name],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_fee_and_deadline_math(self):
        if not shutil.which("node"):
            self.skipTest("node unavailable")
        js = '\n'.join([
            'var todayStr = "2026-11-06";',
            function_source("isFree"),
            function_source("deadlineDays"),
            "const assert = require('node:assert/strict');",
            'assert.equal(isFree({price:"無料会員 50,000円", is_free:null}),false);',
            'assert.equal(isFree({price:"無料会員 50,000円", is_free:true}),false);',
            'assert.equal(isFree({price:"無料", is_free:null}),true);',
            'assert.equal(isFree({price:"参加費：無料", is_free:null}),true);',
            'assert.equal(isFree({price:null, is_free:true}),true);',
            'assert.equal(isFree({price:null, is_free:null}),false);',
            'assert.equal(deadlineDays("2026-11-06"),0);',
            'assert.equal(deadlineDays("2026-11-13"),7);',
            'assert.equal(deadlineDays("2026-11-05"),-1);',
            'assert.equal(deadlineDays("2027-02-04"),90);',
        ])
        res = subprocess.run(["node", "-e", js], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)

if __name__ == "__main__":
    unittest.main()
