# Attribution, Contributions and AI Usage

## Original work and third-party material

1. Paper: Tengfei Tu, Xiaoyu Liu, Linhai Song, Yiying Zhang, *Understanding Real-World Concurrency Bugs in Go*, ASPLOS 2019. DOI 10.1145/3297858.3304069.
2. Dataset: <https://github.com/system-pclub/go-concurrency-bugs>, pinned to commit `f2655063a2278cff64a51121b73801eda05fdcfa`.
3. The workbook `bug table.xlsx` and the historical patch records belong to the original authors. The pinned upstream tree contains no license file.
4. We fetch that tree for analysis only. We do not vendor the workbook or patch files, and we do not modify any upstream file. Data directories are ignored by `.gitignore`.
5. The reference values compared in `scripts/analyze.py` are transcribed from Table 5 of the paper; the paper is cited in the final report.

## Code written by this group

1. `run.py`, `scripts/analyze.py`, `scripts/dataset.py`, `tests/test_analysis.py`: new analysis code written for this course, at starting commit `fae5844`.
2. Week 2 additions: `Dockerfile`, `.dockerignore`, `Makefile`, `scripts/verify_env.py`, `tests/test_verify_env.py`, `docs/reproduction-scope.md`, `ATTRIBUTION.md`, and one README section.
3. Week 2 changes no existing source file. `scripts/verify_env.py` imports the pinned constants from `scripts/dataset.py` instead of copying them.

## Starting commit and modified files

| Item                     | Value                                                   |
| ------------------------ | ------------------------------------------------------- |
| Starting commit          | `fae5844` (2026-11-07), the completed Week 1 submission |
| Week 1 check             | 2026-11-08 23:59, covered by `fae5844`                  |
| Files added in Week 2    | 7 files listed above, plus a README section             |
| Files modified in Week 2 | none of the existing analysis code or results           |

## AI usage statement

1. An AI assistant drafted scripts, documentation and the Week 2 preflight check, and helped transcribe and check the course requirements.
2. Team members review, edit and take responsibility for all committed material. No text is committed without review.
3. No AI-generated sentence is presented as a runtime measurement. All reported numbers come from executing the repository's own scripts; commands and raw outputs are retained in `results/`.
4. This statement will be reproduced and, if necessary, extended in the final report.
