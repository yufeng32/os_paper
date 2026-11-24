# Validation — non-blocking addition, 2026-11-24

## Recorded checks

- Pinned dataset checkout is clean at f2655063a2278cff64a51121b73801eda05fdcfa; workbook SHA-256 matches the existing pin.
- Tables 9/10/11: 36/30/42 non-total cells checked, zero differing cells.
- Official Go 1.20.14 archive verified before extraction; environment includes positive and mutex-protected negative race-detector probes.
- Natural matrix: 27,600/27,600 executions; 23 complete cases, 23 clean fixed controls, zero infrastructure errors.
- Outcomes: 14 behavioral reproductions, 8 race-only reproductions, 1 unobserved historical timer candidate.
- Each 100-run batch: 18/23 candidates reported; mean 78.26%, sample SD 0.00 percentage points. Different cohort/workload from the paper's 20/10 result; not detector recall.
- Controlled diagnostic: 276/276 executions, 23 clean fixed controls, zero infrastructure errors; excluded from natural rates.
- Scalar checkpoint validation: 1,200/1,200 executions, clean fixed control and no infrastructure errors.
- Every natural, diagnostic and scalar-validation archive log passed hash, command, classification, matrix and case-summary verification.
- 25 unit tests pass (tests.txt), including rejection of corrupted case identity even when the target race is reported.
- Final source/driver hashes match the receipts for all three accepted experiments.
- Existing blocking scripts/results were not changed. No commit or push was performed.

## Commands

```powershell
.venv/Scripts/python.exe scripts/analyze_nonblocking.py
.venv/Scripts/python.exe scripts/dynamic/nonblocking/prepare_toolchain.py
.venv/Scripts/python.exe scripts/dynamic/nonblocking/run.py
.venv/Scripts/python.exe scripts/dynamic/nonblocking/run.py --schedule controlled --runs 3 --batches 1
.venv/Scripts/python.exe scripts/dynamic/nonblocking/verify.py
.venv/Scripts/python.exe scripts/dynamic/nonblocking/verify.py --output results/nonblocking/diagnostic
.venv/Scripts/python.exe scripts/dynamic/nonblocking/verify.py --output results/nonblocking/model_validation
.venv/Scripts/python.exe -m unittest discover -s tests -v
git diff --check
```

A repeated experiment needs a new --output directory. The accepted full matrix
was restarted after the preliminary checkpoint model corrupted output metadata.
That entire interrupted attempt and original source are retained in preliminary/;
no failed record was silently substituted in the final matrix. The revised case
models the same missed-lock publication access with a scalar length and immutable
backing; this additional reconstruction limit is documented in CASES.md.
