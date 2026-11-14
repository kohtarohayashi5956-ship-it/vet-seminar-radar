# -*- coding: utf-8 -*-
"""Regression checks for the independent certification search reset."""
import pathlib
import unittest

TEMPLATE = pathlib.Path(__file__).resolve().parents[1] / "template.html"


class CertificationControlsTests(unittest.TestCase):
    def test_reset_is_wired_to_certification_fields_only(self):
        content = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('id="certReset"', content)
        self.assertIn('$("certReset").addEventListener("click"', content)
        start = content.index('$("certReset").addEventListener("click"')
        end = content.index('$("certShortcut").addEventListener', start)
        handler = content[start:end]
        for value in ('$("certField").value = "all";',
                      '$("certKind").value = "all";',
                      '$("certSearch").value = "";'):
            self.assertIn(value, handler)
        self.assertNotIn('$("fQ").value', handler)
        self.assertIn('render();', handler)


if __name__ == "__main__":
    unittest.main()
