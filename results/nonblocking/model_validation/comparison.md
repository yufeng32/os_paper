# Non-blocking race-detector experiment

Schedule: **natural**. 1 candidate records; 3 batches x 100 runs per combination.
Completed process records: 1200/1200. Infrastructure errors: 0.

| Root cause | Paper used/detected | Ours attempted/eligible | Ours detected (any batch) |
| --- | ---: | ---: | ---: |
| traditional | 13/7 | 0/0 | 0 |
| anonymous | 4/3 | 1/1 | 1 |
| shared_lib | 2/0 | 0/0 | 0 |
| channel | 1/0 | 0/0 | 0 |

Paper Table 12 (PDF p. 11) uses 20 bugs and one budget of 100 runs per bug;
the pinned workbook flags 23 candidates (four channel cases instead of one). No exact 20-case cohort is established.
Our samples are standalone pattern reconstructions under Go 1.20.14, not the historical applications.
Counts are not an estimate of the original detector's accuracy. Case identities are in manifest.json;
raw commands, exit codes, observations and reports are preserved per run.

| Batch | Eligible cases | Detected within budget | Rate |
| --- | ---: | ---: | ---: |
| 1 | 1 | 1 | 100.00% |
| 2 | 1 | 1 | 100.00% |
| 3 | 1 | 1 | 100.00% |

Batch rate mean = 100.00%; sample SD = 0.00%.

A case is eligible only when all requested executions finish without infrastructure errors and its fixed control is clean.
Unobserved candidates remain in the attempted-cohort table and in the eligible denominator; they are NOT established detector misses.
A target race report establishes the conflicting access, even when the ordinary output appears correct.
Target panics, lost notifications and ordering violations are classified separately from detector warnings.
The timerReuse candidate retains its historical API pattern without injecting a user-level race; no observation means no confirmed reproduction.
Controlled diagnostics are excluded from the natural detection table.

## Per-case status

| Case | Status | Plain symptoms | Race warnings |
| --- | --- | ---: | ---: |
| cockroachdb_d5a604c99d9e | race_reproduced_only | 0 | 300 |
