# Go Concurrency Bug Study: Course Reproduction

Our CS340 Operating Systems project studies **Understanding Real-World Concurrency Bugs in Go** (Tu, Liu, Song, and Zhang, ASPLOS 2019). This first update audits the dataset behind **Table 5**. It includes runnable analysis and traceable results. Historical Go applications and detector experiments have not been run.

- [Paper](https://songlh.github.io/paper/go-study.pdf) / [DOI](https://doi.org/10.1145/3297858.3304069)
- [Authors' dataset](https://github.com/system-pclub/go-concurrency-bugs), pinned to `f2655063a2278cff64a51121b73801eda05fdcfa`
- [Reading notes](docs/paper-notes.md): question, concepts, Figure 1, taxonomy, evidence, and our task
- [Method and discrepancy evidence](docs/reproduction-plan.md)

## First result

| Metric | Paper Table 5 | Our audit | Absolute difference |
| --- | ---: | ---: | ---: |
| Blocking records | 85 | 85 | 0 |
| Non-blocking records | 86 | 86 | 0 |
| Shared-memory flags | 105 | 106 | 1 |
| Message-passing flags | 66 | 66 | 0 |

**Behavior totals match; the exclusive root-cause taxonomy is only partially recovered.** One Kubernetes blocking record marks both root-cause flags as 1. Our root-cause columns count original flags independently, so they overlap; they do not describe 172 distinct bugs. Two BoltDB records use issue IDs rather than full hashes and are retained. No label is changed to match the paper.

See the generated [full comparison](results/table5/comparison.md) and [anomalies](results/table5/anomalies.csv). This verifies published annotations, not their independent correctness or detector effectiveness.

## Setup and run

Reference interpreter: **Python 3.12.13**, also recorded in `.python-version`. Install that interpreter and Git. No Go compiler or Excel installation is required. Both Python packages are pinned in `requirements.txt`.

Windows PowerShell, from the repository root:

```powershell
python --version
git --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

Linux/macOS with the same Python version:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

`run.py` is the build/run entry point; no compilation is needed. The first run clones the dataset into ignored `data/upstream`, checks out the pinned commit, verifies the workbook SHA-256, and writes `results/table5`. Installation and initial cloning need network access. The fetch script honors environment/system proxy settings for its Git subprocess only. Later runs reuse the verified checkout without fetching. Existing dirty or differently versioned checkouts are rejected, never reset.

To use an existing directory containing the unchanged `bug table.xlsx`:

```powershell
.\.venv\Scripts\python.exe run.py --data-dir "../origin_code/go-concurrency-bugs" --output-dir .cache/local-results
```

This is an example path, not a code dependency. `--data-dir`, `--fetch-dir`, and `--output-dir` accept arbitrary paths, including spaces. Defaults resolve from this repository. Local inputs are verified by exact workbook bytes; their Git HEAD is not assumed to equal the reference commit. Changed workbooks fail before analysis.

## Outputs and verification

| Output in `results/table5/` | Meaning |
| --- | --- |
| `records.csv` | 171 records, original IDs/flags, normalized application, source sheet and row |
| `counts.csv` | Per-application totals, flag marginals, ambiguous/unclassified counts |
| `comparison.csv`, `comparison.md` | Every Table 5 cell, signed and absolute differences |
| `anomalies.csv` | Two non-hash IDs and one dual-marked root cause |
| `row-audit.csv` | Inclusion/skip disposition for every physical row in both detail sheets |
| `run.json` | Input fingerprint, tool/OS versions, UTC timestamp, measured analysis time |

Expected stdout reports **171 records and 3 anomalies**. Analysis takes less than a second on the recorded machine; first-run network time varies and is included in printed total elapsed time. See [validation](results/validation.md) for actual commands and timings. CSV and comparison Markdown should be byte-identical between runs; `run.json` varies with time and environment.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover issue IDs, summary/blank rows, application aliases, missing/conflicting classification, duplicate records, and repeated issue IDs belonging to different commits. Duplicate record keys fail explicitly. Repeating deterministic counts checks consistency; it does not provide independent samples or a meaningful standard deviation.

## Attribution and repository management

The workbook and historical patch records belong to the original authors. The pinned upstream tree has no license file. We fetch it for analysis and do not vendor its workbook or patches. This repository contains our analysis code, derived audit outputs, and reading notes. All analysis code is new; no upstream file was modified. Data, virtual environments, caches, and credentials are ignored; small audit outputs are retained.

The course requires meaningful commits **pushed each Sunday by 23:59**, with the actual contributor's **student ID and full name** in each commit message. Confirmed contributor for this update: **1240029057 陈钰丰**, GitHub account **yufeng32**. Target repository: [yufeng32/os_paper](https://github.com/yufeng32/os_paper). This update is submitted under this contributor's identity with AI assistance as described below. Other members' identities and contributions have not been recorded. Final delivery requires substantive contributions from all four members and tag `v1.0`.

AI assistance: an AI assistant drafted the scripts, notes, and documentation and ran the recorded checks. Team members must review the materials. No AI-generated statement is presented as a runtime measurement. Later work must separately meet the requirements for runtime results, three independent runs, discrepancy analysis, and a controlled extension.
