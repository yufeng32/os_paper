# Reproducing *Understanding Real-World Concurrency Bugs in Go* at Reduced Scale

**CS340 Operating Systems — Research Paper Replication**
Group: 1240029057 陈钰丰 (yufeng32), 1240026499 沈漠 (woshimoshen), 1240026895 章钧钧 (siriuszhang06-wq), + one member.
**Status:** Week 3 draft. Sections 1–4 and 6 contain measured results; the Extension (Section 5) and final claim verdicts are completed in Week 4.

## Abstract

We reproduce the empirical core of Tu et al., *Understanding Real-World Concurrency Bugs in Go* (ASPLOS 2019) at reduced scale. From the authors' pinned workbook we recover the taxonomy (Table 5), the blocking-bug root causes (Table 6) and fix strategies (Table 7) cell-for-cell, and we run a reduced Table 8 experiment: eight of the 21 reproduced blocking bugs, reconstructed as standalone programs, evaluated with Go's built-in deadlock detector in two modes. The classification and root-cause tables reproduce exactly. The detector evaluation partially supports the paper: 3 of 8 cases are detected naturally and 7 of 8 when every goroutine is forced asleep, versus the paper's 2 of 21. The gap is explained by the detector's all-asleep precondition and by the two detected cases (BoltDB#392/#240) lacking a patch in the pinned dataset. Every number traces to a script and a log in the repository.

## 1. Introduction and Claims

### 1.1 Paper and problem

Go encourages message passing (channels) over shared memory, on the belief that explicit message passing is less error-prone. The paper performs the first systematic, empirical study of real Go concurrency bugs across six production applications (Docker, Kubernetes, etcd, CockroachDB, gRPC, BoltDB), classifying 171 bugs along two orthogonal axes — **behaviour** (blocking / non-blocking) and **cause** (shared memory / message passing) — and evaluating two built-in detectors. Its headline finding is that message passing is no safer than shared memory: about 58% of blocking bugs are caused by message passing.

### 1.2 Claims tested

- **C1 (Tables 5, 6, 7).** The published behaviour counts and the blocking root-cause/fix cross-tabs are recoverable from the pinned workbook.
- **C2 (Table 8).** The built-in Go deadlock detector finds only a subset of the blocking bugs.

### 1.3 Scope

Reduced scale, stated up front. We reproduce Tables 5–7 in full from the workbook, and Table 8 on 8 of the 21 reproduced blocking bugs. We do **not** reproduce the non-blocking side (Tables 9–12), the full detector comparison, or the historical applications themselves (see 2.4).

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
| Python | 3.12.3 (pin 3.12.13), openpyxl 3.1.5, et-xmlfile 2.0.0 |
| Go (runtime) | go1.20.14 windows/amd64 |
| C compiler | MinGW gcc 8.1.0 (`-race` available; not used in Table 8) |
| Container | `python:3.12.13-slim-bookworm` pins the Python audits |

### 2.3 Workloads and inputs

- Static audits: the pinned workbook, verified byte-for-byte by SHA-256.
- Runtime (Table 8): 8 of the 21 blocking bugs marked `Reproduced? = 1`, chosen to span Mutex (2), Chan (3), Chan w/ (2) and Messaging Lib (1). Each case is a standalone Go program that keeps only the buggy control flow extracted from the fix-commit patch.

### 2.4 Deviations

| Item | Paper | Ours | Reason |
| --- | --- | --- | --- |
| Method | Built and ran the historical applications | Pattern-level reconstruction | 2016-era trees are pre-modules and unbuildable with Go 1.20 |
| Runtime sample | 21 blocking bugs | 8 (2 Mutex, 3 Chan, 2 Chan w/, 1 Lib) | Reduced scale; BoltDB#392/#240 lack patches |
| Repetitions | One run (blocking is deterministic) | 3 runs per case | Course requirement; confirms determinism |
| Detector modes | Natural | A natural; B forced all-asleep | B isolates the all-asleep precondition |
| Environment | Paper's machines | Windows 11, Go 1.20.14 | Recorded on the actual machine |

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

### 3.5 Traceability

| Result | Script | Output | Command |
| --- | --- | --- | --- |
| Table 5 | `run.py`, `scripts/analyze.py` | `results/table5/` | `.venv/Scripts/python.exe run.py` |
| Tables 6–7 | `scripts/analyze_table6_7.py` | `results/table6/`, `results/table7/` | `.venv/Scripts/python.exe scripts/analyze_table6_7.py` |
| Table 8 | `scripts/dynamic/run_all.py` | `results/runtime/` | `.venv/Scripts/python.exe scripts/dynamic/run_all.py` |

## 4. Analysis of Discrepancies

### 4.1 Claim verdicts

- **C1: supported.** Tables 5 (behaviour), 6 and 7 recover exactly; the single Table 5 root-cause discrepancy is a documented dual-flag record, not an error.
- **C2: partially supported.** The qualitative claim (the detector misses most blocking bugs) holds; the exact 2/21 rate does not transfer at this scale.

### 4.2 Gaps and their explanation

- **A vs B (3/8 vs 7/8).** The four background-leak cases (docker_17176, etcd_4474, grpc_1850, grpc_1293) are missed naturally because the leaked goroutine coexists with a running/exiting process, so "all goroutines asleep" never holds; forcing all-asleep detects them. This isolates the detector's precondition.
- **moby#256 (Lib) never detected.** Its deadlock is on OS pipe I/O, not a Go primitive; the detector only inspects goroutines blocked on Go primitives.
- **Ours 37.5% > paper 9.5%.** (1) The eight reconstructable cases are biased toward true circular deadlocks; (2) the paper's two detected cases are BoltDB#392/#240, which have no patch in the pinned dataset; (3) our true-deadlock cases have `main` waiting, as a hung program would.

### 4.3 Evidence

Every claim above is backed by a logged run: `results/runtime/raw_results.csv`, `results/runtime/summary.csv`, and one `<case>_<mode>_<n>.log` per run (containing either the detector's `fatal error: all goroutines are asleep` and a goroutine dump, a clean exit, or a timeout with no detector output).

### 4.4 Limitations

- Pattern-level reconstruction omits the applications' surrounding logic and timing; it shows that a bug **can** block, not how often it does in production.
- 8 of 21 cases; two of the paper's detected cases are unreconstructable here.
- The non-blocking side (Tables 9–12) is not reproduced.

## 5. Extension (Week 4 — pending)

One controlled experiment beyond the paper, changing a single factor. Candidate: re-run the same blocking cases on a different Go toolchain version (or a second, independent detector) on the same machine and workload, and interpret the effect on the detection rate. To be completed in Week 4 with results in `results/extension/`.

## 6. Conclusion

The paper's classification and root-cause results reproduce exactly from the pinned workbook. Its detector finding is directionally reproduced: the built-in deadlock detector misses most blocking bugs, and its misses are explained by the all-asleep precondition and by non-Go-primitive (I/O) blocking, not by the detector misunderstanding the primitives. The exact 2/21 rate is scale- and selection-dependent. **Overall verdict: partially reproduced.**

### Lessons learned

1. Reproducing a data-classification paper from its own dataset recovers its arithmetic but not the independent correctness of every label.
2. Reproducing a detector evaluation requires reconstructing the blocking condition, and Go's detector only speaks when every goroutine is asleep — a precondition easy to overlook and easy to accidentally satisfy with a spurious `main` block.
3. Missing patches (two BoltDB cases) can remove exactly the cases that matter, and must be reported as a deviation rather than hidden.

## Contribution and AI usage

**Contribution statement.** W1 (1240029057 陈钰丰): Table 5 audit and reading notes. W2 (1240026895 章钧钧): pinned environment and scope declaration. W3 (1240026499 沈默): b01 (Kubernetes #35672) ListAndWatch resync goroutine-leak runtime case, supplementary to the 21-bug Table 8 set. W3 (1240029367 邵杰): Tables 6–7 audit, Table 8 reduced runtime subset, report skeleton. W4: extension and report completion. This statement is reconciled with the git log in the final report.

**AI usage statement.** AI assistance was used to draft and check code and documentation; all material was reviewed and is owned by the team. No generated text is presented as a runtime measurement.

## References

1. T. Tu, X. Liu, L. Song, Y. Zhang. *Understanding Real-World Concurrency Bugs in Go.* ASPLOS 2019. DOI 10.1145/3297858.3304069.
2. Dataset: https://github.com/system-pclub/go-concurrency-bugs
3. Course brief: CS340 Research Paper Replication, 2026–2027.
