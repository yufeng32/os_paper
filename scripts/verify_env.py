"""Preflight check for a clean-machine reproduction (CS340, Week 2).

Additive only: this file does not change run.py, scripts/analyze.py,
scripts/dataset.py, the existing tests, or any published result.

Usage:
    python scripts/verify_env.py
    python scripts/verify_env.py --write      # also write results/environment.json
    python scripts/verify_env.py --strict    # warnings become failures
"""
from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from scripts.dataset import COMMIT, SHA256, WORKBOOK, verify
except ImportError as error:
    print(f"FAIL: cannot import scripts.dataset from {ROOT}: {error}", file=sys.stderr)
    raise SystemExit(2)

EXPECTED_PYTHON = "3.12.13"
EXPECTED_PACKAGES = {"openpyxl": "3.1.5", "et-xmlfile": "2.0.0"}
REQUIRED_FILES = (
    ".gitignore",
    ".python-version",
    "requirements.txt",
    "run.py",
    "scripts/analyze.py",
    "scripts/dataset.py",
    "scripts/verify_env.py",
    "tests/test_analysis.py",
)
DATA_DIR = ROOT / "data" / "upstream"
ENVIRONMENT_JSON = ROOT / "results" / "environment.json"

OK, WARN, FAIL, INFO = "OK", "WARN", "FAIL", "INFO"


def check_python() -> tuple[str, str]:
    """Compare the running interpreter with the pinned reference interpreter."""
    actual = platform.python_version()
    if actual == EXPECTED_PYTHON:
        return OK, f"{actual} (matches .python-version)"
    return WARN, f"{actual}; reference interpreter is {EXPECTED_PYTHON}"


def check_packages() -> list[tuple[str, str, str]]:
    """A missing package is fatal; a different patch version is only a warning."""
    rows: list[tuple[str, str, str]] = []
    for name, expected in EXPECTED_PACKAGES.items():
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            rows.append((f"package:{name}", FAIL,
                         "not installed; run pip install -r requirements.txt"))
            continue
        if actual == expected:
            rows.append((f"package:{name}", OK, f"{actual} (pinned)"))
        else:
            rows.append((f"package:{name}", WARN,
                         f"{actual}; requirements.txt pins {expected}"))
    return rows


def check_git() -> tuple[str, str]:
    """The first dataset acquisition in scripts/dataset.py shells out to git."""
    if shutil.which("git") is None:
        return FAIL, "git not on PATH; the first fetch needs it"
    try:
        result = subprocess.run(["git", "--version"], capture_output=True,
                                text=True, check=True)
        return OK, (result.stdout.strip() or result.stderr.strip())
    except (OSError, subprocess.CalledProcessError) as error:
        return FAIL, f"git --version failed: {error}"


def check_files() -> list[tuple[str, str, str]]:
    """Guard against a partial checkout without hard-coding absolute paths."""
    rows: list[tuple[str, str, str]] = []
    for relative in REQUIRED_FILES:
        target = ROOT / relative
        present = target.is_file()
        rows.append((f"file:{relative}", OK if present else FAIL,
                     "present" if present else "missing"))
    return rows


def check_dataset() -> tuple[str, str]:
    """Reuse the upstream verify() so the SHA-256 is never duplicated here."""
    workbook = DATA_DIR / WORKBOOK
    if not workbook.is_file():
        return INFO, f"not fetched yet; 'make run' clones commit {COMMIT[:12]}"
    try:
        verify(DATA_DIR)
    except (OSError, ValueError) as error:
        return FAIL, f"workbook check failed: {error}"
    return OK, f"workbook SHA-256 matches {SHA256[:12]}..."


def build_report(strict: bool) -> dict:
    checks: list[tuple[str, str, str]] = [
        ("python", *check_python()),
        ("git", *check_git()),
        ("dataset", *check_dataset()),
    ]
    checks.extend(check_packages())
    checks.extend(check_files())
    counts = {status: sum(1 for item in checks if item[1] == status)
              for status in (OK, WARN, FAIL, INFO)}
    return {
        "schema": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "reference": {
            "python": EXPECTED_PYTHON,
            "dataset_commit": COMMIT,
            "workbook": WORKBOOK,
            "workbook_sha256": SHA256,
        },
        "machine": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python": platform.python_version(),
            "python_implementation": platform.python_implementation(),
        },
        "checks": [{"name": name, "status": status, "detail": detail}
                   for name, status, detail in checks],
        "summary": {
            "ok": counts[OK], "warn": counts[WARN], "fail": counts[FAIL],
            "info": counts[INFO], "strict": strict,
        },
    }


def print_report(report: dict) -> None:
    machine = report["machine"]
    print("CS340 reproduction preflight (Week 2)")
    print(f"machine : {machine['os']} {machine['os_release']} "
          f"({machine['os_version']}), {machine['architecture']}")
    print(f"python  : {machine['python']} "
          f"(reference {report['reference']['python']})")
    print("-" * 72)
    for item in report["checks"]:
        print(f"[{item['status']:<4}] {item['name']:<34} {item['detail']}")
    print("-" * 72)
    summary = report["summary"]
    print(f"OK={summary['ok']}  WARN={summary['warn']}  "
          f"FAIL={summary['fail']}  INFO={summary['info']}  "
          f"strict={summary['strict']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true",
                        help="also write results/environment.json for traceability")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as failures (final acceptance)")
    args = parser.parse_args()

    report = build_report(args.strict)
    print_report(report)
    if args.write:
        ENVIRONMENT_JSON.parent.mkdir(parents=True, exist_ok=True)
        ENVIRONMENT_JSON.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {ENVIRONMENT_JSON.relative_to(ROOT)}")

    failed = report["summary"]["fail"] > 0
    if args.strict and report["summary"]["warn"] > 0:
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
