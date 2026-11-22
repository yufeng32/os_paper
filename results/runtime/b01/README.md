# Runtime case b01 — Kubernetes ListAndWatch resync goroutine leak

## Reproduction limitation

This stage uses a standalone reconstruction of the original Kubernetes bug
pattern. The historical Kubernetes source code was inspected (the buggy file at
the parent commit and the fix commit diff were both retrieved from upstream and
compared), but the complete historical Kubernetes project was **not successfully
built or executed** — that revision is a pre-modules tree (`Godeps` + `vendor`,
Go 1.6/1.7 era) and cannot be built as-is with a modern Go toolchain.

The results demonstrate that **the reconstructed bug pattern can reproduce
goroutine blocking behaviour**. They do **not** establish that the original
Kubernetes application was executed successfully, and they say nothing about
how often that function returns early in a real cluster. Read every number in
this directory with this scope in mind; the same limitation is stated in
`case_info.md`, `build_log.txt` (STEP 10) and the harness `README.md`.

## Case in one paragraph

`kubernetes/kubernetes`, `pkg/client/cache/reflector.go`. `ListAndWatch` starts
a child goroutine that can only leave its `select` loop through `stopCh` or
through a `Resync()` error. When `ListAndWatch` returns normally, `defer
cleanup()` stops the resync timer and `stopCh` stays open, so the child never
gets a signal again: it blocks in `select` forever. That is a message-passing
blocking bug of the same family as the paper's Figure 1 (parent leaves, child
has no exit path).

- buggy commit: `6abb4723571fc6b9e4dc05807511569dfc865f83`
- fix commit: `991674380b7773d73afaeafeac6242bf3b6e6001` — "Fix resync goroutine
  leak in ListAndWatch"; adds `cancelCh` closed by `defer close(cancelCh)` and
  a third `select` case.

## Layout

```
results/runtime/b01/
├── README.md                 <- this file: case summary, recorded result, open questions
├── case_info.md              <- bug identity, commit relationship, buggy code, fix diff, detectors
├── environment.md            <- machine + toolchain + requirements of the 2016 code
├── build_log.txt             <- every command actually executed and its real output
├── runtime_results.csv       <- 6 runs (3 buggy + 3 fixed), growth / blocked / verdict
├── CSV_NOTES.md              <- what each csv column means, incl. not_attempted vs failed
├── evidence/
│   ├── buggy_ListAndWatch.go.txt   <- real buggy excerpt from upstream
│   ├── fix_commit_991674380.txt    <- full fix commit (git show) from the dataset
│   └── README.md                   <- where each piece came from
└── logs/
    ├── run_buggy_1..3.txt     <- one file per repetition
    ├── run_fixed_1..3.txt
    └── run_all_console.txt    <- console capture of the whole run.ps1 session
```

The runnable harness lives outside `results/`, at
`scripts/dynamic/b01-listwatch/` (`main.go`, `go.mod`, `run.ps1`,
`CODE_WALKTHROUGH.md`).

## Recorded result (2026-11-13, 3 runs each)

| variant | goroutine growth per 5 calls (3 runs) | mean ± SD | blocked goroutines | verdict |
| --- | --- | --- | --- | --- |
| buggy | 5, 5, 5 | 5.00 ± 0.00 | 5 | blocking reproduced |
| fixed | 0, 0, 0 | 0.00 ± 0.00 | 0 | no blocking (control holds) |

One row per run is in `runtime_results.csv`; the per-repetition raw outputs are
in `logs/`. The `fixed` variant is the control: if it also grew, the harness
would be broken rather than the bug being reproduced.

## What this stage did not answer

- The whole historical Kubernetes tree was never compiled (see `environment.md`);
  "can the original binary be built" remains open and is documented as a
  limitation, not as a success.
- The fix commit ships **no regression test**, so there is no upstream "original
  test input" to run; the reproducer is a reconstruction and is labelled as such
  everywhere.
- The Go built-in deadlock detector and `-race` were not applied to this case
  yet. Expected (hypothesis, to be verified in the detector stage): neither will
  report it — the deadlock detector needs *all* goroutines asleep and here the
  main goroutine keeps running; `-race` looks for data races and there is no
  shared memory here. The exact paper table and metric will be confirmed against
  the paper's tables before a Paper vs. Ours comparison is written.
