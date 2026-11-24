# Reproduction Scope and Deviations

**Historical status:** Week 3 update, 2026-11-18. Week 1 was the starting submission `fae5844` (2026-11-07); Week 2 was `e32a676` (2026-11-18, pinned environment and this scope declaration). This is a living document; later weeks append to it rather than rewriting history.

**Current addition (2026-11-24):** non-blocking coverage has been added using
the same pattern-level method. The Week 3 exclusions below are historical;
the appended non-blocking update and `results/nonblocking/` define the new scope.

## Why this document exists

The course brief states that "a reduced scale is acceptable if stated" (CS340 Research Paper Replication, Section 1, Assessment Criteria). This reproduction is deliberately partial. We state the scale, the claims and every deviation here instead of implying a full replication.

## Starting point

| Item | Value |
| --- | --- |
| Repository | https://github.com/yufeng32/os_paper.git |
| Branch | main |
| Starting commit | `fae5844` (2026-11-07, student 1240029057) |
| Paper | Tu, Liu, Song, Zhang, *Understanding Real-World Concurrency Bugs in Go*, ASPLOS 2019 |
| Authors' dataset | https://github.com/system-pclub/go-concurrency-bugs at `f2655063a2278cff64a51121b73801eda05fdcfa` |
| Workbook | `bug table.xlsx`, SHA-256 `a0e5f0103600b3c394b86cb975f403789366f0190312019fae648de0cd8e3235` |
| Reference interpreter | Python 3.12.3 locally (the pin is 3.12.13), openpyxl 3.1.5, et-xmlfile 2.0.0 |
| Go toolchain (Week 3 runtime) | go1.20.14 windows/amd64 (`D:\tools\go`) |
| Entry points | `run.py` (Table 5), `scripts/analyze_table6_7.py` (Tables 6–7), `scripts/dynamic/run_all.py` (Table 8) |

## Claims to be tested

| ID | Paper anchor | Claim | Method | Status |
| --- | --- | --- | --- | --- |
| C1 | Tables 5, 6, 7 | The published behaviour counts (85 blocking, 86 non-blocking) and the blocking root-cause/fix cross-tabs can be recovered from the pinned workbook. | Cell-by-cell static audit. | **Completed.** Table 5 behaviour totals match; Table 6 and Table 7 match the paper cell-for-cell (0 differences). |
| C2 | Table 8 | The built-in Go deadlock detector finds only a subset of the blocking bugs. | A reduced runtime subset (8 of the 21 reproduced blocking bugs), pattern-level reconstruction. | **Completed at reduced scale.** A = 3/8 detected (natural), B = 7/8 (forced all-asleep); paper 2/21. Verdict: partially supported. |

C1 carries its own discrepancy: one shared-memory root-cause cell differs by 1 (Table 5), and the exclusive cause of one Kubernetes record is unresolved. Table 6/7 reproduce exactly once the two ambiguous records are assigned explicitly (Docker `moby#25384` → Wait; Kubernetes `kubernetes#11298` → Chan w/). This verifies the published annotations and their arithmetic, not the independent correctness of every label.

## Scale: Week 3 historical scope

In scope and delivered:

1. Cell-by-cell static audit of **Table 5** (done, W1).
2. Static audit of **Table 6** (blocking root causes) and **Table 7** (blocking fix strategies) from the same 85 records (done, W3).
3. A reduced **Table 8** runtime subset: 8 of the 21 reproduced blocking bugs, each run 3 times in two modes (done, W3).
4. One controlled extension that changes a single factor (Week 4).
5. A six-section English report with claim verdicts, quantified gaps, a deviations table, a contribution statement and an AI usage statement.

Out of scope at Week 3, explicitly:

1. The complete commit history of all six studied applications.
2. Every triggered workload used in the paper.
3. The non-blocking side (Tables 9–12); only the tables tied to C1 and C2 are compared.
4. The paper's full detector comparison at its original scale.
5. Any assertion about label correctness or detector effectiveness that we did not measure ourselves.

## Deviations from the paper

| Item | Paper setting | Our setting | Reason |
| --- | --- | --- | --- |
| Input | Historical commits and patches across six applications | One pinned workbook export, fetched by script and verified byte-for-byte | Deterministic, offline-checkable input for a reduced-scale reproduction |
| Reproduction method | Built and ran the historical applications | **Pattern-level reconstruction**: each blocking case is a standalone Go program that keeps only the buggy control flow extracted from the fix-commit patch | The 2016-era trees are pre-modules (Godeps + `vendor`, Go 1.6/1.7) and cannot be built with Go 1.20 |
| Runtime sample | 21 reproduced blocking bugs (7 Mutex, 8 Chan, 4 Chan w/, 2 Lib) | **8 blocking bugs** from the workbook's `Reproduced? = 1` set: 2 Mutex, 3 Chan, 2 Chan w/, 1 Lib | Reduced scale, permitted if stated. Two of the paper's 21 (BoltDB#392/#240) have no patch in the pinned dataset and were excluded |
| Repetitions | One run per blocking bug (the paper notes blocking is deterministic) | **3 runs per case**, reported as a count; std = 0 because detection is binary and deterministic | Required by the course; also demonstrates determinism |
| Detector | Built-in Go deadlock detector | Same detector, in two modes: **A** natural behaviour, **B** forced all-asleep (`select{}`) | Mode B isolates the detector's all-asleep precondition behind the paper's 2/21 |
| Environment | The paper's original machines and Go toolchain | Windows 11, Go 1.20.14 windows/amd64, MinGW gcc 8.1.0; the container image pins the Python audit only | Recorded on the actual machine; Go added for the runtime experiment |
| Detector set | Multiple detectors in the paper | Only the built-in Go deadlock detector | We only report detectors we actually run |
| Statistical claim | Paper's published rates | Paper vs. Ours on the same metric for the 8 selected cases only | Repeated deterministic counts do not yield a meaningful standard deviation |

## Weekly delivery plan

Each row is one weekly check at Sunday 23:59.

| Week | Check date | Scope | Status |
| --- | --- | --- | --- |
| W1 | 2026-11-08 | Table 5 audit, README, reading notes, tests, validation | Delivered `fae5844` |
| W2 | 2026-11-15 | Pinned environment, Dockerfile/Makefile/preflight, scope + attribution | Delivered `e32a676` |
| W3 | 2026-11-22 | Tables 6–7 static audit, Table 8 reduced runtime subset, raw logs, report skeleton | **This update** |
| W4 | 2026-11-29 | One-factor extension, claim verdicts, quantified gaps, report draft | Pending |
| Final | 2026-12-01 | Report PDF, presentation, tag `v1.0` | Pending |

## Week 3 outcome

- **Table 6** (blocking root causes): 30/30 cells match the paper. Message passing causes 49/85 (58%) of blocking bugs — the paper's Observation 3 is reproduced.
- **Table 7** (blocking fix strategies): 30/30 cells match.
- **Table 8** (deadlock detector): 8 cases, A = 3/8 detected, B = 7/8 detected; the paper reports 2/21. The A→B gap shows the detector fires only when *all* goroutines are asleep; the four background-leak cases are detectable only in forced mode, and the pipe-I/O case (`moby#256`) is never detected because the block is not on a Go primitive. The paper's two detected cases (BoltDB#392/#240) could not be reconstructed (no patch). Verdict: **partially supported** (qualitative claim reproduced; exact rate not, for the stated reasons).
- **Exclusions:** `kubernetes#35672` (case b01, a prior member's separate feasibility study) is not in the `Reproduced? = 1` set and is not used here; BoltDB#392/#240 lack patches.

## What Week 2 explicitly did NOT contain (historical)

1. No Go programs, no detector invocation, no runtime measurements.
2. No changes to `run.py`, `scripts/analyze.py`, `scripts/dataset.py`, existing tests, or `results/table5/`.
3. No second analysis pipeline; every Makefile target wraps the existing `run.py`.

## Verification commands

```sh
# static audits
.venv/Scripts/python.exe scripts/verify_env.py
.venv/Scripts/python.exe run.py                      # Table 5  -> results/table5/
.venv/Scripts/python.exe scripts/analyze_table6_7.py # Tables 6-7
.venv/Scripts/python.exe -m unittest discover -s tests -v

# runtime (needs Go 1.20 on PATH)
.venv/Scripts/python.exe scripts/dynamic/run_all.py   # Table 8 -> results/runtime/
```

`make check` / `make env-record` remain available where `make` is installed. Week 3 logs record the OS, architecture and Go version behind every runtime number.

## Non-blocking update — 2026-11-24

The earlier Week 3 exclusion of Tables 9–12 is superseded for this addition.
The original blocking measurements remain unchanged.

- **C3, Tables 9–11: supported as an annotation audit.** All 86 non-blocking
  records are retained; 36, 30 and 42 non-total cells respectively match.
  Table 11 unions channel/select into Channel and once/go into Misc per record;
  independent primitive columns overlap. No source label is repaired.
- **C4, Table 12: partially supported in reconstructed workloads.** All 23
  workbook-flagged candidates are assessed: 14 show behavioral failures, 8 only
  target races, and one timer candidate remains unobserved. The three natural
  batches each report 18/23 candidates within 100 runs. This demonstrates
  non-blocking failures outside race detection, not the original 10/20 rate.

The natural matrix contains 27,600 executions with zero infrastructure errors
and 23/23 clean fixed controls (13,800 fixed executions). Mean candidate warning
coverage is 78.26%, sample SD 0.00 percentage points. An unobserved candidate
remains visible and is not an established detector miss. Controlled diagnostics
are stored separately and excluded from these rates.

The 23 flagged records comprise 13 traditional, 4 anonymous-function, 2 shared-library
and 4 channel cases; the paper uses only one channel case in its 20-case cohort.
No exact 20-case identity or quantitative equivalence is claimed. Each program
is an authored pattern reconstruction with source/fix mapping and case-level limits.
The pending-write-transaction path is reconstructed for BoltDB's merge record;
the upstream merge diff and regression test were inspected to supplement its empty dataset patch.

Two library/model boundaries matter: the historical context formatter is explicitly
modeled because Go 1.20 changed that behavior; the AfterFunc/Reset timer candidate
is not observed on this toolchain. Checkpoint publication uses a scalar length
over immutable backing rather than a racing multiword slice header. The preliminary
header version corrupted an output ID; that record was rejected, the whole attempt
and original source retained, and a fresh full matrix run after 1,200 clean scalar-model
validation executions. Preliminary results are excluded from final statistics.

The recorded environment is Go 1.20.14 windows/amd64, Python 3.12.13 and
MinGW-W64 gcc 16.1.0, with a verified portable Go archive. Up to eight same-combination
processes overlap, each with GOMAXPROCS=2; GORACE removes the exit delay after
target work joins. These are recorded workload deviations. See `results/nonblocking/`
for manifests, environment, CSVs and complete hashed log archives. The separate
Week 4 one-factor extension and final course deliverables remain pending.
