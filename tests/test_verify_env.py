"""Tests for the Week-2 preflight check.

No network, no workbook and no Excel installation are needed for these tests.
"""
from __future__ import annotations

import json
import unittest
from unittest import mock

import scripts.verify_env as ve


class PreflightTests(unittest.TestCase):
    def test_module_resolves_repository_root(self):
        self.assertTrue((ve.ROOT / "scripts" / "verify_env.py").is_file())
        self.assertTrue((ve.ROOT / "run.py").is_file())

    def test_pins_are_read_from_the_existing_dataset_module(self):
        self.assertEqual(len(ve.COMMIT), 40)
        self.assertEqual(len(ve.SHA256), 64)
        self.assertEqual(ve.WORKBOOK, "bug table.xlsx")
        self.assertEqual(ve.EXPECTED_PYTHON, "3.12.13")
        self.assertEqual(ve.EXPECTED_PACKAGES,
                         {"openpyxl": "3.1.5", "et-xmlfile": "2.0.0"})

    def test_required_files_include_the_existing_entry_points(self):
        for name in ("run.py", "scripts/analyze.py", "scripts/dataset.py",
                     "tests/test_analysis.py", ".python-version"):
            self.assertIn(name, ve.REQUIRED_FILES)

    def test_report_has_a_stable_serialisable_schema(self):
        report = ve.build_report(strict=False)
        self.assertEqual(report["schema"], 1)
        for key in ("generated_utc", "reference", "machine", "checks", "summary"):
            self.assertIn(key, report)
        json.dumps(report)
        for item in report["checks"]:
            self.assertEqual({"name", "status", "detail"}, set(item))
            self.assertIn(item["status"], (ve.OK, ve.WARN, ve.FAIL, ve.INFO))

    def test_missing_package_is_a_failure(self):
        with mock.patch.object(ve.metadata, "version",
                               side_effect=ve.metadata.PackageNotFoundError("x")):
            rows = ve.check_packages()
        self.assertTrue(rows)
        self.assertTrue(all(row[1] == ve.FAIL for row in rows))

    def test_unfetched_dataset_is_informational_not_a_failure(self):
        with mock.patch.object(ve, "DATA_DIR", ve.ROOT / "no-such-data-dir"):
            status, detail = ve.check_dataset()
        self.assertEqual(status, ve.INFO)
        self.assertIn("not fetched", detail)


if __name__ == "__main__":
    unittest.main()
