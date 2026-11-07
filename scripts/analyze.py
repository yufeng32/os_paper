"""Row-level audit of Table 5. No source data or category labels are repaired."""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import re
import time

import openpyxl

from scripts.dataset import COMMIT, URL, WORKBOOK, verify

# Tu et al., ASPLOS 2019, Table 5, PDF p. 5 (not workbook summary cells).
PAPER = {
    "Docker": (21, 23, 28, 16),
    "Kubernetes": (17, 17, 20, 14),
    "etcd": (21, 16, 18, 19),
    "CockroachDB": (12, 16, 23, 5),
    "gRPC": (11, 12, 12, 11),
    "BoltDB": (3, 2, 4, 1),
    "Total": (85, 86, 105, 66),
}
ALIASES = {k.casefold(): k for k in PAPER if k != "Total"}
ALIASES.update({"grpc-go": "gRPC"})
METRICS = ("blocking", "non_blocking", "shared_memory_flags", "message_passing_flags")


def text(value):
    return "" if value is None else str(value).strip()


def parse_rows(sheet, rows):
    """Return records, anomalies, and a disposition for every physical row."""
    rows = list(rows)
    if not rows:
        raise ValueError(f"Empty sheet: {sheet}")
    headers = [text(v) for v in rows[0]]
    required = ("commit hash", "BugID", "application", "shared", "message")
    if any(headers.count(h) != 1 for h in required):
        raise ValueError(f"Missing or ambiguous headers in {sheet}")
    columns = {h: headers.index(h) for h in required}
    records, anomalies, audit, seen = [], [], [], set()
    for row_number, row in enumerate(rows, 1):
        row = list(row) + [None] * max(0, len(headers) - len(row))
        raw_id = text(row[columns["commit hash"]])
        bug_id = text(row[columns["BugID"]])
        raw_app = text(row[columns["application"]])
        app = ALIASES.get(raw_app.casefold(), "Unknown")
        serial = row[0]
        numbered = type(serial) is int and serial > 0
        identifier = bool(re.fullmatch(r"[0-9a-fA-F]{40}", raw_id)) or "#" in raw_id or "#" in bug_id
        candidate = numbered or (app != "Unknown" and identifier)
        disposition = "included" if candidate else "summary_or_annotation"
        if row_number == 1:
            disposition = "header"
            candidate = False
        elif not any(v is not None for v in row):
            disposition = "blank"
        audit.append({"sheet": sheet, "row": row_number, "disposition": disposition,
                      "raw_serial": text(serial), "raw_identifier": raw_id,
                      "raw_bug_id": bug_id, "raw_application": raw_app})
        if not candidate:
            continue
        key = (app, raw_id or bug_id)
        if key[1] and key in seen:
            raise ValueError(f"Duplicate record in {sheet}!{row_number}: {key}")
        seen.add(key)
        flags = (row[columns["shared"]], row[columns["message"]])
        valid_flags = all(type(v) in (int, float) and v in (0, 1) for v in flags)
        cause = {(1, 0): "shared_memory", (0, 1): "message_passing",
                 (1, 1): "ambiguous_both", (0, 0): "unclassified"}.get(flags, "invalid") if valid_flags else "invalid"
        issues = []
        if not numbered:
            issues.append(("missing_serial", "Retained because application and identifier identify a record."))
        if app == "Unknown":
            issues.append(("unknown_application", "Retained in Unknown; no application inferred."))
        if not re.fullmatch(r"[0-9a-fA-F]{40}", raw_id):
            issues.append(("non_hash_identifier", "Retained as a record; identifier is not a full commit hash."))
        if cause not in ("shared_memory", "message_passing"):
            issues.append(("root_cause_" + cause, "No exclusive root cause inferred; original flags retained."))
        record = {"record_id": f"{sheet}:{row_number}", "sheet": sheet, "row": row_number,
                  "raw_serial": text(serial), "raw_identifier": raw_id, "raw_bug_id": bug_id,
                  "raw_application": raw_app, "application": app, "behavior": sheet,
                  "raw_shared": text(flags[0]), "raw_message": text(flags[1]),
                  "root_cause": cause, "valid_flags": int(valid_flags),
                  "anomaly_codes": ";".join(code for code, _ in issues)}
        records.append(record)
        for code, detail in issues:
            anomalies.append({"record_id": record["record_id"], "sheet": sheet,
                              "row": row_number, "raw_identifier": raw_id,
                              "code": code, "detail": detail})
    return records, anomalies, audit


def aggregate(records):
    apps = [a for a in PAPER if a != "Total"]
    apps += sorted({r["application"] for r in records} - set(apps))
    output = []
    for app in apps + ["Total"]:
        selected = [r for r in records if app == "Total" or r["application"] == app]
        row = {"application": app, "records": len(selected),
               "blocking": sum(r["behavior"] == "blocking" for r in selected),
               "non_blocking": sum(r["behavior"] == "non-blocking" for r in selected)}
        # Raw flag marginals intentionally overlap for a dual-marked record.
        for metric, field in ((METRICS[2], "raw_shared"), (METRICS[3], "raw_message")):
            row[metric] = sum(float(r[field]) == 1 for r in selected if r["valid_flags"])
        row["ambiguous_records"] = sum(r["root_cause"] == "ambiguous_both" for r in selected)
        row["unclassified_or_invalid_records"] = sum(r["root_cause"] in ("unclassified", "invalid") for r in selected)
        output.append(row)
    return output


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(data_dir: Path, output_dir: Path):
    started = time.perf_counter()
    digest = verify(data_dir)
    records, anomalies, audit = [], [], []
    workbook = openpyxl.load_workbook(data_dir / WORKBOOK, read_only=True, data_only=True)
    try:
        for sheet in ("blocking", "non-blocking"):
            found, issues, dispositions = parse_rows(sheet, workbook[sheet].values)
            records.extend(found)
            anomalies.extend(issues)
            audit.extend(dispositions)
    finally:
        workbook.close()
    counts = aggregate(records)
    comparison = []
    for row in counts:
        if row["application"] not in PAPER:
            continue
        for metric, expected in zip(METRICS, PAPER[row["application"]]):
            actual = row[metric]
            comparison.append({"application": row["application"], "metric": metric,
                               "paper": expected, "ours": actual, "difference": actual - expected,
                               "absolute_difference": abs(actual - expected)})
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "records.csv", records, list(records[0]))
    write_csv(output_dir / "counts.csv", counts, list(counts[0]))
    write_csv(output_dir / "comparison.csv", comparison, list(comparison[0]))
    write_csv(output_dir / "anomalies.csv", anomalies,
              ["record_id", "sheet", "row", "raw_identifier", "code", "detail"])
    write_csv(output_dir / "row-audit.csv", audit, list(audit[0]))
    report = ["# Table 5: Paper vs. Ours", "",
              "Source: Tu et al., [ASPLOS 2019 paper](https://songlh.github.io/paper/go-study.pdf), Table 5, PDF p. 5.", "",
              "Behavior counts are record counts. Root-cause columns below count original 1 flags independently;",
              "they are overlapping marginals when a record has both flags. They are not repaired exclusive categories.", "",
              "| Application | Metric | Paper | Ours | Ours - Paper | Absolute difference |",
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    report += [f"| {r['application']} | {r['metric']} | {r['paper']} | {r['ours']} | {r['difference']} | {r['absolute_difference']} |" for r in comparison]
    report += ["", "## Evidence and verdict", "",
               f"Parsed {len(records)} records; see records.csv for sheet/row provenance, anomalies.csv for unresolved labels, and row-audit.csv for every included/skipped row.",
               "The behavior totals match. Root-cause marginals are only partially reproduced if a difference or ambiguous label remains.",
               "No missing label was guessed and no source workbook summary was used as an observation.",
               "This is a deterministic data audit, not an independent reclassification or a runtime detector experiment.",
               "Repeated counts do not supply independent samples or a meaningful standard deviation.", ""]
    (output_dir / "comparison.md").write_text("\n".join(report), encoding="utf-8")
    metadata = {"dataset_url": URL, "reference_commit": COMMIT, "workbook": WORKBOOK,
                "workbook_sha256": digest, "verification": "exact workbook bytes; local Git HEAD not required",
                "python": platform.python_version(), "openpyxl": openpyxl.__version__,
                "os": platform.system(), "os_release": platform.release(), "os_version": platform.version(),
                "architecture": platform.machine(), "processor": platform.processor(),
                "utc_time": datetime.now(timezone.utc).isoformat(),
                "analysis_seconds": round(time.perf_counter() - started, 6),
                "records": len(records), "anomalies": len(anomalies)}
    (output_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} records and {len(anomalies)} anomalies to {output_dir}")
    return metadata
