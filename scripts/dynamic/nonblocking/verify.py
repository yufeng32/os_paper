"""Verify every archived execution, hash, matrix cell and summary against raw logs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.dynamic.nonblocking.run import parse_run


def verify(output):
    metadata = json.loads((output / "run.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    cases = {c["case_id"]: c for c in manifest}
    with (output / "raw_results.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    expected = {(cid, b, kind, variant, n) for cid in cases
                for b in range(1, metadata["batches"] + 1)
                for kind in ("plain", "race") for variant in ("buggy", "fixed")
                for n in range(1, metadata["runs"] + 1)}
    seen = set()
    checked = []
    payload = (output / "logs.zip").read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata["logs_zip_sha256"]:
        raise ValueError("Archive SHA-256 mismatch")
    with zipfile.ZipFile(output / "logs.zip") as archive:
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("Duplicate archive member")
        if set(archive.namelist()) != {r["log"] for r in rows}:
            raise ValueError("Archive member set differs from raw-result log set")
        for row in rows:
            key = (row["case"], int(row["batch"]), row["build"], row["variant"], int(row["run"]))
            if key not in expected or key in seen:
                raise ValueError(f"Unexpected or duplicate matrix cell: {key}")
            seen.add(key)
            data = archive.read(row["log"])
            if hashlib.sha256(data).hexdigest() != row["log_sha256"]:
                raise ValueError(f"Log SHA-256 mismatch: {row['log']}")
            run = json.loads(data)
            parsed = parse_run(run, cases[row["case"]]["symbol"], row["case"])
            for name, value in parsed.items():
                if str(value) != row[name]:
                    raise ValueError(f"Classification mismatch: {row['log']} {name}")
            for name in ("exit_code", "timeout", "elapsed_seconds"):
                if str(run[name]) != row[name]:
                    raise ValueError(f"Process metadata mismatch: {row['log']} {name}")
            args = run["command"]
            expected_args = {"-case": row["case"], "-variant": row["variant"],
                             "-schedule": metadata["schedule"], "-seed": row["seed"]}
            for flag, value in expected_args.items():
                if args.count(flag) != 1 or args[args.index(flag)+1] != value:
                    raise ValueError(f"Command mismatch: {row['log']} {flag}")
            if Path(args[0]).name != row["build"] + ".exe":
                raise ValueError(f"Wrong build executable: {row['log']}")
            checked.append({**row, **parsed})
    if seen != expected:
        raise ValueError(f"Missing matrix cells: {len(expected-seen)}")
    with (output / "summary.csv").open(encoding="utf-8", newline="") as f:
        summaries = list(csv.DictReader(f))
    if {r["case"] for r in summaries} != set(cases) or len(summaries) != len(cases):
        raise ValueError("Summary case set differs from manifest")
    for summary in summaries:
        case_rows = [r for r in checked if r["case"] == summary["case"]]
        fixed = [r for r in case_rows if r["variant"] == "fixed"]
        buggy = [r for r in case_rows if r["variant"] == "buggy"]
        target = sum(r["target_race"] for r in buggy if r["build"] == "race")
        plain_symptoms = sum(r["symptom"] for r in buggy if r["build"] == "plain")
        race_symptoms = sum(r["symptom"] for r in buggy if r["build"] == "race")
        control = not any(r["symptom"] or r["race_reported"] or r["infrastructure_error"] for r in fixed)
        complete = not any(r["infrastructure_error"] for r in case_rows)
        expected_status = ("incomplete" if not complete else "control_failed" if not control else
                           "behavior_reproduced" if plain_symptoms or race_symptoms else
                           "race_reproduced_only" if target else "not_observed")
        if summary["status"] != expected_status or int(summary["target_race_runs"]) != target:
            raise ValueError(f"Summary status/count mismatch: {summary['case']}")
        if int(summary["plain_symptoms"]) != plain_symptoms or int(summary["race_symptoms"]) != race_symptoms:
            raise ValueError(f"Summary symptom count mismatch: {summary['case']}")
    return {"archive_logs_verified": len(rows), "matrix_cells_expected": len(expected),
            "case_summaries_verified": len(cases), "all_matrix_cells_present": True,
            "infrastructure_errors": sum(bool(r["infrastructure_error"]) for r in checked),
            "archive_sha256": metadata["logs_zip_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "results/nonblocking/runtime")
    a = parser.parse_args()
    report = verify(a.output)
    (a.output / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
