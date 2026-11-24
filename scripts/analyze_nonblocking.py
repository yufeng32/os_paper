"""Audit Tables 9--11 without repairing labels in the pinned workbook."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.analyze import parse_rows
from scripts.dataset import COMMIT, WORKBOOK, verify

CAUSES = {
    "traditional": "traditional bug", "anonymous": "anonymous funcion",
    "waitgroup": "misusing waitgroup", "shared_lib": "race@lib",
    "channel": "misusing channel", "message_lib": "misusing messaging lib",
}
STRATEGIES = {
    "Adds": "Add-t", "Moves": "Move-t", "Bypass": "eliminate or bypass Insruction",
    "Private": "data private", "Misc": "Misc.",
}
PRIMITIVES = {
    "Mutex": ("lock-patch",), "Channel": ("channel-patch", "select-patch"),
    "Atomic": ("atomic-patch",), "WaitGroup": ("waitgroup-patch",),
    "Cond": ("cond-patch",), "Misc": ("once-patch", "go-patch"),
    "None": ("none",),
}
APPS = ("Docker", "Kubernetes", "etcd", "CockroachDB", "gRPC", "BoltDB")
APP_DIR = dict(zip(APPS, ("docker", "kubernetes", "etcd", "cockroachdb", "grpc-go", "boltdb")))
REPOS = dict(zip(APPS, ("moby/moby", "kubernetes/kubernetes", "etcd-io/etcd",
                       "cockroachdb/cockroach", "grpc/grpc-go", "boltdb/bolt")))
# Paper PDF pp. 9, 11. Cause order is explicit; Table 10/11 print WaitGroup
# before anonymous, whereas Table 9 prints anonymous before WaitGroup.
PAPER9 = {
    "Docker": (9, 6, 0, 1, 6, 1), "Kubernetes": (8, 3, 1, 0, 5, 0),
    "etcd": (9, 0, 2, 2, 3, 0), "CockroachDB": (10, 1, 3, 2, 0, 0),
    "gRPC": (8, 1, 0, 1, 2, 0), "BoltDB": (2, 0, 0, 0, 0, 0),
}
PAPER10 = {
    "traditional": (27, 4, 5, 10, 0), "anonymous": (5, 2, 0, 4, 0),
    "waitgroup": (3, 2, 1, 0, 0), "shared_lib": (1, 2, 1, 0, 2),
    "channel": (6, 7, 3, 0, 0), "message_lib": (0, 0, 0, 0, 1),
}
PAPER11 = {
    "traditional": (24, 3, 6, 0, 0, 0, 13), "anonymous": (3, 2, 3, 0, 0, 0, 3),
    "waitgroup": (2, 0, 0, 4, 3, 0, 0), "shared_lib": (0, 2, 1, 1, 0, 1, 2),
    "channel": (3, 11, 0, 2, 1, 2, 1), "message_lib": (0, 1, 0, 0, 0, 0, 0),
}


def columns(headers):
    required = [*CAUSES.values(), *STRATEGIES.values(), "Reproduced?",
                *(h for hs in PRIMITIVES.values() for h in hs)]
    for h in required:
        if headers.count(h) != 1:
            raise ValueError(f"Missing or ambiguous header: {h!r}")
    return {h: headers.index(h) for h in required}


def binary(value):
    if value is None:
        return 0  # Empty annotation cells mean the flag is not selected.
    if type(value) not in (int, float) or value not in (0, 1):
        raise ValueError(f"Invalid annotation flag {value!r}")
    return int(value)


def csv_write(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_records(data):
    digest = verify(data)
    wb = openpyxl.load_workbook(data / WORKBOOK, read_only=True, data_only=True)
    try:
        rows = list(wb["non-blocking"].values)
    finally:
        wb.close()
    col = columns(list(rows[0]))
    records, anomalies, _ = parse_rows("non-blocking", rows)
    detail, candidates = [], []
    for rec in records:
        row = rows[rec["row"] - 1]
        causes = [c for c, h in CAUSES.items() if binary(row[col[h]])]
        strategies = [s for s, h in STRATEGIES.items() if binary(row[col[h]])]
        if len(causes) != 1 or len(strategies) != 1:
            raise ValueError(f"Nonexclusive labels at row {rec['row']}: {causes}, {strategies}")
        primitives = [p for p, hs in PRIMITIVES.items() if any(binary(row[col[h]]) for h in hs)]
        if not primitives or ("None" in primitives and len(primitives) != 1):
            raise ValueError(f"Inconsistent primitive labels at row {rec['row']}")
        item = {"row": rec["row"], "application": rec["application"],
                "bug_id": rec["raw_bug_id"], "commit": rec["raw_identifier"],
                "cause": causes[0], "strategy": strategies[0],
                "primitives": ";".join(primitives),
                "raw_primitive_flags": ";".join(h for hs in PRIMITIVES.values()
                                                for h in hs if binary(row[col[h]])),
                "reproduced_flag": binary(row[col["Reproduced?"]])}
        detail.append(item)
        if item["reproduced_flag"]:
            app = item["application"]
            patch = data / "non-blocking-bugs" / APP_DIR[app] / (item["commit"] + ".txt")
            payload = patch.read_bytes() if patch.exists() else b""
            candidates.append({**item, "case_id": f"{APP_DIR[app].replace('-', '_')}_{item['commit'][:12]}",
                               "repository": REPOS[app],
                               "source_url": f"https://github.com/{REPOS[app]}/commit/{item['commit']}",
                               "dataset_patch": patch.relative_to(data).as_posix(),
                               "patch_present": bool(payload),
                               "patch_has_diff": b"diff --git" in payload,
                               "patch_sha256": hashlib.sha256(payload).hexdigest() if payload else ""})
    return detail, candidates, digest, anomalies


def comparison(number, groups, categories, paper, counts, out):
    rows = []
    for group in groups:
        for i, category in enumerate(categories):
            got = counts[group, category]
            exp = paper[group][i]
            rows.append({"group": group, "category": category, "paper": exp,
                         "ours": got, "difference": got - exp})
    csv_write(out / f"table{number}" / "comparison.csv", rows)
    table = [{"group": g, **{c: counts[g, c] for c in categories}} for g in groups]
    table.append({"group": "Total", **{c: sum(counts[g, c] for g in groups) for c in categories}})
    csv_write(out / f"table{number}" / f"table{number}.csv", table)
    diffs = sum(r["difference"] != 0 for r in rows)
    lines = [f"# Table {number}: Paper vs. Ours", "",
             f"Pinned workbook: {COMMIT}; 86 non-blocking records. Paper PDF p. {9 if number == 9 else 11}.", "",
             "| Group | " + " | ".join(categories) + " |",
             "| --- | " + " | ".join("---:" for _ in categories) + " |"]
    for row in table:
        lines.append("| " + str(row["group"]) + " | " + " | ".join(str(row[c]) for c in categories) + " |")
    lines += ["", f"Differing non-total cells: **{diffs}/{len(rows)}**. Signed differences are in comparison.csv.", ""]
    if number == 11:
        lines += ["Channel is the per-record union of channel-patch and select-patch (select operates on channels).",
                  "Misc is the per-record union of once-patch and go-patch. Unions count once per record.",
                  "Other primitive columns overlap.",
                  "These columns are not a partition of 86 bugs. Raw flags remain in records_detail.csv.", ""]
    (out / f"table{number}" / "comparison.md").write_text("\n".join(lines), encoding="utf-8")
    return diffs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/upstream")
    parser.add_argument("--output", type=Path, default=ROOT / "results/nonblocking")
    args = parser.parse_args()
    detail, candidates, digest, anomalies = load_records(args.data_dir)
    out = args.output
    csv_write(out / "records_detail.csv", detail)
    csv_write(out / "candidates.csv", candidates)
    counts9 = Counter((r["application"], r["cause"]) for r in detail)
    counts10 = Counter((r["cause"], r["strategy"]) for r in detail)
    counts11 = Counter((r["cause"], p) for r in detail for p in r["primitives"].split(";"))
    differences = {
        "table9": comparison(9, APPS, CAUSES, PAPER9, counts9, out),
        "table10": comparison(10, CAUSES, STRATEGIES, PAPER10, counts10, out),
        "table11": comparison(11, CAUSES, PRIMITIVES, PAPER11, counts11, out),
    }
    metadata = {"reference_commit": COMMIT, "workbook_sha256": digest,
                "utc_time": datetime.now(timezone.utc).isoformat(), "records": len(detail),
                "candidate_count": len(candidates), "candidate_causes": dict(Counter(c["cause"] for c in candidates)),
                "differing_cells": differences, "anomalies": anomalies,
                "paper_table12": {"traditional": 13, "anonymous": 4, "shared_lib": 2, "channel": 1},
                "cohort_note": "Workbook flags identify 23 records, not the paper's 20. No 20-case identity is inferred."}
    (out / "audit_run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: metadata[k] for k in ("records", "candidate_count", "candidate_causes", "differing_cells")}, indent=2))


if __name__ == "__main__":
    main()
