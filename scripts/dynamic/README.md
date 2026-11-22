# scripts/dynamic — reduced-scale Table 8 reproducers

One Go binary (`main.go`) holds eight pattern-level reproducers selected by `-case`, plus a
Python harness (`run_all.py`) that builds it and runs every case in two modes three times.

## Build & run

```sh
.venv/Scripts/python.exe scripts/dynamic/run_all.py
```

Requires Go on PATH (`D:\tools\go\bin`). The harness sets `GOROOT`/`GOPATH`/`GOPROXY`
itself. Outputs `results/runtime/raw_results.csv`, `results/runtime/summary.csv`, and one
`<case>_<mode>_<n>.log` per run.

## Modes

- `-mode A` natural behaviour (a leak exits; a true deadlock hangs).
- `-mode B` `main` blocks on `select{}`, forcing every goroutine asleep.

## Cases (all from the workbook's `Reproduced? = 1` blocking set)

| case | project | bug | fix commit | cause | pattern |
| --- | --- | --- | --- | --- | --- |
| docker_17176 | Docker | moby#17176 | 2f16895… | Mutex | `Lock()` early-return missing `Unlock` → next `Lock` blocks |
| etcd_5509 | etcd | etcd#5509 | 1d88130… | Mutex | ABBA lock order → circular deadlock |
| etcd_4474 | etcd | etcd#4474 | 0cb304e… | Chan | unconditional send on unbuffered `commitC`, no receiver |
| grpc_1850 | gRPC | #1850 | 484b3eb… | Chan | flow-control token not returned on error → next acquire blocks |
| grpc_1293 | gRPC | #1293 | 7df48be… | Chan | stream deleted without error → in-flight `RecvMsg` blocks |
| moby_27782 | Docker | moby#27782 | a69a59f… | Chan w/ | consumer waits a later event while producer blocks sending an earlier one |
| grpc_1459 | gRPC | #1459 | c29d638… | Chan w/ | keepalive holds the mutex while waiting on a channel |
| moby_256 | Docker | moby#256 | 58befe3… | Lib | sequential stdout read while the stderr pipe fills → pipe deadlock |

**Excluded:** b01 (`kubernetes#35672`) is a different case and not in the `Reproduced?` set,
so it does not overlap the previous member's work; BoltDB#392 and #240 have no patch in the
pinned dataset and cannot be reconstructed (they are the paper's only two detected cases —
see `comparison.md`).

## Deviation

Pattern-level reconstruction, not the original 2016-era applications (pre-modules,
Godeps/vendor, unbuildable with Go 1.20). Each reproducer keeps only the buggy control flow
identified from the fix-commit patch; the real app's surrounding logic and timing are
omitted. The effect on the Table 8 comparison is discussed in `results/runtime/comparison.md`.
