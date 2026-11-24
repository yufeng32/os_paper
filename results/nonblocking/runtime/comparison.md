# Non-blocking race-detector experiment

Schedule: **natural**. 23 candidate records; 3 batches x 100 runs per combination.
Completed process records: 27600/27600. Infrastructure errors: 0.

| Root cause | Paper used/detected | Ours attempted/eligible | Ours detected (any batch) |
| --- | ---: | ---: | ---: |
| traditional | 13/7 | 13/13 | 12 |
| anonymous | 4/3 | 4/4 | 4 |
| shared_lib | 2/0 | 2/2 | 1 |
| channel | 1/0 | 4/4 | 1 |

Paper Table 12 (PDF p. 11) uses 20 bugs and one budget of 100 runs per bug;
the pinned workbook flags 23 candidates (four channel cases instead of one). No exact 20-case cohort is established.
Our samples are standalone pattern reconstructions under Go 1.20.14, not the historical applications.
Counts are not an estimate of the original detector's accuracy. Case identities are in manifest.json;
raw commands, exit codes, observations and reports are preserved per run.

| Batch | Eligible cases | Detected within budget | Rate |
| --- | ---: | ---: | ---: |
| 1 | 23 | 18 | 78.26% |
| 2 | 23 | 18 | 78.26% |
| 3 | 23 | 18 | 78.26% |

Batch rate mean = 78.26%; sample SD = 0.00%.

A case is eligible only when all requested executions finish without infrastructure errors and its fixed control is clean.
Unobserved candidates remain in the attempted-cohort table and in the eligible denominator; they are NOT established detector misses.
A target race report establishes the conflicting access, even when the ordinary output appears correct.
Target panics, lost notifications and ordering violations are classified separately from detector warnings.
The timerReuse candidate retains its historical API pattern without injecting a user-level race; no observation means no confirmed reproduction.
Controlled diagnostics are excluded from the natural detection table.

## Per-case status

| Case | Status | Plain symptoms | Race warnings |
| --- | --- | ---: | ---: |
| docker_4e262f638760 | behavior_reproduced | 300 | 0 |
| docker_c1ad02ccc879 | behavior_reproduced | 300 | 300 |
| docker_1670914b8a56 | behavior_reproduced | 247 | 300 |
| docker_825e3a66a419 | behavior_reproduced | 15 | 300 |
| kubernetes_345f875c51c0 | race_reproduced_only | 0 | 300 |
| kubernetes_647b826d697a | behavior_reproduced | 174 | 299 |
| kubernetes_3c345abafd02 | race_reproduced_only | 0 | 300 |
| etcd_5d033c22afdf | not_observed | 0 | 0 |
| etcd_c678dcbd9172 | race_reproduced_only | 0 | 300 |
| etcd_91dc6b29a6e0 | race_reproduced_only | 0 | 296 |
| etcd_2c83362e63e6 | behavior_reproduced | 110 | 300 |
| etcd_e129223dbeba | behavior_reproduced | 300 | 300 |
| etcd_3ce31acda410 | race_reproduced_only | 0 | 300 |
| etcd_4bdfc0a46d28 | behavior_reproduced | 290 | 300 |
| etcd_7f95780bfb5d | behavior_reproduced | 300 | 0 |
| cockroachdb_d5a604c99d9e | race_reproduced_only | 0 | 299 |
| cockroachdb_4edda446686e | race_reproduced_only | 0 | 300 |
| grpc_go_c6b46087ab92 | behavior_reproduced | 300 | 0 |
| grpc_go_b71aced4a2a1 | behavior_reproduced | 68 | 300 |
| grpc_go_a62701e4aa1d | behavior_reproduced | 190 | 298 |
| grpc_go_87bcb38fba80 | race_reproduced_only | 0 | 300 |
| boltdb_c69cb102ce8f | behavior_reproduced | 300 | 0 |
| boltdb_7fb06feea401 | behavior_reproduced | 80 | 300 |
