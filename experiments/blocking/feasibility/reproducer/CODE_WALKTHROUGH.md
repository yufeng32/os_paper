# Code walk-through — how `main.go` maps onto the real bug

This document explains the reproducer line by line, so that a reader (or the TA) can see exactly
which piece of upstream code each block stands for, and why the buggy version leaks while the fixed
version does not. It is the companion of `main.go`; the real upstream excerpt is in
`../evidence/buggy_ListAndWatch.go.txt`.

## 1. What is original and what is reconstructed

| Upstream (`pkg/client/cache/reflector.go`, commit `6abb4723…`) | Reproducer (`main.go`) |
| --- | --- |
| `resyncCh, cleanup := r.resyncChan()` + `defer cleanup()` | `resyncCh, cleanup := resyncChan(20*time.Millisecond)` + `defer cleanup()` in `listAndWatch` |
| `(*Reflector).resyncChan()` — a channel that fires once per resync period, with a paired cleanup | `resyncChan(d)` — buffered-size-1 channel fed by a timer goroutine; `cleanup()` stops the timer and closes its `stop` channel |
| `resyncerrc := make(chan error, 1)` | same, kept because the real child goroutine also reports `Resync` errors through it |
| `stopCh <-chan struct{}` (the long-lived stop channel of the reflector) | package-level `neverClosed` channel, deliberately never closed |
| `r.store.Resync()` | `storeResyncSuccess()` returning `nil` (the bug does not depend on `Resync` failing) |
| `glog.V(4).Infof(...)` | omitted on purpose: no third-party dependency, no log noise |
| buggy `select { case <-resyncCh: case <-stopCh: return }` | identical in `-mode=buggy` |
| fix: `cancelCh := make(chan struct{}); defer close(cancelCh); case <-cancelCh: return` | identical in `-mode=fixed` |

Not reconstructed: the `List()` / `Watch()` round trips, the real object store, watch timeouts, and
anything timing related. Those describe *when* the enclosing function returns; the bug is about
what happens to the child goroutine *after* it returns, which is fully captured here.

## 2. The buggy path, step by step

1. `listAndWatch("buggy")` is called: `resyncChan` is created and `defer cleanup()` is registered.
2. The child goroutine starts and parks in:
   ```go
   select {
   case <-resyncCh:      // the resync timer fired
   case <-neverClosed:   // the reflector's stop channel — never fires in this scenario
   }
   ```
3. `listAndWatch` "returns" (the real function returns as soon as `Watch` errors out or the
   caller stops it). The deferred `cleanup()` runs: the resync timer is stopped and the feeder
   goroutine exits. **`resyncCh` will never receive again.**
4. `neverClosed` is never closed either. So the child goroutine has no remaining exit path and stays
   in `select` forever → one leaked, permanently blocked goroutine per `ListAndWatch` call.

That is the whole bug: the child has **two** exits (resync fires, or process-wide stop), and both
are unavailable precisely in the situation where the parent leaves. The upstream fix adds a third
exit whose only job is "the parent returned".

## 3. The fixed path

```go
cancelCh = make(chan struct{})   // created inside listAndWatch
defer close(cancelCh)            // closed when listAndWatch returns, always
select {
case <-resyncCh:
case <-neverClosed:
case <-cancelCh:                 // new third case
    return
}
```

When `listAndWatch` returns, `close(cancelCh)` makes that case ready immediately, so the child
goroutine observes it and returns. Nothing else changes — the resync behaviour for the *normal*
case (where the parent is still alive) is untouched.

## 4. How the numbers in the logs are produced

| Printed field | Produced by | Meaning |
| --- | --- | --- |
| `goroutines at start` | `runtime.NumGoroutine()` before the first call | baseline |
| `after ListAndWatch call #k` | `runtime.NumGoroutine()` after call *k* + 30 ms sleep | shows +1 per call in buggy mode |
| `goroutines at end` / `growth` | `runtime.NumGoroutine()` after a final 120 ms sleep, minus baseline | the leak count |
| `parked in chan receive/select` | counts `runtime.Stack(buf, true)` sections containing `chan receive` / `select` | sanity check that the extra goroutines are *blocked on channels*, not just alive |
| the stack dump | `runtime.Stack(buf, true)`, first 3 stacks | shows `main.listAndWatch.func1` at `main.go:83` inside `[select]` — the exact statement the upstream fix patched |

`-calls=5` therefore means "five `ListAndWatch` calls", and buggy mode is expected to report
`growth = 5`. Change it to `-calls=50` and the buggy variant reports 50, i.e. the leak is linear in
the number of re-listens — a useful fact for the later detector stage.

## 5. Why this is a valid feasibility result, and its limits

Valid because: the reconstructed control flow is byte-for-byte equivalent on the axis that matters
(which exit paths the child has), the run is reproducible (3/3 identical outcomes), and the control
variant proves the harness can also *not* leak — so a green "fixed" result is not a broken test.

Limits (state them in the report as limits, not as findings):
- it is a reconstruction, not the upstream package; it does not prove that upstream Kubernetes leaks
  at a specific rate;
- it cannot exercise the real `List`/`Watch` path, so it says nothing about how often
  `ListAndWatch` returns early in a real cluster;
- it does not model the process-wide stop path being closed, which is the other way the real child
  goroutine can exit.
