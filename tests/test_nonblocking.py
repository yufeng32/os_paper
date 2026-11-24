"""Guard against false detection claims and distorted non-blocking counts."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.analyze_nonblocking import binary, columns, load_records, PRIMITIVES
from scripts.dynamic.nonblocking.cases import enrich, SPECS
from scripts.dynamic.nonblocking.run import parse_run, summarize


def run_result(stdout="", stderr="", code=0, timeout=False):
    return {"stdout": stdout, "stderr": stderr, "exit_code": code, "timeout": timeout}


class DetectionTests(unittest.TestCase):
    def test_timeout_is_not_a_reproduced_bug_or_detector_report(self):
        r = parse_run(run_result(timeout=True), "foo")
        self.assertEqual(r["infrastructure_error"], "timeout")
        self.assertEqual((r["symptom"], r["target_race"]), (0, 0))

    def test_warning_must_point_to_both_target_access_stacks(self):
        report = "WARNING: DATA RACE\nRead by goroutine 1:\n  main.foo.func1()\nPrevious write by goroutine 2:\n  main.foo.func2()\nGoroutine 2 created at:\n  main.parallel()"
        result = 'RESULT ' + json.dumps({"case": "c", "symptom": False})
        r = parse_run(run_result(result, report, 66), "foo", "c")
        self.assertEqual((r["target_race"], r["symptom"], r["infrastructure_error"]), (1, 0, ""))
        unrelated = report.replace("main.foo.func2", "main.other.func2")
        self.assertEqual(parse_run(run_result(result, unrelated, 66), "foo")["target_race"], 0)

    def test_creation_stacks_do_not_establish_conflicting_accesses(self):
        report = "WARNING: DATA RACE\nmain.other()\nGoroutine 2 created at:\nmain.foo.func1()\nmain.foo.func2()"
        self.assertEqual(parse_run(run_result(stderr=report), "foo")["target_race"], 0)

    def test_map_fatal_is_symptom_not_race_warning(self):
        r = parse_run(run_result(stderr="fatal error: concurrent map iteration and map write", code=2), "balancerMap")
        self.assertEqual((r["symptom"], r["target_race"], r["infrastructure_error"]), (1, 0, ""))

    def test_copy_fault_requires_target_faulting_stack(self):
        stderr = "unexpected fault address\nfatal error: fault\n\ngoroutine 7 [running]:\nruntime.memmove()\nmain.checkpointFiles.func2()\n\ngoroutine 1 [waiting]:\nmain.parallel()"
        r = parse_run(run_result(stderr=stderr, code=2), "checkpointFiles")
        self.assertEqual((r["fatal_copy"], r["symptom"], r["infrastructure_error"]), (1, 1, ""))
        self.assertEqual(parse_run(run_result(stderr=stderr.replace("main.checkpointFiles.func2", "main.other"), code=2), "checkpointFiles")["infrastructure_error"], "missing_result")

    def test_wrong_case_duplicate_result_and_bad_json_are_errors(self):
        good = 'RESULT {"case":"c","symptom":false}'
        self.assertEqual(parse_run(run_result(good), "foo", "d")["infrastructure_error"], "wrong_case_result")
        self.assertEqual(parse_run(run_result(good + "\n" + good), "foo")["infrastructure_error"], "multiple_result_records")
        self.assertTrue(parse_run(run_result("RESULT {"), "foo")["infrastructure_error"])

    def test_target_warning_does_not_override_corrupt_case_identity(self):
        result = 'RESULT ' + json.dumps({"case": "checkpoint\x00", "symptom": False})
        report = "WARNING: DATA RACE\nmain.checkpointFiles.func1()\nmain.checkpointFiles.func2()"
        r = parse_run(run_result(result, report, 66), "checkpointFiles", "checkpoint")
        self.assertEqual(r["target_race"], 1)
        self.assertEqual(r["infrastructure_error"], "wrong_case_result")

    def test_nonzero_exit_is_not_detection(self):
        r = parse_run(run_result('RESULT {"symptom":false}', code=66), "foo")
        self.assertEqual(r["infrastructure_error"], "race_exit_without_report")
        self.assertEqual(r["target_race"], 0)

    def test_failed_fixed_control_excludes_case_but_remains_visible(self):
        rows = []
        for variant in ("buggy", "fixed"):
            for kind in ("plain", "race"):
                rows.append({"case": "c", "variant": variant, "build": kind, "batch": 1,
                             "run": 1, "infrastructure_error": "", "symptom": int(variant == "fixed"),
                             "race_reported": int(kind == "race"), "target_race": int(kind == "race")})
        manifest = [{"case_id": "c", "cause": "traditional", "bug_id": "i", "commit": "a"}]
        with tempfile.TemporaryDirectory() as td:
            stats = summarize(rows, manifest, 1, 1, "natural", Path(td))
            self.assertEqual(stats["statuses"], {"control_failed": 1})
            self.assertEqual(stats["batch_detection"][0]["eligible"], 0)

    def test_missing_run_does_not_count_as_detector_miss(self):
        manifest = [{"case_id": "c", "cause": "channel", "bug_id": "i", "commit": "a"}]
        with tempfile.TemporaryDirectory() as td:
            stats = summarize([], manifest, 1, 1, "natural", Path(td))
            self.assertEqual(stats["statuses"], {"incomplete": 1})
            self.assertIsNone(stats["detection_rate_mean"])


class AnnotationTests(unittest.TestCase):
    def test_invalid_flags_and_ambiguous_headers_rejected(self):
        for value in (True, "1", 2, -1):
            with self.assertRaises(ValueError):
                binary(value)
        with self.assertRaises(ValueError):
            columns(["traditional bug", "traditional bug"])

    def test_select_belongs_to_channel_and_misc_is_union(self):
        self.assertIn("select-patch", PRIMITIVES["Channel"])
        self.assertEqual(PRIMITIVES["Misc"], ("once-patch", "go-patch"))

    def test_pinned_candidates_keep_distinct_commits_for_one_issue(self):
        data = Path(__file__).resolve().parents[1] / "data/upstream"
        if not (data / "bug table.xlsx").exists():
            self.skipTest("pinned dataset not fetched")
        records, candidates, _, _ = load_records(data)
        self.assertEqual(len(records), 86)
        self.assertEqual(len(candidates), 23)
        self.assertEqual(len({c["commit"] for c in candidates}), 23)
        self.assertEqual(sum(c["bug_id"].casefold() == "etcd#4876" for c in candidates), 4)
        self.assertEqual({c["commit"][:12] for c in candidates}, set(SPECS))
        self.assertEqual(len({enrich(c)["case_id"] for c in candidates}), 23)


if __name__ == "__main__":
    unittest.main()
