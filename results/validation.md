# First Update Validation

Performed on 2026-11-08 (Asia/Macau). This validates the data-audit pipeline, not historical Go runtime behavior. Structured evidence and output checksums are in [verification.json](verification.json).

## Environment

- Python 3.12.13; openpyxl 3.1.5; et-xmlfile 2.0.0.
- Git 2.55.0.windows.4.
- Windows 11, version 10.0.26200, AMD64.
- Processor identification: Intel64 Family 6 Model 183 Stepping 1, GenuineIntel.
- Input fingerprint and exact UTC run times are retained in the run metadata.

## Commands and outcomes

Commands ran from the repository root unless stated otherwise:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

The environment was newly created; both pinned packages installed successfully. The default `data/upstream` destination did not exist before the run. The clone checked out the pinned commit and produced 171 records and 3 anomalies. Total elapsed time including cloning was **3.745 seconds**; analysis/output generation took **0.231874 seconds**. All **6 unit tests passed**; `pip check` reported no broken requirements.

The initial direct GitHub clone failed to connect. After the fetch script was updated to honor the existing system proxy for its Git subprocess only, fresh acquisition succeeded. No global Git configuration was changed and no proxy address/credential was embedded in the repository.

The second route used the existing `../origin_code/go-concurrency-bugs` workbook, invoked `run.py` by its absolute path from the parent directory, and wrote to `.cache/local results` (a Unicode absolute path containing spaces). It succeeded in **0.200 seconds** total, with **0.198722 seconds** for analysis/output generation.

Byte comparisons passed for `records.csv`, `counts.csv`, `comparison.csv`, `anomalies.csv`, `row-audit.csv`, and `comparison.md`. The two `run.json` files intentionally differ in timestamp and measured time. No mean or standard deviation is calculated for these deterministic counts.

## Integrity and failure-path checks

- Included IDs are unique and correspond exactly to included worksheet/row pairs in the row audit.
- All 209 physical rows in the two detail sheets have dispositions: 171 included, 18 blank, 18 summary/annotation, and 2 headers.
- Only Kubernetes shared-memory flags and the corresponding total differ from Table 5; each absolute difference is 1.
- Appending test bytes to a disposable workbook copy caused SHA-256 rejection with exit code 1 before creating its output directory.
- Adding an untracked marker to a disposable clone caused the fetch route to reject the dirty checkout with exit code 1. The marker remained intact.
- Git ignore checks passed for dataset/virtual-environment/cache paths; the result CSVs and metadata remain eligible for commit.

## Limits

Executed on Windows only. Linux/macOS commands are provided but have not been tested here. Timings describe this machine and network session. No historical application build, bug-trigger experiment, detector evaluation, or extension was performed. Submission identity confirmed by the user: 1240029057 陈钰丰. Target repository: https://github.com/yufeng32/os_paper. Publication is verified separately after the local validation recorded here.
