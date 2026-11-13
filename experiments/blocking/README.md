# Blocking Bug Experiment — Case b01 (Kubernetes ListAndWatch resync leak)

## Important Reproduction Limitation

The experiment uses a standalone reconstruction of the original Kubernetes bug pattern.

The historical Kubernetes source code was inspected (the buggy file at the parent commit and the
fix commit diff were both retrieved from upstream and compared), but the complete historical
Kubernetes project was **not successfully built or executed** — that revision is a pre-modules tree
(`Godeps` + `vendor`, Go 1.6/1.7 era) and cannot be built as-is with a modern Go toolchain.

Therefore the results demonstrate that **the reconstructed bug pattern can reproduce goroutine
blocking behaviour**. They do **not** establish that the original Kubernetes application was
executed successfully, and they say nothing about how often that function returns early in a real
cluster. Read every number in `feasibility/` with this scope in mind; the same limitation is stated
in `feasibility/case_info.md`, `feasibility/build_log.txt` (STEP 10) and
`feasibility/reproducer/README.md`.

This directory holds the week's deliverable: a **feasibility investigation** of one real Go blocking
bug taken from the paper *Understanding Real-World Concurrency Bugs in Go* (ASPLOS'19) and its
dataset `system-pclub/go-concurrency-bugs`.

Scope of this stage: establish whether the bug is reproducible at all — identify the bug, pin the
two commits, retrieve the real historical code, check whether that historical tree can be built,
and, since it cannot, build and run a faithful pattern-level reconstruction that shows the
goroutine really does block. Running the Go deadlock detector / `-race` on this case is the **next**
stage, not this one.

## Case in one paragraph

`kubernetes/kubernetes`, `pkg/client/cache/reflector.go`. `ListAndWatch` starts a child goroutine
that can only leave its `select` loop through `stopCh` or through a `Resync()` error. When
`ListAndWatch` returns normally, `defer cleanup()` stops the resync timer and `stopCh` stays open,
so the child never gets a signal again: it blocks in `select` forever. That is a message-passing
blocking bug of the same family as the paper's Figure 1 (parent leaves, child has no exit path).

- buggy commit: `6abb4723571fc6b9e4dc05807511569dfc865f83`
- fix commit: `991674380b7773d73afaeafeac6242bf3b6e6001` — "Fix resync goroutine leak in
  ListAndWatch"; adds `cancelCh` closed by `defer close(cancelCh)` and a third `select` case.

## Layout

```
experiments/blocking/
├── README.md                      <- this file: how to obtain code, build, run, judge
└── feasibility/
    ├── case_info.md               <- bug identity, buggy code, fix diff, why this case
    ├── environment.md             <- machine + toolchain + requirements of the 2016 code
    ├── build_log.txt              <- every command actually executed and its real output
    ├── feasibility_results.csv    <- 6 runs (3 buggy + 3 fixed), growth / blocked / verdict
    ├── CSV_NOTES.md               <- what each csv column means, incl. not_attempted vs failed
    ├── evidence/
    │   ├── buggy_ListAndWatch.go.txt   <- real buggy excerpt from upstream
    │   ├── fix_commit_991674380.txt    <- full fix commit (git show) from the dataset
    │   └── README.md                   <- where each piece came from
    ├── reproducer/
    │   ├── main.go                <- standalone reconstruction (buggy and fixed paths)
    │   ├── go.mod
    │   ├── run.ps1                <- build + 3 repetitions per variant, writes into logs/
    │   ├── CODE_WALKTHROUGH.md    <- line-by-line map of the code onto the upstream bug
    │   └── README.md
    └── logs/
        ├── run_buggy_1..3.txt     <- one file per repetition
        ├── run_fixed_1..3.txt
        └── run_all_console.txt    <- console capture of the whole run.ps1 session
```

## 1. How to obtain the historical code

Two things are needed: the **fix commit diff** (to know what the bug was) and the **buggy file**
(to read the actual code). Do not read today's `master`: that file has been rewritten many times
since 2016.

Option A — the paper's dataset (fastest, no clone needed):

```bash
curl -L -o gcb_dataset.zip https://codeload.github.com/system-pclub/go-concurrency-bugs/zip/refs/heads/master
unzip gcb_dataset.zip
cat go-concurrency-bugs-master/blocking-bugs/kubernetes/991674380b7773d73afaeafeac6242bf3b6e6001.txt
```

The file name **is** the fix commit; the content is that commit's `git show` output.

Option B — GitHub REST API (what was used here, because `git clone` was reset by the network):

```bash
# 1) fix commit -> its parent is the buggy commit
curl -H "User-Agent: curl" https://api.github.com/repos/kubernetes/kubernetes/commits/991674380b7773d73afaeafeac6242bf3b6e6001
# parent sha returned: 6abb4723571fc6b9e4dc05807511569dfc865f83

# 2) the buggy file at that commit
curl -H "User-Agent: curl" \
  "https://api.github.com/repos/kubernetes/kubernetes/contents/pkg/client/cache/reflector.go?ref=6abb4723571fc6b9e4dc05807511569dfc865f83"
# the reply is base64; decode .content to get the real file
```

Option C — full repository, if you have the bandwidth:

```bash
git clone https://github.com/kubernetes/kubernetes.git
cd kubernetes
git checkout 6abb4723571fc6b9e4dc05807511569dfc865f83
```

## 2. How to switch to the correct version

Always check out the **buggy** commit, never `master`:

```bash
git checkout 6abb4723571fc6b9e4dc05807511569dfc865f83
git show 991674380b7773d73afaeafeac6242bf3b6e6001 -- pkg/client/cache/reflector.go   # the fix
```

If you only have the dataset zip, you do not need a checkout: `evidence/buggy_ListAndWatch.go.txt`
already contains the exact buggy excerpt, and `evidence/fix_commit_991674380.txt` contains the fix.

## 3. How to configure the environment

| Item | Value used |
| --- | --- |
| Go — version actually tested | `go1.20.14 windows/amd64` (portable zip) |
| Go — version declared by `go.mod` | `go 1.20` (declared minimum only) |
| Go — other versions | not verified — nothing was run outside 1.20.14, and no claim is made about them |
| OS | Windows 11 (the reproducer is OS-independent; Linux/macOS work the same) |
| Shell | PowerShell 7 (the script), or run `go run . -mode=buggy` manually |

Nothing else is required: the reproducer uses only the Go standard library (`flag`, `fmt`,
`runtime`, `strings`, `time`), no third-party module, no network access at run time.

**Do not** try to `go build ./...` the 2016 Kubernetes tree: that commit has no `go.mod`
(HTTP 404), it is vendored through `Godeps/Godeps.json`, and it expects the Go 1.6/1.7 GOPATH
workflow. This is recorded as a deviation in `environment.md` and `build_log.txt` STEP 5.

## 4. How to run

```bash
cd experiments/blocking/feasibility/reproducer
go version
go build -o repro.exe .          # or: go build -o repro .
./repro.exe -mode=buggy -calls=5
./repro.exe -mode=fixed -calls=5
```

or everything at once (3 repetitions of each variant, logs written to `../logs/`):

```powershell
powershell -ExecutionPolicy Bypass -File experiments/blocking/feasibility/reproducer/run.ps1
```

What the two modes do:

| mode | behaviour |
| --- | --- |
| `buggy` | the child goroutine has only `resyncCh` / never-closed `stopCh` as exit paths — the version before the fix |
| `fixed` | the fix is applied: `cancelCh` is created and `defer close(cancelCh)` runs when `ListAndWatch` returns, so the child also selects on `cancelCh` and exits |

`-calls=5` means "simulate five `ListAndWatch` calls", i.e. five times the reflector re-lists and
returns. Each call leaks one goroutine in buggy mode.

## 5. How to judge success

A run counts as **blocking reproduced** when all three hold:

1. `runtime.NumGoroutine()` at the end is larger than the count at start, by one per
   `ListAndWatch` call (5 calls → growth 5);
2. at least that many goroutines are parked in `chan receive` / `select` according to the
   `runtime.Stack(all=true)` dump;
3. the dumped stacks point at the `select` statement that the fix patched
   (`main.listAndWatch.func1`, `main.go:83`), i.e. the goroutine is stuck on the channel wait and
   not on something else.

The `fixed` mode is the control: if it also grows, the reproducer is wrong (not the bug), and the
run must be discarded — that is precisely why the control variant is run 3 times too.

Result actually obtained (2026-11-13, 3 runs each):

| variant | goroutine growth per 5 calls (3 runs) | mean ± SD | blocked goroutines | verdict |
| --- | --- | --- | --- | --- |
| buggy | 5, 5, 5 | 5.00 ± 0.00 | 5 | blocking reproduced |
| fixed | 0, 0, 0 | 0.00 ± 0.00 | 0 | no blocking (control holds) |

## 6. What this stage did not answer

- The whole historical Kubernetes tree was never compiled (see above); "can the original binary be
  built" remains open and is documented as a limitation, not as a success.
- The fix commit ships **no regression test**, so there is no upstream "original test input" to run;
  the reproducer is a reconstruction and is labelled as such everywhere.
- The Go built-in deadlock detector and `-race` were not applied to this case yet. Expected
  (hypothesis, to be verified next stage): neither will report it — the deadlock detector needs
  *all* goroutines asleep and here the main goroutine keeps running; `-race` looks for data races
  and there is no shared memory here. This lines up with the paper's Table 8 / Table 12 numbers.
