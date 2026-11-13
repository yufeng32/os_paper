# Reproducer — pattern-level reconstruction

`main.go` re-implements only the control flow of the buggy / fixed resync goroutine from
`kubernetes/kubernetes` `pkg/client/cache/reflector.go` (commit `6abb4723…`, fixed by
`991674380…`), using standard-library code only. It is **not** the original source; the original
buggy excerpt is kept in `../evidence/buggy_ListAndWatch.go.txt`.

## Files

| File | Purpose |
| --- | --- |
| `main.go` | single program, `-mode=buggy` or `-mode=fixed` selects which version runs |
| `go.mod` | module `blockingfeasibility`, `go 1.20`, no dependencies |
| `run.ps1` | builds once, then runs each mode 3 times, writing `../logs/run_<mode>_<n>.txt` |
| `CODE_WALKTHROUGH.md` | line-by-line mapping between this code and the upstream buggy/fixed code, and how each printed number is produced |

## Commands

```bash
go build -o repro.exe .
./repro.exe -mode=buggy -calls=5     # expect: goroutine growth = calls, all parked in [select]
./repro.exe -mode=fixed -calls=5     # expect: growth = 0
```

## Why a reconstruction instead of the real package

The buggy commit is a pre-modules Kubernetes tree (`Godeps` + `vendor`, Go 1.6/1.7 era, no
`go.mod`); it cannot be built as-is with a modern toolchain without days of porting work, and the
fix commit adds no test. The reconstruction isolates the exact control flow that was wrong
(two exit paths instead of three) and makes the blocking observable with `runtime.NumGoroutine()`
plus a `runtime.Stack` dump, so the claim "this is a blocking bug" is backed by a run rather than
by reading.

What the reconstruction deliberately keeps faithful:

- the resync channel is produced by a `resyncChan()`-style helper with a paired `cleanup()`;
- `cleanup()` is called through `defer` when the enclosing function returns, exactly as upstream;
- the long-lived `stopCh` is never closed, exactly as upstream (it belongs to the informing
  machinery, not to one `ListAndWatch` call);
- the fixed path is byte-for-byte the fix: `cancelCh := make(chan struct{})`,
  `defer close(cancelCh)`, `case <-cancelCh: return`.

What it does not reproduce: the real `r.store.Resync()` work, the real watch/list round trips, and
therefore any timing or event-volume aspect of the bug. Those matter for a detector experiment, not
for a "does it block at all" experiment.
