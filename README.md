# Go Concurrency Bug Study: Course Reproduction

Our CS340 Operating Systems project studies **Understanding Real-World Concurrency Bugs in Go** (Tu, Liu, Song, and Zhang, ASPLOS 2019). This repository reconstructs the paper's **classification (Table 5)**, its **blocking-bug root causes and fix strategies (Tables 6–7)**, and a **reduced-scale evaluation of the built-in deadlock detector (Table 8)**. The historical 2016-era applications are not built as-is; the runtime part is a pattern-level reconstruction of each bug's control flow (stated in [Scope and deviations](docs/reproduction-scope.md)). Every reported number is traceable to a script and a log in this repository.

- [Paper](https://songlh.github.io/paper/go-study.pdf) / [DOI](https://doi.org/10.1145/3297858.3304069)
- [Authors' dataset](https://github.com/system-pclub/go-concurrency-bugs), pinned to `f2655063a2278cff64a51121b73801eda05fdcfa`
- [Reading notes](docs/paper-notes.md): question, concepts, Figure 1, taxonomy, evidence, and our task
- [Scope, claims and deviations](docs/reproduction-scope.md)
- [Attribution, contributions and AI usage](ATTRIBUTION.md)

## Results (Paper vs. Ours)

### Table 5 — taxonomy (behaviour × cause)

| Metric | Paper Table 5 | Our audit | Absolute difference |
| --- | ---: | ---: | ---: |
| Blocking records | 85 | 85 | 0 |
| Non-blocking records | 86 | 86 | 0 |
| Shared-memory flags | 105 | 106 | 1 |
| Message-passing flags | 66 | 66 | 0 |

**Behaviour totals match; the exclusive root-cause taxonomy is only partially recovered.** One Kubernetes blocking record marks both root-cause flags as 1. Our root-cause columns count original flags independently, so they overlap; they do not describe 172 distinct bugs. Two BoltDB records use issue IDs rather than full hashes and are retained. No label is changed to match the paper. See [full comparison](results/table5/comparison.md) and [anomalies](results/table5/anomalies.csv).

### Table 6 — blocking-bug root causes (all 30 cells match)

| App | Mutex | RWMutex | Wait | Chan | Chan w/ | Lib | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Docker | 9 | 0 | 3 | 5 | 2 | 2 | 21 |
| Kubernetes | 6 | 2 | 0 | 3 | 6 | 0 | 17 |
| etcd | 5 | 0 | 0 | 10 | 5 | 1 | 21 |
| CockroachDB | 4 | 3 | 0 | 5 | 0 | 0 | 12 |
| gRPC | 2 | 0 | 0 | 6 | 2 | 1 | 11 |
| BoltDB | 2 | 0 | 0 | 0 | 1 | 0 | 3 |
| **Total** | **28** | **5** | **3** | **29** | **16** | **4** | **85** |

This reproduces the paper's headline Observation 3: **58% (49/85) of blocking bugs are caused by message passing**, not shared memory. Two ambiguous records are assigned explicitly (Docker `moby#25384` → Wait; Kubernetes `kubernetes#11298` → Chan w/) and listed in [edge cases](results/table6/edge_cases.md). See [comparison](results/table6/comparison.md).

### Table 7 — blocking-bug fix strategies (all cells match)

| Cause | Adds | Moves | Changes | Removes | Misc | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mutex | 9 | 7 | 2 | 8 | 2 | 28 |
| RWMutex | 0 | 2 | 0 | 3 | 0 | 5 |
| Wait | 0 | 1 | 0 | 1 | 1 | 3 |
| Chan | 15 | 1 | 5 | 4 | 4 | 29 |
| Chan w/ | 6 | 3 | 2 | 4 | 1 | 16 |
| Lib | 1 | 0 | 0 | 1 | 2 | 4 |
| **Total** | **31** | **14** | **9** | **21** | **10** | **85** |

### Table 8 — built-in deadlock detector (reduced scale: 8 blocking bugs)

The detector fires only when **all** goroutines are asleep. Each case runs in two modes: **A** natural behaviour (a background leak exits; a true deadlock hangs) and **B** forced all-asleep (`select{}`).

| Root cause | Paper used / detected | Ours used / detected (A) | Ours used / detected (B) |
| --- | ---: | ---: | ---: |
| Mutex | 7 / 1 | 2 / 1 | 2 / 2 |
| Chan | 8 / 0 | 3 / 0 | 3 / 3 |
| Chan w/ | 4 / 1 | 2 / 2 | 2 / 2 |
| Messaging Lib | 2 / 0 | 1 / 0 | 1 / 0 |
| **Total** | **21 / 2 (9.5%)** | **8 / 3 (37.5%)** | **8 / 7 (87.5%)** |

**Partially supported.** The paper's qualitative claim (the detector finds only a minority, and fails for background-leak and non-Go-primitive cases) is reproduced; the exact 2/21 rate is not, because the two cases the paper's detector caught (BoltDB#392/#240) have no patch in the pinned dataset and could not be reconstructed. The A→B gap (3→7) isolates the detector's all-asleep precondition. Details and per-case verdicts in [runtime comparison](results/runtime/comparison.md).

## Reproducibility (environment)

The environment is pinned in `Dockerfile` (`python:3.12.13-slim-bookworm`) and `.python-version`. `Makefile` wraps the existing scripts; it does not add a second analysis pipeline. The runtime experiment additionally needs Go 1.20.14 (`D:\tools\go` on the recorded machine) and a C compiler for `-race`; see `scripts/dynamic/README.md`.

## Setup and run

**Static audits (Table 5, 6, 7)** need Python 3.12 and Git only:

```sh
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt    # or .venv/bin/python on Linux
.venv/Scripts/python.exe run.py                                 # Table 5  -> results/table5/
.venv/Scripts/python.exe scripts/analyze_table6_7.py           # Tables 6-7 -> results/table6, results/table7
```

`run.py` clones the pinned dataset into ignored `data/upstream`, verifies the workbook SHA-256, and writes results. The fetch honours environment/system proxy for its Git subprocess only; existing dirty checkouts are rejected, never reset.

**Runtime experiment (Table 8)** needs Go 1.20 on `PATH`:

```sh
.venv/Scripts/python.exe scripts/dynamic/run_all.py            # builds + runs 8 cases x 2 modes x 3 -> results/runtime/
```

`b01` (`kubernetes#35672`, a supplementary case outside the 21-bug set) has its own reproducer in `scripts/dynamic/b01-listwatch/` and results in `results/runtime/b01/`.

## Outputs and verification

| Output | Meaning |
| --- | --- |
| `results/table5/` | Table 5 audit: records, counts, comparison, anomalies, row-audit, run.json |
| `results/table6/` | Table 6 audit: per-app root causes, `records_detail.csv`, `comparison.md`, `edge_cases.md` |
| `results/table7/` | Table 7 audit: cause × fix cross-tab, `comparison.md` |
| `results/runtime/` | Table 8: `candidates.csv`, `raw_results.csv`, `summary.csv`, `comparison.md`, one log per run |
| `scripts/dynamic/b01-listwatch/` + `results/runtime/b01/` | Supplementary b01 case (`kubernetes#35672`): reproducer and 3-run buggy/fixed logs |

Expected: `run.py` prints **171 records and 3 anomalies**; `analyze_table6_7.py` prints Table 6 totals `[28,5,3,29,16,4]` and Table 7 totals `[31,14,9,21,10]` with **0 differing cells**; `run_all.py` prints A = 3/8, B = 7/8 detected. Tests: `.venv/Scripts/python.exe -m unittest discover -s tests -v`.

## Attribution and repository management

The workbook and historical patch records belong to the original authors; the pinned upstream tree has no license file. We fetch it for analysis only and vendor neither the workbook nor the patches. All analysis code is new; no upstream file was modified. Data, virtual environments, caches and credentials are ignored; small audit outputs are retained.

The course requires meaningful commits **pushed each Sunday by 23:59**, with the contributor's **student ID and full name** in each commit message. Per-week contributions are recorded in [ATTRIBUTION.md](ATTRIBUTION.md). Final delivery requires substantive contributions from all four members and tag `v1.0`.
