# Attribution, Contributions and AI Usage

## Original work and third-party material

1. Paper: Tengfei Tu, Xiaoyu Liu, Linhai Song, Yiying Zhang, *Understanding Real-World Concurrency Bugs in Go*, ASPLOS 2019. DOI 10.1145/3297858.3304069.
2. Dataset: <https://github.com/system-pclub/go-concurrency-bugs>, pinned to commit `f2655063a2278cff64a51121b73801eda05fdcfa`.
3. The workbook `bug table.xlsx` and the historical patch records belong to the original authors. The pinned upstream tree contains no license file.
4. We fetch that tree for analysis only. We do not vendor the workbook or patch files, and we do not modify any upstream file. Data directories are ignored by `.gitignore`.
5. Reference values for Tables 5–12 are transcribed from the paper and compared in the static-audit scripts and runtime results. Table 12 is compared with an explicitly different 23-candidate reconstruction cohort.

## Code written by this group

1. **Week 1** (`fae5844`): `run.py`, `scripts/analyze.py`, `scripts/dataset.py`, `tests/test_analysis.py` — the Table 5 audit.
2. **Week 2** (`e32a676`): `Dockerfile`, `.dockerignore`, `Makefile`, `scripts/verify_env.py`, `tests/test_verify_env.py`, `docs/reproduction-scope.md`, `ATTRIBUTION.md`, and a README section. `scripts/verify_env.py` imports the pinned constants from `scripts/dataset.py` instead of copying them.
3. **Week 3** (this update): `scripts/analyze_table6_7.py` (Tables 6–7 static audit), `scripts/dynamic/main.go`, `scripts/dynamic/go.mod`, `scripts/dynamic/run_all.py`, `scripts/dynamic/README.md` (Table 8 reduced runtime subset), plus `results/table6/`, `results/table7/`, `results/runtime/` and the `report/` skeleton. A supplementary case **b01** (`kubernetes#35672`, `ListAndWatch` resync goroutine leak), contributed by 1240026499 沈默, lives in `scripts/dynamic/b01-listwatch/` and `results/runtime/b01/`; it is outside the 21-bug Table 8 set. Week 3 does not change the Week 1 analysis code; it reuses `scripts/analyze.parse_rows` so all tables share the same 85 blocking records.

## Starting commit and modified files

| Item | Value |
| --- | --- |
| Starting commit | `fae5844` (2026-11-07), the completed Week 1 submission |
| Week 1 check | 2026-11-08 23:59, covered by `fae5844` |
| Week 2 check | 2026-11-15 23:59, covered by `e32a676` |
| Files added in Week 3 | `scripts/analyze_table6_7.py`, `scripts/dynamic/*`, `results/table6/*`, `results/table7/*`, `results/runtime/*`, `scripts/dynamic/b01-listwatch/*`, `results/runtime/b01/*`, `report/*` |
| Existing files changed in Week 3 | `README.md`, `docs/reproduction-scope.md`, `ATTRIBUTION.md` (documentation only; no analysis code or Week 1 results changed) |

## Contribution statement (draft, to be reconciled with the git log)

**2026-11-24 non-blocking addition (local, not yet committed):**
`scripts/analyze_nonblocking.py` reuses the existing record parser and input
verification for Tables 9–11. `scripts/dynamic/nonblocking/` adds authored
buggy/fixed pattern reconstructions, a race-detector runner, a verified portable
toolchain preparation script, per-case patch mappings and archive verification.
`results/nonblocking/` contains the new evidence. Additional upstream inspection
recovered the Bolt merge diff and confirmed historical Go 1.7 context formatting;
links and blob identities are recorded, without vendoring historical source.
AI assisted implementation and documentation. Student attribution for this
addition remains to be reconciled with the actual contributor's future commit;
no contribution is assigned to another member by inference.

The final report's contribution statement must match the actual commits. Rows marked "planned" are not yet evidence of contribution.

| Student ID | Full name | GitHub account | Week | Contribution |
| --- | --- | --- | --- | --- |
| 1240029057 | Yufeng Chen | yufeng32 | W1 (completed) | Table 5 audit, pinned dataset acquisition, README, reading notes, tests and validation at `fae5844` |
| 1240026499 | Shen Mo | woshimoshen | W2 | Kubernetes `ListAndWatch` blocking-bug feasibility study (`aa15909`, later retired in `e32a676`) |
| 1240026895 | Junjun Zhang | siriuszhang06-wq | W2 (completed) | Pinned environment, Dockerfile/Makefile/preflight, scope and attribution at `e32a676` |
| 1240026499 | Shen Mo | woshimoshen | W3 (this update) | b01 (`kubernetes#35672`) `ListAndWatch` resync goroutine-leak runtime case: pattern-level reproducer, 3-run buggy/fixed logs and case study under `scripts/dynamic/b01-listwatch/` and `results/runtime/b01/` |
| 1240029367 | 邵杰 | shao248 | W3 (this update) | Tables 6–7 static audit; Table 8 reduced runtime subset (8 cases, A/B); report skeleton |
| TBD | TBD | TBD | W4 | Extension and report draft |

> The Week 3 committers are **1240029367 邵杰** (GitHub `shao248`) and **1240026499 沈默** (GitHub `woshimoshen`). Commit messages must read `1240029367 邵杰: ...` and `1240026499 沈默: ...`. Every member must push substantive commits from their own account.

## AI usage statement

AI assistance was used to draft and check code and documentation; all committed material was reviewed by the team, who take responsibility for it. No generated text is presented as a runtime measurement: every reported number comes from executing this repository's own scripts, with commands and raw outputs retained under `results/`.
