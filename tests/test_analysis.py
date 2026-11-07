"""Semantic edge cases that could silently distort study counts."""

import unittest

from scripts.analyze import aggregate, parse_rows


class ParsingTests(unittest.TestCase):
    def parse(self, rows):
        return parse_rows("blocking", [
            (None, "commit hash", "BugID", "application", "shared", "message"), *rows])

    def test_issue_identifiers_and_summary_rows(self):
        records, issues, audit = self.parse([
            (1, "boltdb#392", "boltdb#392", "boltdb", 0, 1),
            (None, None, None, None, None, None),
            (None, "boltdb", 3, "boltdb", 2, 1),
        ])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["application"], "BoltDB")
        self.assertEqual(issues[0]["code"], "non_hash_identifier")
        self.assertEqual([r["disposition"] for r in audit],
                         ["header", "included", "blank", "summary_or_annotation"])

    def test_both_flags_are_visible_not_repaired(self):
        records, issues, _ = self.parse([(1, "a" * 40, None, "kubernetes", 1, 1)])
        total = aggregate(records)[-1]
        self.assertEqual(total["records"], 1)
        self.assertEqual(total["shared_memory_flags"], 1)
        self.assertEqual(total["message_passing_flags"], 1)
        self.assertEqual(total["ambiguous_records"], 1)
        self.assertEqual(issues[0]["code"], "root_cause_ambiguous_both")

    def test_missing_and_invalid_classification_is_not_zero_filled(self):
        records, _, _ = self.parse([
            (1, "a" * 40, None, "Docker", None, 1),
            (2, "b" * 40, None, "Docker", 0, 0),
        ])
        total = aggregate(records)[-1]
        self.assertEqual(total["records"], 2)
        self.assertEqual(total["message_passing_flags"], 0)
        self.assertEqual(total["unclassified_or_invalid_records"], 2)

    def test_missing_serial_or_identifier_retains_candidate(self):
        records, issues, _ = self.parse([
            (None, "a" * 40, None, "Docker", 1, 0),
            (2, None, None, "unrecognized", 0, 1),
        ])
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["application"], "Unknown")
        self.assertIn("missing_serial", [i["code"] for i in issues])

    def test_duplicate_record_fails_instead_of_double_counting(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.parse([(1, "a" * 40, None, "Docker", 1, 0),
                        (2, "a" * 40, None, "docker", 1, 0)])

    def test_repeated_issue_is_not_a_duplicate_commit(self):
        records, _, _ = self.parse([
            (1, "a" * 40, "project#1", "Docker", 1, 0),
            (2, "b" * 40, "project#1", "Docker", 1, 0),
        ])
        self.assertEqual(len(records), 2)


if __name__ == "__main__":
    unittest.main()
