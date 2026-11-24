# Reproducing *Understanding Real-World Concurrency Bugs in Go* at Reduced Scale

**CS340 Operating Systems — Research Paper Replication**
Group: 1240029057 陈钰丰 (yufeng32), 1240026499 沈漠 (woshimoshen), 1240026895 章钧钧 (siriuszhang06-wq), + one member.
**Status:** Week 3 draft with a 2026-11-24 non-blocking addition. The separate one-factor Extension (Section 5) remains pending; adding non-blocking coverage does not complete that extension.

## Abstract

We reproduce selected results of Tu et al., *Understanding Real-World Concurrency Bugs in Go* (ASPLOS 2019), using a pinned annotation audit and standalone bug-pattern reconstructions. Table 5's behaviour totals match, while one root-cause margin retains a documented source discrepancy. Tables 6–7 and 9–11 match cell-for-cell. In the eight-case blocking experiment, the built-in detector reports three cases naturally and seven when every goroutine is forced asleep; the paper reports two of 21. The non-blocking addition assesses 23 workbook-flagged candidate commits through buggy/fixed programs. Across 27,600 executions, 14 candidates show target behavioral failures and eight show only target races; one historical timer candidate remains unobserved. Each of three 100-run batches reports target races for 18/23 candidates, with all fixed controls clean. The paper's Table 12 used 20 cases and detected 10. Different cohort membership, reconstructed workloads and library behavior prevent exact-rate comparison. Every result traces to a script and retained log; neither runtime experiment builds the complete historical applications.

## 1. Introduction and Claims

### 1.1 Paper and problem

Go encourages message passing (channels) over shared memory, on the belief that explicit message passing is less error-prone. The paper performs the first systematic, empirical study of real Go concurrency bugs across six production applications (Docker, Kubernetes, etcd, CockroachDB, gRPC, BoltDB), classifying 171 bugs along two orthogonal axes — **behaviour** (blocking / non-blocking) and **cause** (shared memory / message passing) — and evaluating two built-in detectors. Its headline finding is that message passing is no safer than shared memory: about 58% of blocking bugs are caused by message passing.

### 1.2 Claims tested

- **C1 (Tables 5, 6, 7).** The published behaviour counts and the blocking root-cause/fix cross-tabs are recoverable from the pinned workbook.
- **C2 (Table 8).** The built-in Go deadlock detector finds only a subset of the blocking bugs.
- **C3 (Tables 9–11).** The non-blocking root-cause, fix-strategy and fix-primitive tables are recoverable from the same pinned workbook.
- **C4 (Table 12, different cohort).** Race-detector warnings cover only part of the non-blocking candidate mechanisms; logical non-blocking failures must be measured separately from data races.

### 1.3 Scope

Reduced scale, stated up front. We audit Tables 5–7 and 9–11 from the workbook, and evaluate Table 8 on 8 of the 21 blocking bugs. For the non-blocking addition we assess all 23 commit records marked `Reproduced? = 1`, using standalone buggy/fixed patterns. The paper's Table 12 used 20 cases; its exact membership has not been recovered. We do not build the historical applications or claim identical detector workloads (see 2.4).

## 2. Reproduction Setup

### 2.1 Starting code and commits

| Item | Value |
| --- | --- |
| Repository | https://github.com/yufeng32/os_paper |
| Starting commit | `fae5844` (Table 5 audit, 2026-11-07) |
| Dataset | `system-pclub/go-concurrency-bugs` at `f2655063…` |
| Workbook | `bug table.xlsx`, SHA-256 `a0e5f010…` |

Table 5, 6, 7 reuse the same inclusion rule (`scripts/analyze.py: parse_rows`), which yields the paper's 85 blocking and 86 non-blocking records. The two ambiguous blocking records are assigned explicitly: Docker `moby#25384` (WaitGroup-only) → Wait; Kubernetes `kubernetes#11298` (wait + channel-mixing) → Chan w/.

### 2.2 Environment

| Item | Value |
| --- | --- |
| OS | Windows 11 (10.0.26200), x86-64 |
| Python | Blocking record: 3.12.3; non-blocking run: 3.12.13; openpyxl 3.1.5, et-xmlfile 2.0.0 |
| Go (runtime) | go1.20.14 windows/amd64 |
| C compiler | Historical blocking record: MinGW gcc 8.1.0 (unused in Table 8); non-blocking run: MinGW-W64 gcc 16.1.0 |
| Container | `python:3.12.13-slim-bookworm` pins the Python audits |

### 2.3 Workloads and inputs

- Static audits: the pinned workbook, verified byte-for-byte by SHA-256.
- Runtime (Table 8): 8 of the 21 blocking bugs marked `Reproduced? = 1`, chosen to span Mutex (2), Chan (3), Chan w/ (2) and Messaging Lib (1). Each case is a standalone Go program that keeps only the buggy control flow extracted from the fix-commit patch.
- Runtime (non-blocking): 23 candidate commits, with 13 traditional, 4 anonymous-function, 2 shared-library and 4 channel labels. The paper has only one channel case in its 20-case sample. Each reconstructed case has buggy/fixed variants under ordinary and `-race` builds. Three batches each use 100 independent process runs per combination (27,600 total); controlled diagnostics are separate. Eight same-combination repetitions can overlap, each with GOMAXPROCS=2. GORACE removes the exit delay after workers have joined. These settings are recorded and are deviations from the historical experiment.

### 2.4 Deviations

| Item | Paper | Ours | Reason |
| --- | --- | --- | --- |
| Method | Built and ran the historical applications | Pattern-level reconstruction | 2016-era trees are pre-modules and unbuildable with Go 1.20 |
| Runtime sample | 21 blocking bugs | 8 (2 Mutex, 3 Chan, 2 Chan w/, 1 Lib) | Reduced scale; BoltDB#392/#240 lack patches |
| Repetitions | One run (blocking is deterministic) | 3 runs per case | Course requirement; confirms determinism |
| Detector modes | Natural | A natural; B forced all-asleep | B isolates the all-asleep precondition |
| Environment | Paper's machines | Windows 11, Go 1.20.14 | Recorded on the actual machine |
| Non-blocking sample | 20 cases, including 1 channel case | 23 workbook candidates, including 4 channel cases | Exact paper membership is not established; candidates are not silently dropped |
| Non-blocking libraries | Historical Go/dependencies | Timer API pattern retained; old context formatter explicitly modeled | Modern context no longer formats non-Stringer values; case-level substitutions are documented |
| Checkpoint model | Shared slice copied after Unlock | Immutable backing plus scalar published length; copy reads length outside/inside mu | Preserves missed-lock mechanism while excluding unsafe multiword-header tearing; preliminary rejected attempt retained |

## 3. Results

### 3.1 Table 5 — taxonomy

Behaviour totals match (85 blocking, 86 non-blocking). Root-cause marginals: 106 shared-memory (paper 105, +1) and 66 message-passing. The +1 is one Kubernetes record with both root-cause flags set, retained rather than repaired.

### 3.2 Table 6 — blocking root causes (30/30 cells match)

Total: Mutex 28, RWMutex 5, Wait 3, Chan 29, Chan w/ 16, Lib 4 = 85. Message passing (Chan 29 + Chan w/ 16 + Lib 4 = 49) is 58% of blocking bugs — Observation 3 reproduced. See `results/table6/comparison.md`.

### 3.3 Table 7 — blocking fix strategies (30/30 cells match)

Total: Adds 31, Moves 14, Changes 9, Removes 21, Misc 10 = 85. See `results/table7/comparison.md`.

### 3.4 Table 8 — built-in deadlock detector (reduced scale)

| Root cause | Paper used / detected | Ours A used / detected | Ours B used / detected |
| --- | ---: | ---: | ---: |
| Mutex | 7 / 1 | 2 / 1 | 2 / 2 |
| Chan | 8 / 0 | 3 / 0 | 3 / 3 |
| Chan w/ | 4 / 1 | 2 / 2 | 2 / 2 |
| Messaging Lib | 2 / 0 | 1 / 0 | 1 / 0 |
| **Total** | **21 / 2 (9.5%)** | **8 / 3 (37.5%)** | **8 / 7 (87.5%)** |

Detection is binary and deterministic; the three runs per case agree (std = 0). See `results/runtime/comparison.md` and the per-run logs.

### 3.5 Tables 9–11 — non-blocking static audit

All 86 non-blocking records are retained. Table 9 matches 36/36 non-total cells,
Table 10 matches 30/30 and Table 11 matches 42/42. Root-cause totals are
46 traditional, 11 anonymous-function, 6 WaitGroup, 6 shared-library,
16 channel and 1 message-library. Fix-strategy totals are 42 Adds, 17 Moves,
10 Bypass, 14 Private and 3 Misc. In Table 11, Channel unions channel/select
flags and Misc unions once/go flags per record; other primitive columns overlap.
These findings recover annotations and arithmetic rather than independent ground truth.

### 3.6 Non-blocking detector comparison — different cohort

| Cause | Paper used/detected | Our candidates/reported per batch |
| --- | ---: | ---: |
| Traditional | 13/7 | 13/12 |
| Anonymous function | 4/3 | 4/4 |
| Shared-memory library | 2/0 | 2/1 |
| Channel misuse | 1/0 | 4/1 |
| **Total** | **20/10** | **23/18** |

Three batches of 100 runs per case/variant/build produce 27,600 executions:
14 candidates exhibit a wrong result, target panic or ordering violation;
8 have target race reports without a separate visible error; one remains
unobserved. All 23 fixed controls pass across 13,800 executions, and there are
zero infrastructure errors. Every batch reports 18/23 candidates within its
100-run budget (candidate warning coverage 78.26%, sample SD 0.00 percentage points).
The unobserved candidate remains in the candidate table and is not classified
as an established detector miss. The denominator describes assessed candidates,
not independently confirmed failures on every run.

Four observed mechanisms have no target race warning: the missed stdin-close
notification, deferred close of an uninitialized channel, Write after WriteStatus,
and Close preceding transaction completion. Their symptoms are distinct from
the conflicting shared-memory accesses reported by `-race`. The historical
etcd#3593 timer pattern remains unobserved. The context formatter is explicitly
reconstructed from historical Go semantics; the checkpoint model uses a scalar
publication count to preserve a missed-lock access without corrupting result metadata.

The 23-candidate sample differs from the paper's 20-case sample in channel
membership (four versus one), and its exact 20-case identity is unknown.
Isolating and repeating the key operations changes the workload; library and
toolchain differences also matter. The higher warning coverage therefore does
not establish better detector accuracy than the paper. Controlled diagnostics
are separate. The full natural archive contains all 27,600 hashed logs, and
verification confirms every matrix cell, classification and case summary.

### 3.7 Traceability

| Result | Script | Output | Command |
| --- | --- | --- | --- |
| Table 5 | `run.py`, `scripts/analyze.py` | `results/table5/` | `.venv/Scripts/python.exe run.py` |
| Tables 6–7 | `scripts/analyze_table6_7.py` | `results/table6/`, `results/table7/` | `.venv/Scripts/python.exe scripts/analyze_table6_7.py` |
| Table 8 | `scripts/dynamic/run_all.py` | `results/runtime/` | `.venv/Scripts/python.exe scripts/dynamic/run_all.py` |
| Tables 9–11 | `scripts/analyze_nonblocking.py` | `results/nonblocking/table9/`, `table10/`, `table11/` | `.venv/Scripts/python.exe scripts/analyze_nonblocking.py` |
| Table 12 comparison | `scripts/dynamic/nonblocking/run.py` | `results/nonblocking/runtime/` | `.venv/Scripts/python.exe scripts/dynamic/nonblocking/run.py` |

## 4. Analysis of Discrepancies

### 4.1 Claim verdicts

- **C1: supported.** Tables 5 (behaviour), 6 and 7 recover exactly; the single Table 5 root-cause discrepancy is a documented dual-flag record, not an error.
- **C2: partially supported.** The qualitative claim (the detector misses most blocking bugs) holds; the exact 2/21 rate does not transfer at this scale.
- **C3: supported as an annotation audit.** All 108 non-total cells across Tables 9–11 match; source classifications are not independently revalidated.
- **C4: partially supported for reconstructed workloads.** Four observed non-blocking mechanisms have no target race warning, but the exact original 10/20 detector result is not reproduced. The differing cohort and workloads prevent a direct accuracy comparison.

### 4.2 Gaps and their explanation

- **A vs B (3/8 vs 7/8).** The four background-leak cases (docker_17176, etcd_4474, grpc_1850, grpc_1293) are missed naturally because the leaked goroutine coexists with a running/exiting process, so "all goroutines asleep" never holds; forcing all-asleep detects them. This isolates the detector's precondition.
- **moby#256 (Lib) never detected.** Its deadlock is on OS pipe I/O, not a Go primitive; the detector only inspects goroutines blocked on Go primitives.
- **Ours 37.5% > paper 9.5%.** (1) The eight reconstructable cases are biased toward true circular deadlocks; (2) the paper's two detected cases are BoltDB#392/#240, which have no patch in the pinned dataset; (3) our true-deadlock cases have `main` waiting, as a hung program would.

### 4.3 Evidence

Every claim above is backed by a logged run: `results/runtime/raw_results.csv`, `results/runtime/summary.csv`, and one `<case>_<mode>_<n>.log` per run (containing either the detector's `fatal error: all goroutines are asleep` and a goroutine dump, a clean exit, or a timeout with no detector output).

For the non-blocking addition, `results/nonblocking/table9/` through `table11/`
contain cell comparisons, while `runtime/` contains all 27,600 execution records
and logs.zip. `verification.json` confirms every archived hash, matrix cell,
classification and case summary. `diagnostic/` preserves 276 separate controlled
runs; `model_validation/` preserves 1,200 scalar-model validation runs. The
interrupted composite-header attempt, including the rejected output identity,
is retained separately under `preliminary/` and excluded from final statistics.

### 4.4 Limitations

- Pattern-level reconstruction omits the applications' surrounding logic and timing; it shows that a bug **can** block, not how often it does in production.
- 8 of 21 cases; two of the paper's detected cases are unreconstructable here.
- The non-blocking addition reconstructs patterns rather than original applications. Its 23 candidate records differ from the paper's 20-case detector sample, and its seed values do not reproduce OS scheduling. A candidate with no observed error or target warning is not an established detector miss.

## 5. Extension (Week 4 — pending)

One controlled experiment beyond the paper, changing a single factor. Candidate: re-run the same blocking cases on a different Go toolchain version (or a second, independent detector) on the same machine and workload, and interpret the effect on the detection rate. To be completed in Week 4 with results in `results/extension/`.

## 6. Conclusion

The pinned workbook recovers the behaviour totals and the blocking/non-blocking
root-cause and fix tables, with the documented Table 5 root-cause discrepancy
retained. The blocking detector experiment reproduces the all-asleep and I/O
boundaries on a reduced subset. The non-blocking reconstructions demonstrate
both target data races and observable failures outside race detection, while
one historical timer candidate remains unobserved. Cohort, workload and library
differences prevent reproducing the original detector rates exactly.
**Overall verdict: partially reproduced.**

### Lessons learned

1. Reproducing a data-classification paper from its own dataset recovers its arithmetic but not the independent correctness of every label.
2. Reproducing a detector evaluation requires reconstructing the blocking condition, and Go's detector only speaks when every goroutine is asleep — a precondition easy to overlook and easy to accidentally satisfy with a spurious `main` block.
3. Missing patches (two BoltDB cases) can remove exactly the cases that matter, and must be reported as a deviation rather than hidden.
4. A non-blocking failure and a data-race report are different observations. Lost notifications, invalid channel operations and transaction-order violations require their own symptom checks, while an unobserved historical library candidate must remain unconfirmed.

## Contribution and AI usage

**Contribution statement.** W1 (1240029057 陈钰丰): Table 5 audit and reading notes. W2 (1240026895 章钧钧): pinned environment and scope declaration. W3 (1240026499 沈默): b01 (Kubernetes #35672) ListAndWatch resync goroutine-leak runtime case, supplementary to the 21-bug Table 8 set. W3 (1240029367 邵杰): Tables 6–7 audit, Table 8 reduced runtime subset, report skeleton. W4: extension and report completion. This statement is reconciled with the git log in the final report.

**AI usage statement.** AI assistance was used to implement and check code and
draft documentation. Measurements come from executed scripts and retained logs;
no generated text is presented as a measurement. Attribution for the local
non-blocking addition and final human review remain part of submission preparation.

## References

1. T. Tu, X. Liu, L. Song, Y. Zhang. *Understanding Real-World Concurrency Bugs in Go.* ASPLOS 2019. DOI 10.1145/3297858.3304069.
2. Dataset: https://github.com/system-pclub/go-concurrency-bugs
3. Course brief: CS340 Research Paper Replication, 2026–2027.
