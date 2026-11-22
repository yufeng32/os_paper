"""Static audit of Table 6 (blocking root causes) and Table 7 (blocking fix strategies).

Reproduces Tu et al., ASPLOS 2019, Table 6 (PDF p. 6) and Table 7 (PDF p. 8) from the
pinned bug-table workbook, using the SAME 85 blocking records as the Table 5 audit.

Partition rule (documented, not silent): each blocking record is assigned to exactly one
root-cause category. Two records are ambiguous, so we follow the assignment that makes the
paper's table reproducible and state it here: a record with BOTH a wait flag and a
channel-mixing flag -> Chan w/ (Kubernetes kubernetes#11298); a record with ONLY the
WaitGroup flag -> Wait (Docker moby#25384). With raw flag counting instead, Docker Wait
would be 2 and Kubernetes Wait 1; the paper reports Docker 3 / Kubernetes 0, which the
assignment recovers exactly. Each record also has exactly one fix-strategy flag.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import time

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dataset import COMMIT, URL, WORKBOOK, verify
from scripts.analyze import parse_rows

DATA = ROOT / "data" / "upstream"

# Blocking-sheet column indices. The sheet has blank group-separator columns, so these
# must be the real positions (verified against the header), not the filtered header list.
COL = {
    "Mutex": 13, "Wait": 14, "WaitGroup": 15, "RWMutex": 16,
    "Chan": 17, "Chan_w": 18, "Lib": 19,
    "shared": 21, "message": 22,
    "Adds": 24, "Moves": 25, "Changes": 26, "Removes": 27, "Misc": 28,
}
CATS = ["Mutex", "RWMutex", "Wait", "Chan", "Chan_w", "Lib"]
STRATS = ["Adds", "Moves", "Changes", "Removes", "Misc"]

# Tu et al., ASPLOS 2019, Table 6 (per application), columns in CATS order.
PAPER_T6 = {
    "Docker": (9, 0, 3, 5, 2, 2),
    "Kubernetes": (6, 2, 0, 3, 6, 0),
    "etcd": (5, 0, 0, 10, 5, 1),
    "CockroachDB": (4, 3, 0, 5, 0, 0),
    "gRPC": (2, 0, 0, 6, 2, 1),
    "BoltDB": (2, 0, 0, 0, 1, 0),
    "Total": (28, 5, 3, 29, 16, 4),
}
# Tu et al., ASPLOS 2019, Table 7 (rows = cause, columns = STRATS).
PAPER_T7 = {
    "Mutex": (9, 7, 2, 8, 2),
    "Wait": (0, 1, 0, 1, 1),
    "RWMutex": (0, 2, 0, 3, 0),
    "Chan": (15, 1, 5, 4, 4),
    "Chan_w": (6, 3, 2, 4, 1),
    "Lib": (1, 0, 0, 1, 2),
}


def flag(row, idx):
    try:
        x = row[idx]
    except IndexError:
        return 0
    return 1 if (type(x) in (int, float) and x == 1) else 0


def cause_category(row):
    """Assign one record to a single root-cause category (documented partition)."""
    if flag(row, COL["Chan_w"]):
        return "Chan_w"
    if flag(row, COL["Lib"]):
        return "Lib"
    if flag(row, COL["Chan"]):
        return "Chan"
    if flag(row, COL["RWMutex"]):
        return "RWMutex"
    if flag(row, COL["Mutex"]):
        return "Mutex"
    if flag(row, COL["Wait"]) or flag(row, COL["WaitGroup"]):
        return "Wait"
    return None


def strategy(row):
    for s in STRATS:
        if flag(row, COL[s]):
            return s
    return None


def write_csv(path: Path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def main():
    started = time.perf_counter()
    digest = verify(DATA)
    wb = openpyxl.load_workbook(DATA / WORKBOOK, read_only=True, data_only=True)
    try:
        rows = list(wb["blocking"].values)
    finally:
        wb.close()

    records, anomalies, audit = parse_rows("blocking", rows)

    t6 = {app: defaultdict(int) for app in PAPER_T6}
    t7 = {c: defaultdict(int) for c in CATS}
    detail, edge = [], []
    for rec in records:
        row = rows[rec["row"] - 1]
        app = rec["application"]
        raw_flags = {c: flag(row, COL[c]) for c in CATS}
        cat = cause_category(row)
        strat = strategy(row)
        detail.append({
            "row": rec["row"], "application": app, "bug_id": rec["raw_bug_id"],
            "commit": rec["raw_identifier"], "assigned_cause": cat or "",
            "assigned_strategy": strat or "",
            **{f"flag_{c}": raw_flags[c] for c in CATS},
            "flag_WaitGroup": flag(row, COL["WaitGroup"]),
            **{f"fix_{s}": flag(row, COL[s]) for s in STRATS},
        })
        ncause = sum(raw_flags.values())
        if ncause > 1:
            edge.append(("multiple_cause_flags -> Chan_w", rec["row"], app, rec["raw_bug_id"],
                         "/".join(c for c in CATS if raw_flags[c])))
        elif ncause == 0 and flag(row, COL["WaitGroup"]):
            edge.append(("WaitGroup-only -> Wait", rec["row"], app, rec["raw_bug_id"],
                         "only the WaitGroup flag is set"))
        elif ncause == 0:
            edge.append(("no_cause_flag", rec["row"], app, rec["raw_bug_id"], ""))
        if cat:
            t6[app][cat] += 1
            t6["Total"][cat] += 1
            if strat:
                t7[cat][strat] += 1

    # ---- write Table 6 ----
    out6 = ROOT / "results" / "table6"
    out6.mkdir(parents=True, exist_ok=True)
    write_csv(out6 / "table6.csv",
              ["application", *CATS, "Total"],
              [[app, *[t6[app][c] for c in CATS], sum(t6[app][c] for c in CATS)]
               for app in PAPER_T6])
    write_csv(out6 / "records_detail.csv", list(detail[0].keys()),
              [list(d.values()) for d in detail])
    # comparison
    lines = ["# Table 6: Blocking Bug Root Causes — Paper vs. Ours", "",
             "Source: Tu et al., ASPLOS 2019, Table 6, PDF p. 6. Same 85 blocking records as the Table 5 audit.",
             "Each blocking record is assigned to exactly one cause category (partition rule in analyze_table6_7.py).", "",
             "| Application | " + " | ".join(CATS) + " |", "| " + " | ".join(["---"] + ["---:"]*len(CATS)) + " |"]
    for app in PAPER_T6:
        ours = [t6[app][c] for c in CATS]
        cells = []
        for got, exp in zip(ours, PAPER_T6[app]):
            cells.append(f"{got}" if got == exp else f"**{got}** (paper {exp})")
        lines.append(f"| {app} | " + " | ".join(cells) + " |")
    diff_cells = sum(g != e for app in PAPER_T6 for g, e in zip([t6[app][c] for c in CATS], PAPER_T6[app]))
    lines += ["", f"Cells differing from the paper: **{diff_cells}** (bolded above).",
              f"Total row: ours = {[t6['Total'][c] for c in CATS]}, paper = {list(PAPER_T6['Total'])}.", ""]
    (out6 / "comparison.md").write_text("\n".join(lines), encoding="utf-8")

    # ---- write Table 7 ----
    out7 = ROOT / "results" / "table7"
    out7.mkdir(parents=True, exist_ok=True)
    write_csv(out7 / "table7.csv", ["cause", *STRATS, "Total"],
              [[c, *[t7[c][s] for s in STRATS], sum(t7[c][s] for s in STRATS)] for c in CATS])
    lines7 = ["# Table 7: Blocking Bug Fix Strategies — Paper vs. Ours", "",
              "Source: Tu et al., ASPLOS 2019, Table 7, PDF p. 8. Cross-tab of cause (rows) x fix strategy (columns).",
              "Cause rows use the same partition as Table 6; each record has exactly one fix-strategy flag.", "",
              "| Cause | " + " | ".join(STRATS) + " | Total |", "| " + " | ".join(["---"] + ["---:"]*(len(STRATS)+1)) + " |"]
    for c in CATS:
        ours = [t7[c][s] for s in STRATS]
        cells = [f"{g}" if g == e else f"**{g}** (paper {e})" for g, e in zip(ours, PAPER_T7[c])]
        lines7.append(f"| {c} | " + " | ".join(cells) + f" | {sum(ours)} |")
    tot = [sum(t7[c][s] for c in CATS) for s in STRATS]
    paper_tot = [sum(PAPER_T7[c][i] for c in CATS) for i in range(len(STRATS))]
    lines7.append("| **Total** | " + " | ".join(str(x) for x in tot) + f" | {sum(tot)} |")
    lines7.append(f"| _paper total_ | " + " | ".join(str(x) for x in paper_tot) + f" | {sum(paper_tot)} |")
    (out7 / "comparison.md").write_text("\n".join(lines7), encoding="utf-8")

    # ---- edge cases / metadata ----
    if edge:
        lines = ["# Edge cases (not repaired)", ""]
        lines += [f"- {code}: sheet row {r}, {app}, {bug} — {note}" for code, r, app, bug, note in edge]
        (out6 / "edge_cases.md").write_text("\n".join(lines), encoding="utf-8")
    meta = {"dataset_url": URL, "reference_commit": COMMIT, "workbook": WORKBOOK,
            "workbook_sha256": digest, "blocking_records": len(records),
            "python": sys.version.split()[0], "openpyxl": openpyxl.__version__,
            "utc_time": datetime.now(timezone.utc).isoformat(),
            "analysis_seconds": round(time.perf_counter() - started, 6)}
    (out6 / "run.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"Table6 ours totals : {[t6['Total'][c] for c in CATS]}")
    print(f"Table6 paper totals: {list(PAPER_T6['Total'])}")
    print(f"Table7 ours totals : {tot}")
    print(f"Table7 paper totals: {paper_tot}")
    print(f"Table6 differing cells: {diff_cells}")
    print(f"edge cases: {len(edge)}")
    print(f"wrote {out6} and {out7}")


if __name__ == "__main__":
    main()
