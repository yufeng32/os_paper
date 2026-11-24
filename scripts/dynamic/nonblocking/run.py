"""Build, validate and repeat the non-blocking pattern experiments.

Default matrix: 23 candidates x 2 variants x 2 builds x 100 runs x 3 batches.
Each process is joined; GORACE atexit_sleep_ms=0 removes only the exit delay.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import zipfile

DIR = Path(__file__).resolve().parent
ROOT = DIR.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.analyze_nonblocking import load_records, csv_write
from scripts.dynamic.nonblocking.cases import enrich

PAPER = {"traditional": (13, 7), "anonymous": (4, 3), "shared_lib": (2, 0), "channel": (1, 0)}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd, env, timeout=120):
    """Capture bytes, including on timeout; terminate the process tree if needed."""
    started = time.perf_counter()
    p = subprocess.Popen(args, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
        else:
            p.kill()  # Reproducers do not create child processes.
        stdout, stderr = p.communicate()
    return {"command": list(map(str, args)), "exit_code": p.returncode, "timeout": timed_out,
            "elapsed_seconds": round(time.perf_counter() - started, 6),
            "stdout": stdout.decode("utf-8", "replace"), "stderr": stderr.decode("utf-8", "replace")}


def parse_run(run, symbol, expected_case=None):
    out, err = run["stdout"], run["stderr"]
    parsed = None
    parse_error = ""
    for line in out.splitlines():
        if line.startswith("RESULT "):
            if parsed is not None:
                parse_error = "multiple_result_records"
                break
            try:
                parsed = json.loads(line[7:])
            except (ValueError, TypeError):
                parse_error = "invalid_result_json"
    race = "WARNING: DATA RACE" in err
    target_race = False
    for warning in err.split("WARNING: DATA RACE")[1:]:
        # Only conflicting access stacks, not goroutine-creation stacks.
        accesses = re.split(r"\nGoroutine \d+", warning, maxsplit=1)[0]
        if len(re.findall(r"main\." + re.escape(symbol) + r"(?:\.|\()", accesses)) >= 2:
            target_race = True
    fatal_map = (symbol == "balancerMap" and
                 any(s in err for s in ("fatal error: concurrent map iteration and map write",
                                         "fatal error: concurrent map read and map write")))
    # A torn slice header can fault during the exact unprotected checkpoint
    # copy. Require the target worker and memmove on the faulting stack;
    # unrelated crashes remain infrastructure errors.
    faulting_stack = re.split(r"\ngoroutine \d+", err, maxsplit=2)
    top = faulting_stack[1] if len(faulting_stack) > 1 else ""
    fatal_copy = (symbol == "checkpointFiles" and "fatal error: fault" in err and
                  "main.checkpointFiles.func2(" in top and "runtime.memmove(" in top)
    fatal_target = fatal_map or fatal_copy
    symptom = fatal_target or bool(parsed and parsed.get("symptom") is True)
    infrastructure = parse_error
    if run["timeout"]:
        infrastructure = "timeout"
    elif parsed is not None:
        if expected_case and parsed.get("case") != expected_case:
            infrastructure = "wrong_case_result"
        elif not isinstance(parsed.get("symptom"), bool):
            infrastructure = "invalid_symptom_type"
        elif parsed.get("error"):
            infrastructure = parsed["error"]
        elif run["exit_code"] not in (0, 66):
            infrastructure = "unexpected_exit"
        elif run["exit_code"] == 66 and not race:
            infrastructure = "race_exit_without_report"
    elif not fatal_target:
        infrastructure = "missing_result"
    return {"race_reported": int(race), "target_race": int(target_race),
            "symptom": int(symptom), "target_panic": int(bool(parsed and str(parsed.get("observation", "")).startswith("panic:") and symptom)),
            "fatal_map": int(fatal_map), "fatal_copy": int(fatal_copy), "infrastructure_error": infrastructure,
            "observation": parsed.get("observation", "") if parsed else
            ("runtime map fatal" if fatal_map else "unprotected checkpoint slice copy fault" if fatal_copy else "")}


def tool_environment(go):
    env = dict(os.environ)
    env.pop("GOFLAGS", None)
    env.pop("GOEXPERIMENT", None)
    env.update({"GOROOT": str(go.parent.parent), "GOPATH": str(ROOT / ".cache/nonblocking-gopath"),
                "GOCACHE": str(ROOT / ".cache/nonblocking-gocache"), "CGO_ENABLED": "1", "GOOS": "windows", "GOARCH": "amd64",
                "GOMAXPROCS": "2", "GORACE": "exitcode=66 halt_on_error=0 atexit_sleep_ms=0"})
    env["PATH"] = str(go.parent) + os.pathsep + env.get("PATH", "")
    return env


def preflight(go, env, out):
    evidence = {}
    for name, args in {
        "go_version": [str(go), "version"], "go_env": [str(go), "env", "-json", "GOOS", "GOARCH", "CGO_ENABLED", "CC", "GOROOT", "GOVERSION"],
        "compiler": [env.get("CC", "gcc"), "--version"],
    }.items():
        evidence[name] = command(args, ROOT, env)
        if evidence[name]["exit_code"] != 0:
            raise RuntimeError(f"Preflight failed: {name}: {evidence[name]}")
    if "go1.20.14 windows/amd64" not in evidence["go_version"]["stdout"]:
        raise RuntimeError("Baseline requires go1.20.14 windows/amd64; use the verified portable archive")
    probe_dir = ROOT / ".cache/nonblocking-probes"
    probe_dir.mkdir(parents=True, exist_ok=True)
    sources = {
        "positive": 'package main\nimport "sync"\nfunc main(){var x int;var w sync.WaitGroup;w.Add(2);for i:=0;i<2;i++{go func(){defer w.Done();for j:=0;j<1000;j++{x++}}()};w.Wait()}\n',
        "negative": 'package main\nimport "sync"\nfunc main(){var x int;var m sync.Mutex;var w sync.WaitGroup;w.Add(2);for i:=0;i<2;i++{go func(){defer w.Done();for j:=0;j<1000;j++{m.Lock();x++;m.Unlock()}}()};w.Wait()}\n',
    }
    for name, source in sources.items():
        path, binary = probe_dir / (name + ".go"), probe_dir / (name + ".exe")
        path.write_text(source, encoding="utf-8")
        built = command([str(go), "build", "-race", "-o", str(binary), str(path)], ROOT, env, 300)
        evidence[name + "_build"] = built
        if built["exit_code"] != 0:
            raise RuntimeError(f"Race build failed: {built}")
        tested = command([str(binary)], ROOT, env)
        evidence[name + "_run"] = tested
        detected = "WARNING: DATA RACE" in tested["stderr"]
        if tested["timeout"] or detected != (name == "positive") or tested["exit_code"] != (66 if detected else 0):
            raise RuntimeError(f"Race probe failed: {name}: {tested}")
    evidence.update({"os": platform.platform(), "architecture": platform.machine(),
                     "python": sys.version, "utc_time": datetime.now(timezone.utc).isoformat(),
                     "go_executable_sha256": sha256(go),
                     "environment": {k: env[k] for k in ("GOROOT", "GOPATH", "GOCACHE", "CGO_ENABLED", "GOMAXPROCS", "GORACE")}})
    download = go.parents[2] / "download.json"
    if download.exists():
        evidence["download"] = json.loads(download.read_text(encoding="utf-8"))
    (out / "environment.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return evidence


def summarize(rows, manifest, runs, batches, schedule, out):
    summaries, batch_rows, controls = [], [], []
    for case in manifest:
        cid = case["case_id"]
        selected = [r for r in rows if r["case"] == cid]
        for batch in range(1, batches + 1):
            br = [r for r in selected if r["batch"] == batch]
            fixed = [r for r in br if r["variant"] == "fixed"]
            buggy_race = [r for r in br if r["variant"] == "buggy" and r["build"] == "race"]
            expected = runs * 4
            complete = len(br) == expected and not any(r["infrastructure_error"] for r in br)
            control = (len(fixed) == runs * 2 and
                       not any(r["symptom"] or r["race_reported"] or r["infrastructure_error"] for r in fixed))
            batch_rows.append({"case": cid, "cause": case["cause"], "batch": batch,
                               "complete": int(complete), "control_pass": int(control),
                               "eligible": int(complete and control),
                               "detected": int(any(r["target_race"] for r in buggy_race)),
                               "race_runs": sum(r["target_race"] for r in buggy_race),
                               "symptom_runs": sum(r["symptom"] for r in br if r["variant"] == "buggy"),
                               "first_detection_run": next((r["run"] for r in buggy_race if r["target_race"]), "")})
        buggy = [r for r in selected if r["variant"] == "buggy"]
        plain = [r for r in buggy if r["build"] == "plain"]
        race = [r for r in buggy if r["build"] == "race"]
        cb = [r for r in batch_rows if r["case"] == cid]
        control = all(r["control_pass"] for r in cb)
        complete = all(r["complete"] for r in cb)
        symptom, detected = any(r["symptom"] for r in buggy), any(r["target_race"] for r in buggy)
        status = ("incomplete" if not complete else "control_failed" if not control else
                  "behavior_reproduced" if symptom else "race_reproduced_only" if detected else "not_observed")
        summaries.append({"case": cid, "cause": case["cause"], "bug_id": case["bug_id"],
                          "commit": case["commit"], "schedule": schedule, "status": status,
                          "plain_symptoms": sum(r["symptom"] for r in plain),
                          "race_symptoms": sum(r["symptom"] for r in race),
                          "target_race_runs": sum(r["target_race"] for r in race),
                          "buggy_plain_runs": len(plain), "buggy_race_runs": len(race),
                          "control_pass": int(control), "complete": int(complete)})
        controls.append({"case": cid, "fixed_runs": sum(r["variant"] == "fixed" for r in selected),
                         "control_pass": int(control)})
    csv_write(out / "summary.csv", summaries)
    csv_write(out / "batch_results.csv", batch_rows)
    csv_write(out / "controls.csv", controls)
    comparison = []
    for cause, (paper_used, paper_detected) in PAPER.items():
        eligible = [r for r in summaries if r["cause"] == cause and r["complete"] and r["control_pass"]]
        comparison.append({"cause": cause, "paper_used": paper_used, "paper_detected": paper_detected,
                           "ours_attempted": sum(c["cause"] == cause for c in manifest),
                           "ours_eligible": len(eligible), "ours_detected_any_batch": sum(r["target_race_runs"] > 0 for r in eligible),
                           "ours_behavior_reproduced": sum(r["status"] == "behavior_reproduced" for r in eligible),
                           "ours_not_observed": sum(r["status"] == "not_observed" for r in eligible)})
    csv_write(out / "comparison.csv", comparison)
    rates = []
    batch_stats = []
    for batch in range(1, batches + 1):
        eligible = [r for r in batch_rows if r["batch"] == batch and r["eligible"]]
        detected = sum(r["detected"] for r in eligible)
        rate = detected / len(eligible) if eligible else None
        if rate is not None:
            rates.append(rate)
        batch_stats.append({"batch": batch, "eligible": len(eligible), "detected": detected, "rate": rate})
    stats = {"schedule": schedule, "runs_per_combination": runs, "batches": batches,
             "process_runs": len(rows), "expected_process_runs": len(manifest)*4*runs*batches,
             "complete_cases": sum(r["complete"] for r in summaries),
             "control_pass_cases": sum(r["control_pass"] for r in summaries),
             "statuses": {s: sum(r["status"] == s for r in summaries) for s in sorted({r["status"] for r in summaries})},
             "batch_detection": batch_stats,
             "detection_rate_mean": statistics.mean(rates) if rates else None,
             "detection_rate_sample_sd": statistics.stdev(rates) if len(rates)>1 else None,
             "infrastructure_errors": sum(bool(r["infrastructure_error"]) for r in rows)}
    (out / "statistics.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    lines = ["# Non-blocking race-detector experiment", "",
             f"Schedule: **{schedule}**. {len(manifest)} candidate records; {batches} batches x {runs} runs per combination.",
             f"Completed process records: {len(rows)}/{stats['expected_process_runs']}. Infrastructure errors: {stats['infrastructure_errors']}.", "",
             "| Root cause | Paper used/detected | Ours attempted/eligible | Ours detected (any batch) |",
             "| --- | ---: | ---: | ---: |"]
    for r in comparison:
        lines.append(f"| {r['cause']} | {r['paper_used']}/{r['paper_detected']} | {r['ours_attempted']}/{r['ours_eligible']} | {r['ours_detected_any_batch']} |")
    lines += ["", "Paper Table 12 (PDF p. 11) uses 20 bugs and one budget of 100 runs per bug;",
              "the pinned workbook flags 23 candidates (four channel cases instead of one). No exact 20-case cohort is established.",
              "Our samples are standalone pattern reconstructions under Go 1.20.14, not the historical applications.",
              "Counts are not an estimate of the original detector's accuracy. Case identities are in manifest.json;",
              "raw commands, exit codes, observations and reports are preserved per run.", "",
              "| Batch | Eligible cases | Detected within budget | Rate |", "| --- | ---: | ---: | ---: |"]
    for b in batch_stats:
        rate_text = f"{b['rate']:.2%}" if b['rate'] is not None else "n/a"
        lines.append(f"| {b['batch']} | {b['eligible']} | {b['detected']} | {rate_text} |")
    if rates:
        sd = f"{statistics.stdev(rates):.2%}" if len(rates)>1 else "n/a"
        lines += ["", f"Batch rate mean = {statistics.mean(rates):.2%}; sample SD = {sd}."]
    lines += ["", "A case is eligible only when all requested executions finish without infrastructure errors and its fixed control is clean.",
              "Unobserved candidates remain in the attempted-cohort table and in the eligible denominator; they are NOT established detector misses.",
              "A target race report establishes the conflicting access, even when the ordinary output appears correct.",
              "Target panics, lost notifications and ordering violations are classified separately from detector warnings.",
              "The timerReuse candidate retains its historical API pattern without injecting a user-level race; no observation means no confirmed reproduction.",
              "Controlled diagnostics are excluded from the natural detection table.", "",
              "## Per-case status", "", "| Case | Status | Plain symptoms | Race warnings |", "| --- | --- | ---: | ---: |"]
    for r in summaries:
        lines.append(f"| {r['case']} | {r['status']} | {r['plain_symptoms']} | {r['target_race_runs']} |")
    (out / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return stats


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--go", type=Path, default=Path(os.environ.get("GO_EXE", ROOT / ".cache/nonblocking-toolchain/go/bin/go.exe")))
    p.add_argument("--case", action="append", help="select a case ID (repeatable)")
    p.add_argument("--runs", type=int, default=100)
    p.add_argument("--batches", type=int, default=3)
    p.add_argument("--timeout", type=float, default=10)
    p.add_argument("--jobs", type=int, default=8, help="independent processes per combination (recorded; default 8)")
    p.add_argument("--schedule", choices=("natural", "controlled"), default="natural")
    p.add_argument("--output", type=Path)
    p.add_argument("--preflight-only", action="store_true")
    a = p.parse_args()
    if a.runs < 1 or a.batches < 1 or a.timeout <= 0 or a.jobs < 1:
        p.error("runs, batches, jobs and timeout must be positive")
    out = a.output or ROOT / "results/nonblocking" / ("runtime" if a.schedule == "natural" else "diagnostic")
    # Existing evidence is never silently overwritten. Choose a new output directory.
    if out.exists() and any(out.iterdir()):
        p.error(f"Output is not empty: {out}; choose --output for a fresh run")
    out.mkdir(parents=True, exist_ok=True)
    _, candidates, digest, _ = load_records(ROOT / "data/upstream")
    manifest = [enrich(c) for c in candidates]
    if a.case:
        unknown = set(a.case) - {c["case_id"] for c in manifest}
        if unknown:
            p.error(f"unknown cases: {sorted(unknown)}")
        manifest = [c for c in manifest if c["case_id"] in a.case]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    go = a.go.resolve()
    if not go.is_file():
        p.error(f"Go executable not found: {go}; pass --go or GO_EXE")
    env = tool_environment(go)
    print("Checking compiler and race-detector positive/negative controls ...", flush=True)
    preflight(go, env, out)
    if a.preflight_only:
        print("Preflight passed", flush=True)
        return
    binaries = {}
    builds = {}
    build_dir = ROOT / ".cache/nonblocking-build"
    build_dir.mkdir(parents=True, exist_ok=True)
    for kind in ("plain", "race"):
        binary = build_dir / (kind + ".exe")
        args = [str(go), "build", "-o", str(binary)]
        if kind == "race":
            args.append("-race")
        args.append(".")
        built = command(args, DIR, env, 300)
        builds[kind] = built
        if built["exit_code"] or built["timeout"]:
            (out / "builds.json").write_text(json.dumps(builds, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(f"{kind} build failed: {built}")
        binaries[kind] = binary
        builds[kind]["sha256"] = sha256(binary)
    (out / "builds.json").write_text(json.dumps(builds, indent=2) + "\n", encoding="utf-8")
    metadata = {"workbook_sha256": digest, "runs": a.runs, "batches": a.batches,
                "timeout": a.timeout, "schedule": a.schedule, "parallel_processes": a.jobs,
                "source_sha256": {path.name: sha256(path) for path in sorted([*DIR.glob("*.go"), DIR / "go.mod"])},
                "driver_sha256": {path.name: sha256(path) for path in (DIR / "run.py", DIR / "cases.py", DIR / "verify.py")},
                "started_utc": datetime.now(timezone.utc).isoformat()}
    (out / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    rows = []
    expected = len(manifest) * a.batches * a.runs * 4
    started = time.perf_counter()
    fields = ["case", "cause", "variant", "build", "schedule", "batch", "run", "seed", "exit_code", "timeout", "elapsed_seconds",
              "race_reported", "target_race", "symptom", "target_panic", "fatal_map", "fatal_copy", "infrastructure_error", "observation", "log", "log_sha256"]
    with (out / "raw_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        for batch in range(1, a.batches + 1):
            for case in manifest:
                for kind in ("plain", "race"):
                    for variant in ("buggy", "fixed"):
                        def execute(n):
                            seed = batch * 100000 + n
                            args = [str(binaries[kind]), "-case", case["case_id"], "-variant", variant,
                                    "-schedule", a.schedule, "-seed", str(seed)]
                            return n, seed, command(args, DIR, env, a.timeout)
                        # Only repetitions of the same case/build/variant overlap.
                        # Ordered map retains a stable CSV order and seed mapping.
                        with ThreadPoolExecutor(max_workers=a.jobs) as pool:
                            for n, seed, run in pool.map(execute, range(1, a.runs + 1)):
                                parsed = parse_run(run, case["symbol"], case["case_id"])
                                rel = Path("logs") / case["case_id"] / f"b{batch}_{kind}_{variant}_{n:03d}.json"
                                path = out / rel
                                path.parent.mkdir(parents=True, exist_ok=True)
                                path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
                                row = {"case": case["case_id"], "cause": case["cause"], "variant": variant,
                                       "build": kind, "schedule": a.schedule, "batch": batch, "run": n, "seed": seed,
                                       **{k: run[k] for k in ("exit_code", "timeout", "elapsed_seconds")},
                                       **parsed, "log": rel.as_posix(), "log_sha256": sha256(path)}
                                rows.append(row); writer.writerow(row)
                        f.flush()
                print(f"batch {batch}/{a.batches} {case['case_id']}: {len(rows)}/{expected} processes; {time.perf_counter()-started:.1f}s", flush=True)
    stats = summarize(rows, manifest, a.runs, a.batches, a.schedule, out)
    with zipfile.ZipFile(out / "logs.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((out / "logs").rglob("*.json")):
            archive.write(path, path.relative_to(out).as_posix())
    metadata["logs_zip_sha256"] = sha256(out / "logs.zip")
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    (out / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2), flush=True)
    if stats["infrastructure_errors"] or stats["control_pass_cases"] != len(manifest):
        raise SystemExit("Experiment recorded but acceptance checks failed; inspect summary.csv")


if __name__ == "__main__":
    main()
