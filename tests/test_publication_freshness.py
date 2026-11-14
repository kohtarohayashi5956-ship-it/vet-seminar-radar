# -*- coding: utf-8 -*-
"""Do not discard live crawls for diagnostics/docs-only commits."""
import pathlib
import re
import subprocess
import unittest


WORKFLOW = pathlib.Path(".github/workflows/seminar-radar.yml").read_text(
    encoding="utf-8"
)


class PublicationFreshnessTests(unittest.TestCase):
    def test_crawl_guard_ignores_only_nonfunctional_changes(self):
        match = re.search(r"""grep -Ev '([^']+)'""", WORKFLOW)
        self.assertIsNotNone(match, "Missing freshness path guard")
        pattern = match.group(1)

        for path in (
            "data/release_checks.json",
            "data/collection_checks.json",
            "README.md",
            "docs/V1_RELEASE_GATE.md",
            "docs/qa/instructions.md",
        ):
            with self.subTest(ignored=path):
                proc = subprocess.run(
                    ["grep", "-E", pattern], input=path + "\n",
                    capture_output=True, text=True, check=False
                )
                self.assertEqual(proc.returncode, 0, path)

        for path in (
            "free_extract.py",
            "tests/test_publication_freshness.py",
            "config.py",
            "template.html",
            "data/events.json",
            "data/run_status.json",
            "data/manual_events.csv",
            ".github/workflows/seminar-radar.yml",
        ):
            with self.subTest(invalidating=path):
                proc = subprocess.run(
                    ["grep", "-E", pattern], input=path + "\n",
                    capture_output=True, text=True, check=False
                )
                self.assertEqual(proc.returncode, 1, path)


if __name__ == "__main__":
    unittest.main()
