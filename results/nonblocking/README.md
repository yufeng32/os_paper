# Non-blocking reproduction results — 2026-11-24

This addition follows the blocking experiment's **pattern-level reconstruction**
method. It does not execute the complete historical applications. Commands and
case-level limits are in [the experiment guide](../../scripts/dynamic/nonblocking/README.md)
and [case-to-patch mapping](../../scripts/dynamic/nonblocking/CASES.md).

## Static audit: Tables 9–11

The pinned workbook yields 86 non-blocking records. All non-total cells match:

| Table | Compared cells | Differing cells |
| --- | ---: | ---: |
| 9: root causes | 36 | 0 |
| 10: fix strategies | 30 | 0 |
| 11: fix primitives | 42 | 0 |

Source rows and raw primitive flags remain in records_detail.csv. Channel is
the per-record union of channel-patch/select-patch; Misc is the union of
once-patch/go-patch. Primitive columns overlap. Recovering these annotations
does not independently validate every source label.

## Natural experiment

All 23 workbook-flagged candidates were assessed with buggy/fixed versions and
plain/race builds. Three batches each used 100 independent process runs per
combination: **27,600 executions**, with **0 infrastructure errors**.

| Outcome | Cases |
| --- | ---: |
| Target wrong result, panic or ordering violation observed | 14 |
| Target race reported without a separate visible error | 8 |
| Neither observed | 1 |
| Fixed controls passed | 23/23 |

The fixed controls cover **13,800 executions** across both builds. Every batch
reports a target race for **18/23 candidates (78.26%)** within its 100-run budget;
batch coverage mean is **78.26%**, sample SD **0.00 percentage points**. This is
candidate warning coverage, not an estimate of detector recall: the unobserved
timer candidate is not an established detector miss. Four observed logical or
language-rule failures have no target race report.

| Root cause | Paper used/detected | Our candidates/reported (each batch) |
| --- | ---: | ---: |
| Traditional | 13/7 | 13/12 |
| Anonymous function | 4/3 | 4/4 |
| Shared-memory library | 2/0 | 2/1 |
| Channel misuse | 1/0 | 4/1 |
| Total | 20/10 | 23/18 |

The paper's exact 20-case membership has not been recovered. The workbook flags
four channel cases, not one. Different membership, isolated/repeated operations,
toolchain and library behavior prevent interpreting the higher warning coverage
as an improvement over the paper's detector. See [full comparison](runtime/comparison.md),
[case summaries](runtime/summary.csv), [batch results](runtime/batch_results.csv)
and [all raw results](runtime/raw_results.csv).

The unobserved candidate is **etcd#3593**, commit `5d033c22afdf…`. Its historical
AfterFunc/Reset pattern runs without a target warning or visible failure on the
recorded toolchain. The context case explicitly reconstructs Go 1.7 formatting
behavior; Go 1.20 no longer traverses a non-Stringer value in the same way.

## Environment and retained evidence

The run uses a verified official **Go 1.20.14 windows/amd64** portable archive,
Python **3.12.13**, and MinGW-W64 **gcc 16.1.0**. GOMAXPROCS=2 per process;
up to eight repetitions of the same case/build/variant overlap. No cases or
variants overlap within the runner. GORACE removes the exit delay after target
work completes. Versions, flags, commands and hashes are in runtime/environment.json,
builds.json and run.json. Positive/negative detector probes passed first.

- `runtime/`: final natural matrix, including every JSON log inside logs.zip.
- `diagnostic/`: separate controlled scheduling diagnostics; excluded from natural rates.
- `model_validation/`: 1,200 checkpoint scalar-model validation runs, fully verified.
- `preliminary/`: interrupted composite-header attempt and source snapshots,
  excluded from final results. A corrupted case ID was rejected rather than
  silently accepted. The final model represents publication with a scalar length
  and immutable backing, preserving the missing-lock access without header tearing.
- `tests.txt`: 25 passing unit tests.

The controlled diagnostic contains **276 executions**, zero infrastructure errors
and 23/23 clean fixed controls. Its extra ordering edges change which warnings
are possible; its three-run budget and results are not part of the natural
100-run comparison. Verification records for the natural, diagnostic and
scalar-validation archives are retained in their respective verification.json files.

The verifier reads logs.zip directly and checks every log hash, command,
classification, matrix cell and case summary. It also verifies archive membership
and archive SHA-256. Individual uncompressed log copies are ignored by Git;
the complete archives are retained. Existing blocking-bug outputs are unchanged.
