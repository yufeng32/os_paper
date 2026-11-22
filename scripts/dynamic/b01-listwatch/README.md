# Dynamic reproducer — case b01 (Kubernetes ListAndWatch resync leak)

## Reproduction limitation

This program is a **standalone reconstruction** of the original Kubernetes bug
pattern. The historical Kubernetes source was inspected (the buggy file at the
parent commit and the fix commit diff were both retrieved from upstream and
compared), but the complete historical Kubernetes project was **not built or
executed** — that revision is a pre-modules tree (`Godeps` + `vendor`, Go
1.6/1.7 era) and cannot be built as-is with a modern Go toolchain.

The results therefore demonstrate that **the reconstructed bug pattern can
reproduce goroutine blocking behaviour**. They do **not** establish that the
original Kubernetes application was executed successfully, and they say nothing
about how often that function returns early in a real cluster. The same
limitation is stated in `results/runtime/b01/case_info.md` and
`results/runtime/b01/build_log.txt`.

## Files

| File | Purpose |
| --- | --- |
| `main.go` | single program, `-mode=buggy` or `-mode=fixed` selects which version runs |
| `go.mod` | module `b01listwatch`, `go 1.20`, no dependencies |
| `run.ps1` | builds once, then runs each mode 3 times, writing `results/runtime/b01/logs/run_<mode>_<n>.txt` |
| `CODE_WALKTHROUGH.md` | line-by-line mapping between this code and the upstream buggy/fixed code, and how each printed number is produced |

The upstream excerpts this reconstruction is based on are kept in
`results/runtime/b01/evidence/`; the recorded runs and aggregate numbers are in
`results/runtime/b01/`.

## Commands

From the repository root:

```powershell
cd scripts/dynamic/b01-listwatch
go version
go build -o repro.exe .
.\repro.exe -mode=buggy -calls=5     # expect: goroutine growth = calls, all parked in [select]
.\repro.exe -mode=fixed -calls=5     # expect: growth = 0
```

Or run all six repetitions and write the per-run logs:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dynamic/b01-listwatch/run.ps1
```

## Why a reconstruction instead of the real package

The buggy commit is a pre-modules Kubernetes tree (`Godeps` + `vendor`, Go
1.6/1.7 era, no `go.mod`); it cannot be built as-is with a modern toolchain
without days of porting work, and the fix commit adds no regression test. The
reconstruction isolates the exact control flow that was wrong (two exit paths
instead of three) and makes the blocking observable with
`runtime.NumGoroutine()` plus a `runtime.Stack` dump, so the claim "this is a
blocking bug" is backed by a run rather than by reading.

What the reconstruction deliberately keeps faithful:

- the resync channel is produced by a `resyncChan()`-style helper with a paired
  `cleanup()`;
- `cleanup()` is called through `defer` when the enclosing function returns,
  exactly as upstream;
- the long-lived `stopCh` is never closed, exactly as upstream (it belongs to
  the informer machinery, not to one `ListAndWatch` call);
- the fixed path is byte-for-byte the fix: `cancelCh := make(chan struct{})`,
  `defer close(cancelCh)`, `case <-cancelCh: return`.

What it does not reproduce: the real `r.store.Resync()` work, the real
watch/list round trips, and therefore any timing or event-volume aspect of the
bug. Those matter for a detector experiment, not for a "does it block at all"
experiment.

## How a run is judged

A run counts as **blocking reproduced** when all three hold:

1. `runtime.NumGoroutine()` at the end is larger than the count at start, by
   one per `ListAndWatch` call (5 calls → growth 5);
2. at least that many goroutines are parked in `chan receive` / `select`
   according to the `runtime.Stack(all=true)` dump;
3. the dumped stacks point at the `select` statement that the fix patched
   (`main.listAndWatch.func1`, `main.go:83`), i.e. the goroutine is stuck on
   the channel wait and not on something else.

The `fixed` mode is the control: if it also grows, the reproducer is wrong (not
the bug), and the run must be discarded — that is precisely why the control
variant is run 3 times too.
