# Report skeleton (Week 3 placeholder)

This directory holds the final course report. Per
[`docs/reproduction-scope.md`](../docs/reproduction-scope.md), the report is a
six-section English document with claim verdicts, quantified gaps, a deviations
table, a contribution statement and an AI usage statement. This skeleton is
added in Week 3; sections are filled in Week 4 and the Final milestone. No
claim verdict may be written before the underlying measurement exists.

**2026-11-24 update:** the report now includes the non-blocking audit and the
separate 23-candidate buggy/fixed experiment. Its original Week 3 section list
below is historical. Current evidence is in `results/nonblocking/`; no claim is
made that the paper's exact 20-case Table 12 cohort has been recovered. This
addition does not complete the planned one-factor extension or the final report.

## Sections to complete

1. **Introduction and question** — the paper studied in one paragraph, the two
   fixed claims (C1: Table 5 counts; C2: detector detection of a blocking subset),
   and the reduced-scale setting.
2. **Method** — pinned dataset and workbook, static audit route, dynamic
   reproducer route, three independent runs per runtime case, environment
   recording.
3. **Results**
   - C1 (Table 5): see `results/table5/comparison.md`; behaviour totals match,
     one shared-memory margin differs by 1.
   - C2 (runtime baseline, case b01): see `results/runtime/b01/README.md`.
     Detector outcomes (built-in deadlock detector, `-race`) are recorded only
     after they are actually run.
4. **Deviations from the paper** — reduced runtime subset, reconstruction
     instead of the full historical tree, three repetitions, pinned container;
     track against the deviations table in `docs/reproduction-scope.md`.
5. **Contribution statement** — who did what; reconcile against `ATTRIBUTION.md`
   before the Final tag.
6. **AI usage statement** — reproduce and extend the statement in
   `ATTRIBUTION.md`; numbers in the report come only from executing the
   repository's own scripts and harnesses.

## Status markers

- `[done]` — measured and recorded in this repository.
- `[planned]` — scheduled for a later week; not a result yet.
- `[tbd]` — open question that needs a measurement or a group decision.

## Current baseline for case b01

| variant | growth per 5 calls (3 runs) | mean ± SD | blocked | verdict |
| --- | --- | --- | --- | --- |
| buggy | 5, 5, 5 | 5.00 ± 0.00 | 5 | blocking reproduced in the reconstruction |
| fixed | 0, 0, 0 | 0.00 ± 0.00 | 0 | control holds |

These numbers describe the reconstructed pattern only; see the reproduction
limitation in `results/runtime/b01/README.md`.
