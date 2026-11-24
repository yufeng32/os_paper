# Non-blocking pattern reconstructions

This experiment extends the existing blocking-bug **pattern-level reconstruction**
method. It does not build the historical Docker/Kubernetes/etcd/etc. trees. See
[CASES.md](CASES.md) for each patch, trigger, fix and deliberately omitted behavior.

## Cohort and claims

The pinned workbook contains 86 non-blocking records. Its `Reproduced? = 1` flag
selects **23 distinct commit records**: 13 traditional, 4 anonymous-function,
2 shared-library, and 4 channel cases. The paper's Table 12 instead reports
13/4/2/**1** = 20. That exact 20-case identity has not been recovered. Repeated
issue IDs (notably etcd#4876) remain distinct commits, and no case is removed to
make the total equal 20. The full cohort remains visible even if a candidate
cannot be observed on the baseline toolchain.

Table 12's paper baseline is 10 detected out of 20 within 100 runs per case.
Our result measures these reconstructions and their workloads, not the original
applications or the original detector version. Historical library internals,
timing, dependencies and workloads differ; no result is tuned to match 10/20.

## Environment and commands

Run from the repository root with the existing Python virtual environment.
Baseline: **Go 1.20.14 windows/amd64**, CGO and a working 64-bit C compiler on
PATH (recorded machine: `D:/mingw64/bin/gcc.exe`). Python's audit dependencies
are the existing requirements. The portable toolchain is local to the ignored
cache; system PATH/registry and the existing blocking harness are not changed.
If `data/upstream` is absent in a fresh checkout, first run the repository's
existing `run.py` to fetch and verify the pinned dataset.

```powershell
# Audit Tables 9--11 and select the pinned 23 candidate records.
.venv/Scripts/python.exe scripts/analyze_nonblocking.py

# Official portable archive; SHA-256 checked before extraction or execution.
.venv/Scripts/python.exe scripts/dynamic/nonblocking/prepare_toolchain.py

# Full natural matrix: 23 x 2 variants x 2 builds x 100 runs x 3 batches.
.venv/Scripts/python.exe scripts/dynamic/nonblocking/run.py

# Separate controlled diagnostic: 3 runs per combination, one batch.
.venv/Scripts/python.exe scripts/dynamic/nonblocking/run.py --schedule controlled --runs 3 --batches 1

# Verify every archived log, hash, matrix cell, classification and case summary.
.venv/Scripts/python.exe scripts/dynamic/nonblocking/verify.py
.venv/Scripts/python.exe scripts/dynamic/nonblocking/verify.py --output results/nonblocking/diagnostic

.venv/Scripts/python.exe -m unittest discover -s tests -v
```

Use `--go <path>` or `GO_EXE` to select an existing baseline executable. Use
`--case <id>` (repeatable) for a subset. `--output <new-directory>` preserves
earlier evidence: nonempty output directories are rejected. A preflight-only
run is available with `--preflight-only --output .cache/nonblocking-preflight`.
Build failures stop the experiment rather than becoming detector misses.

## Program interface

The Go binary accepts `-case <id> -variant buggy|fixed
-schedule natural|controlled -seed <integer>`. It emits one `RESULT` JSON line
after joining the experiment's workers, except for unrecoverable target map
or slice-copy faults. The latter count only when the faulting stack identifies
the unprotected checkpoint copy and runtime.memmove. Target panics are recovered and logged with a stack; unknown panics
are infrastructure errors. Each process has a 10-second default watchdog.
Timeouts kill the process tree on Windows and are never evidence of this
non-blocking bug being reproduced.

Natural workloads share only a launch gate before conflicting accesses and a
join afterwards; yields exercise interleavings without forcing an ordering.
Controlled mode additionally delays closure workers until loop exit, waits for
return-channel cleanup before publication, or holds an active transaction briefly.
Those diagnostics can introduce happens-before edges and are never mixed into
natural race-detector rates. Seeds reproduce workload choices, not OS scheduling.
The dependency-free `go.mod` and pinned Go 1.20 compiler retain old loop-variable
semantics. No claim is made that Go 1.22+ with different language settings is equivalent.

`GOMAXPROCS=2` is fixed. `GORACE=exitcode=66 halt_on_error=0 atexit_sleep_ms=0`
retains reports and exit code while removing the default one-second exit delay.
Experiment workers join before main returns; no early exit is used to hide a report.
The driver first checks known racing and mutex-protected positive/negative
programs, ensuring the installed compiler actually supports `-race`.

## Interpretation and evidence

- **behavior_reproduced:** a target wrong result, panic or ordering violation
  was observed and the fixed control stayed clean.
- **race_reproduced_only:** the target conflicting accesses were reported;
  no separate wrong-output symptom was observed.
- **not_observed:** neither was observed. It is not an established detector miss.
- **control_failed / incomplete:** a fixed control failed or the requested
  executions were not valid; excluded from the eligible detector denominator.

The version-sensitive timer candidate retains the actual `AfterFunc/Reset`
pattern and replaces real I/O with short work. It does not add an unsafe shared
variable merely to obtain a race report. A clean run does not establish either
successful historical reproduction or a detector miss. The context case explicitly
reconstructs Go 1.7 valueCtx.String formatting with a mutable struct in place of
trace: Go 1.20's context no longer traverses a non-Stringer value. This is a
historical library-behavior reconstruction, not a claim about the current stdlib.
The Bolt merge candidate models the pending writable transaction path only.

The checkpoint candidate models slice publication as immutable backing data and
a scalar published length: the buggy copy reads that length outside mu, while
the fixed copy reads it inside mu. This retains the missing-lock mechanism but
does not reproduce multiword slice-header tearing. A preliminary composite-header
attempt corrupted RESULT metadata; the rejected log, source snapshots and entire
interrupted attempt are retained in `results/nonblocking/preliminary/`, excluded
from the final matrix. No invalid record was silently accepted or replaced.

Outputs are in `results/nonblocking/runtime/` and `diagnostic/`: environment and
build records, manifest, per-run CSV, summaries, batch results and comparison.
Every execution retains exact argv, stdout/stderr, elapsed time, timeout and exit
status in a JSON log. Eight independent repetitions of the same case/build/variant
run concurrently by default (`--jobs 8`, each with GOMAXPROCS=2); variants and
cases do not overlap. This throughput choice is recorded in run.json and can
affect interleavings; use `--jobs 1` for a serial experiment in a new directory.
All JSON logs are retained in **logs.zip**; individual
copies are ignored by Git. CSV paths address members of that archive. SHA-256
hashes cover each log, archive, binary and experiment source. The verifier reads
the archive directly; no extraction is needed.

Each batch uses the paper's rule: at least one target warning in the 100-run
budget counts as detected. Reports must point to both target access stacks,
not just name a goroutine-creation function. Fixed controls run with both builds
and must have no warning or target symptom. Three batch rates are shown separately,
with mean and sample SD. Candidate coverage and observations accompany detection
rates so failures and untriggered candidates cannot be hidden.

Sources: [paper](https://songlh.github.io/paper/go-study.pdf),
[Go race detector](https://go.dev/doc/articles/race_detector),
[loop-variable change](https://go.dev/blog/loopvar-preview), and the pinned
dataset patch identities in CASES.md. Additional inspected upstream files and
the recovered Bolt merge are indexed in `results/nonblocking/additional_sources.json`.
