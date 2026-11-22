# -*- coding: utf-8 -*-
"""Harness for the reduced-scale Table 8 reproduction.

Builds scripts/dynamic (one binary, 8 blocking-bug reproducers), then runs each case in
mode A (natural) and mode B (force all-asleep) three times, captures logs, and classifies:
  detected          -> output contains "all goroutines are asleep"
  exit0_not_detected -> clean exit, detector did not fire
  hung_not_detected  -> timed out; the process hung and the detector did not fire
"""
import csv
import os
import subprocess
from pathlib import Path

DIR = Path(__file__).resolve().parent
ROOT = DIR.parent.parent
OUT = ROOT / "results" / "runtime"
OUT.mkdir(parents=True, exist_ok=True)

GOBIN = r"D:/tools/go/bin"
GO = GOBIN + "/go.exe"
ENV = dict(os.environ)
ENV["PATH"] = GOBIN + os.pathsep + ENV.get("PATH", "")
ENV["GOROOT"] = r"D:/tools/go"
ENV["GOPATH"] = r"D:/tools/gopath"
ENV["GOPROXY"] = "https://goproxy.cn,direct"

CASES = ["docker_17176", "etcd_5509", "etcd_4474", "grpc_1850",
         "grpc_1293", "moby_27782", "grpc_1459", "moby_256"]
CATEGORY = {
    "docker_17176": "Mutex", "etcd_5509": "Mutex", "etcd_4474": "Chan",
    "grpc_1850": "Chan", "grpc_1293": "Chan", "moby_27782": "Chan_w",
    "grpc_1459": "Chan_w", "moby_256": "Lib",
}
MODES = ["A", "B"]
RUNS = 3
TIMEOUT = 8

exe = DIR / "dynamic.exe"
print("building ...")
subprocess.run([GO, "build", "-o", str(exe), "."], cwd=str(DIR), env=ENV, check=True)
print("built", exe)

rows = []
for case in CASES:
    for mode in MODES:
        for n in range(1, RUNS + 1):
            try:
                r = subprocess.run([str(exe), "-case", case, "-mode", mode],
                                   capture_output=True, text=True, timeout=TIMEOUT, env=ENV)
                out = (r.stdout or "") + (r.stderr or "")
                rc = r.returncode
                if "all goroutines are asleep" in out:
                    verdict = "detected"
                elif rc == 0:
                    verdict = "exit0_not_detected"
                else:
                    verdict = "exit%d" % rc
            except subprocess.TimeoutExpired as e:
                raw = e.stdout or b""
                errb = e.stderr or b""
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", "replace")
                if isinstance(errb, bytes):
                    errb = errb.decode("utf-8", "replace")
                out = raw + errb
                rc = "timeout"
                verdict = "hung_not_detected"
            (OUT / ("%s_%s_%d.log" % (case, mode, n))).write_text(out, encoding="utf-8")
            rows.append([case, CATEGORY[case], mode, n, verdict, rc, len(out)])
            print("%-13s %-7s %s %d -> %s" % (case, CATEGORY[case], mode, n, verdict))

with open(OUT / "raw_results.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["case", "category", "mode", "run", "verdict", "exit_code", "log_bytes"])
    w.writerows(rows)

# summary: per case, majority verdict per mode
def majority(vals):
    return max(set(vals), key=vals.count)

summary = []
for case in CASES:
    a = [r[4] for r in rows if r[0] == case and r[2] == "A"]
    b = [r[4] for r in rows if r[0] == case and r[2] == "B"]
    summary.append([case, CATEGORY[case], majority(a), a.count("detected"), majority(b), b.count("detected")])

with open(OUT / "summary.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["case", "category", "A_verdict", "A_detected_of_3", "B_verdict", "B_detected_of_3"])
    w.writerows(summary)

print("\n=== SUMMARY (case, category, A, B) ===")
for s in summary:
    print("  %-13s %-7s  A=%s (%d/3)   B=%s (%d/3)" % (s[0], s[1], s[2], s[3], s[4], s[5]))
print("\nwrote", OUT / "raw_results.csv", "and", OUT / "summary.csv")
