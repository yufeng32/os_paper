# Reproduction Scope and Deviations

**Status:** Week 2 declaration, 2026-11-13. Week 1 was the team lead's starting submission at `fae5844` (checked 2026-11-08). This is a living document; later weeks append to it rather than rewriting history.

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
| Reference interpreter | Python 3.12.13, openpyxl 3.1.5, et-xmlfile 2.0.0 |
| Entry point | `run.py` (unchanged by Week 2) |

## Claims to be tested

Two claims are fixed now. A third may be added in Week 3 only after the paper's results tables have been checked against the dataset; we do not assign a table number without checking it.

| ID | Paper anchor | Claim | Method | Status |
| --- | --- | --- | --- | --- |
| C1 | Table 5 | The published behaviour counts (85 blocking, 86 non-blocking) can be recovered from the pinned workbook. | Cell-by-cell static audit. | Completed at the starting commit; see `results/table5/comparison.md`. |
| C2 | Table 8, to be confirmed in Week 3 | Dynamic detectors find a subset of the blocking bugs in the study. | A small runtime subset that we can actually build and trigger. | Planned for Week 3. |

C1 is already reported with its own discrepancy: one shared-memory root-cause cell differs by 1, and the exclusive cause of one Kubernetes record is unresolved. This verifies the published annotations and their arithmetic, not the independent correctness of every label. `docs/reproduction-plan.md` links the next blocking case to Table 8; we will confirm the exact table and metric before writing the Paper vs. Ours table.

## Scale: what is reproduced

In scope:

1. Cell-by-cell static audit of Table 5 from the pinned workbook (already done).
2. A small number of historical bug cases that can be built and triggered (Week 3).
3. Three independent runtime runs per selected case, reported as mean +/- standard deviation.
4. One controlled extension that changes a single factor, on the same hardware and workload (Week 4).
5. A six-section English report with claim verdicts, quantified gaps, a deviations table, a contribution statement and an AI usage statement.

Out of scope, explicitly:

1. The complete commit history of all six studied applications.
2. Every triggered workload used in the paper.
3. Every figure and table in the paper; only the tables tied to C1 and C2 are compared.
4. The paper's full detector comparison at its original scale.
5. Any assertion about label correctness or detector effectiveness that we did not measure ourselves.

## Deviations from the paper

| Item | Paper setting | Our setting | Reason |
| --- | --- | --- | --- |
| Input | Historical commits and patches across six applications | One pinned workbook export, fetched by script and verified byte-for-byte | Deterministic, offline-checkable input for a reduced-scale reproduction |
| Runtime sample | A larger set of triggered blocking and non-blocking cases | A small subset selected by build/trigger feasibility in Week 3; exact cases and count to be recorded there | Reduced scale is permitted if stated; infeasible builds are reported as feasibility outcomes, not negative results |
| Repetitions | Not reported as three independent runs in the static study | Three independent runs per runtime metric, mean +/- standard deviation | Required by the course assessment criteria |
| Environment | The paper's original machines and Go toolchain | Pinned container: Debian bookworm, Python 3.12.13, pinned packages; Go toolchain to be pinned in Week 3 | Reproducibility on a clean machine; versions must be recorded |
| Detector set | Multiple detectors in the paper | A detector subset chosen after the Week 3 feasibility check | We only report detectors we actually run |
| Statistical claim | Paper's published rates | Paper vs. Ours on the same metric and setting for the selected cases only | Repeated deterministic counts do not satisfy the statistical requirement |

## Weekly delivery plan

Each row is one weekly check at Sunday 23:59. Later code is intentionally not written in earlier weeks.

| Week | Check date | Scope | Files added |
| --- | --- | --- | --- |
| W1 | 2026-11-08 | Team lead's starting submission, already pushed | `fae5844`: Table 5 audit, README, reading notes, tests and validation |
| W2 | 2026-11-15 | Pinned environment and a written scope declaration | `Dockerfile`, `.dockerignore`, `Makefile`, `scripts/verify_env.py`, `tests/test_verify_env.py`, `docs/reproduction-scope.md`, `ATTRIBUTION.md`, and a short README section |
| W3 | 2026-11-22 | Reduced runtime subset, three independent runs, raw logs | `scripts/dynamic/`, `results/runtime/`, `report/` skeleton |
| W4 | 2026-11-29 | One-factor extension, claim verdicts, quantified gaps, report draft | `results/extension/`, `report/` sections |
| Final | 2026-12-01 | Report PDF, presentation, tag `v1.0` | none |

## What Week 2 explicitly does NOT contain

1. No Go programs, no detector invocation, no runtime measurements.
2. No changes to `run.py`, `scripts/analyze.py`, `scripts/dataset.py`, existing tests, or `results/table5/`.
3. No second analysis pipeline; every Makefile target wraps the existing `run.py`.
4. No claim verdicts, no statistics, no figures, no extension results.
5. No vendored workbook, patches, or files over 50 MB.

## Verification commands

```sh
make check          # preflight report
make env-record     # write results/environment.json
make run            # existing Table 5 audit, 171 records and 3 anomalies
make test           # unit tests
make docker-build   # pinned container; RUN verifies the environment
make docker-run     # audit inside the container
```

`make env-record` writes `results/environment.json` so that the operating system, kernel-level version string, architecture and interpreter behind any later number are traceable. Week 3 runtime logs must record the same fields.
