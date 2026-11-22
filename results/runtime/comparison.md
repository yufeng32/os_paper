# Table 8: Blocking-Bug Deadlock Detector — Paper vs. Ours

Source: Tu et al., ASPLOS 2019, Table 8, PDF p. 8. Detector: Go 1.20.14 built-in deadlock
detector. Reproduced at reduced scale: 8 of the 21 reproduced blocking bugs (the workbook's
`Reproduced? = 1` set). Case code: `scripts/dynamic/`; raw logs: `results/runtime/*.log`;
machine-readable: `raw_results.csv`, `summary.csv`.

Each case runs in two modes:
- **A (natural):** the program behaves as the original does. A background-goroutine leak
  exits cleanly; a true circular deadlock hangs.
- **B (forced):** after the bug, `main` blocks on `select{}`, so every goroutine is asleep —
  the precondition the detector requires.

## Paper vs. Ours (mode A, natural)

| Root cause | Paper used | Paper detected | Ours used | Ours detected (A) |
| --- | ---: | ---: | ---: | ---: |
| Mutex | 7 | 1 | 2 | 1 |
| Chan | 8 | 0 | 3 | 0 |
| Chan w/ | 4 | 1 | 2 | 2 |
| Messaging Lib | 2 | 0 | 1 | 0 |
| **Total** | **21** | **2 (9.5%)** | **8** | **3 (37.5%)** |

## Forced all-asleep (mode B, diagnostic control)

| Root cause | Ours used | Ours detected (B) |
| --- | ---: | ---: |
| Mutex | 2 | 2 |
| Chan | 3 | 3 |
| Chan w/ | 2 | 2 |
| Messaging Lib | 1 | 0 |
| **Total** | **8** | **7 (87.5%)** |

## Per-case verdicts (A / B)

| case | cause | A | B |
| --- | --- | --- | --- |
| docker_17176 | Mutex | not detected (clean exit) | detected |
| etcd_5509 | Mutex | **detected (ABBA)** | detected |
| etcd_4474 | Chan | not detected (clean exit) | detected |
| grpc_1850 | Chan | not detected (clean exit) | detected |
| grpc_1293 | Chan | not detected (clean exit) | detected |
| moby_27782 | Chan w/ | **detected (circular)** | detected |
| grpc_1459 | Chan w/ | **detected (mutex+chan)** | detected |
| moby_256 | Lib | not detected (hung) | not detected (hung) |

## Interpretation

- Detection is binary and deterministic: for every (case, mode) the three runs agree
  (std = 0), so we report "detected x/3" rather than a mean.
- The gap between A (3/8) and B (7/8) is the detector's precondition, not a change in the
  bugs. Four of the eight (docker_17176, etcd_4474, grpc_1850, grpc_1293) are
  background-goroutine leaks: in the real program the goroutine leaks while the process
  keeps running or exits, so "all goroutines asleep" never holds and the detector misses
  them. Force every goroutine asleep and the same bugs are reported.
- moby_256 (Lib) is never detected, even in B: its deadlock is on OS pipe I/O, not a Go
  primitive, and the detector only inspects goroutines blocked on Go primitives (channel,
  mutex, select). This reproduces the paper's finding that messaging-library bugs elude it.
- Our A rate (37.5%) exceeds the paper's (9.5%) for three documented reasons: (1) the eight
  reconstructable cases are biased toward true circular deadlocks; (2) the two cases the
  paper's detector did catch, BoltDB#392 and BoltDB#240, have no patch in the pinned
  dataset and could not be reconstructed; (3) the A mode of the true-deadlock cases has
  `main` waiting, as a real hung program would, whereas some server bugs leave other
  goroutines runnable and so never reach the all-asleep state.

## Verdict

**Partially supported.** The paper's qualitative claim — the built-in detector finds only a
minority of blocking bugs, and fails for non-Go-primitive (pipe I/O) and background-leak
cases — is reproduced. The exact 2/21 rate is not reproduced at this reduced scale, for the
reasons stated above. This is a scale and selection effect, not a contradiction of the
paper's claim.
