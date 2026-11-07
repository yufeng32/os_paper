# Reproduction Method, Findings, and Next Milestone

## Completed first milestone: Table 5 audit

Input: the authors' [dataset](https://github.com/system-pclub/go-concurrency-bugs) at `f2655063a2278cff64a51121b73801eda05fdcfa`. Workbook SHA-256: `a0e5f0103600b3c394b86cb975f403789366f0190312019fae648de0cd8e3235`.

Reference: [paper](https://songlh.github.io/paper/go-study.pdf), Table 5, PDF p. 5. Reference values are transcribed in `scripts/analyze.py` and compared cell by cell. The `application` sheet and detail-sheet summary cells are not used as observations.

## Counting rules

1. Read `blocking` and `non-blocking` in source order. Locate exact field headers: root-cause columns differ between sheets.
2. Include a positive-integer-serial row, or a recognized application plus full hash or issue-style identifier. Serial numbers restart per application. Preserve candidates with incomplete metadata and report anomalies.
3. Exclude headers, blank rows, summaries, and annotations; record every disposition in `row-audit.csv`. An application name alone does not identify a bug record.
4. Normalize whitespace/case and map `grpc`/`grpc-go` to `gRPC`; preserve original spelling. Unrecognized applications remain `Unknown`.
5. Count each included row once in its behavior category. Reject duplicate normalized application/identifier keys within a sheet. Different commits referencing the same issue remain separate source records.
6. Preserve raw `shared`/`message` flags. Valid flags are numeric 0 or 1. One 1 gives an exclusive cause; two 1s mean `ambiguous_both`; two 0s mean `unclassified`; missing/malformed flags mean `invalid`. Infer no label from the desired paper total.
7. Count valid root-cause flags independently. A dual-marked record contributes to both marginals, but once to the behavior total. Invalid pairs contribute to neither marginal and remain visible in unresolved counts.

`records.csv` links each observation to its worksheet and physical one-based row. `counts.csv` includes unresolved counts. `comparison.csv` contains signed (`Ours - Paper`) and absolute differences. Deterministic outputs should match across input routes; time/environment metadata need not match.

## Findings and discrepancy evidence

All per-application behavior counts match: 85 blocking and 86 non-blocking. Raw cause marginals are 106 shared-memory flags and 66 message-passing flags. The only per-application mismatch is Kubernetes shared memory: 21 versus 20. The difference is 1 (5% of the paper's Kubernetes value; approximately 0.95% of its shared-memory total).

| Source | Observation | Treatment |
| --- | --- | --- |
| `blocking`, row 90 | `boltdb#392` in the commit-hash field; flags `(0, 1)` | Retain message-passing blocking record |
| `blocking`, row 92 | `boltdb#240` in the commit-hash field; flags `(1, 0)` | Retain shared-memory blocking record |
| `blocking`, row 35 | Kubernetes `e98c8e7685f4475e091f9186606098039c2fc250`; flags `(1, 1)` | Preserve both flags; exclusive cause unresolved |

The first two explain why a full-hash filter returns only 83 blocking records. The pinned upstream `blocking-bugs/boltdb/` contains only the third BoltDB record's patch file. A missing patch does not erase a workbook observation or establish runtime reproducibility.

For the third record, upstream `blocking-bugs/kubernetes/e98c8e7685f4475e091f9186606098039c2fc250.txt` describes a deadlock involving a condition variable's lock, and a change to channel notification. This provides context, but does not establish the paper's intended exclusive label. Both original flags explain the arithmetic discrepancy; we do not silently replace `(1, 1)` with `(0, 1)`.

**Verdict:** behavior counts are recovered; the exclusive root-cause taxonomy is partially recovered. This verifies annotations/arithmetic, not the correctness of every classification.

## Course alignment and remaining work

This update supplies code, a pinned input/dependencies, README-only run instructions, traceable outputs, discrepancy evidence, and an ignore file. First-week submission still needs review, a meaningful commit with the real contributor's student ID/full name, and a push to the confirmed remote before the weekly deadline.

Next, attempt a historical build/trigger feasibility check for a blocking case linked to Table 8. Recover the repository, buggy/fixing revisions, input, and original settings before selecting the runtime subset. Missing builds/inputs are feasibility outcomes, not negative detector results.

Later attempts must preserve commands, versions, workload, concurrency settings, timeout, exit status, logs, symptom observations, and detector reports. A timeout alone does not establish the intended bug. Compare matching cases/metrics, state all deviations, and perform at least three independent runtime runs/batches for mean and standard deviation. Repeated deterministic counts do not meet that statistical requirement.

Final work also requires figures, evidence-based claim verdicts, an extension changing one factor at a time, member contributions, AI usage, and tag `v1.0`. The extension and full runtime sample will be selected after baseline feasibility; neither is completed here.
