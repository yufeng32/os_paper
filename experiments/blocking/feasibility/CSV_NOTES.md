# Column notes — `feasibility_results.csv`

Three status columns are deliberately **strings, not booleans**, so that "we did not try" can never
be read as "we tried and failed":

| Column | Values used | Meaning |
| --- | --- | --- |
| `get_code_success` | `true` | the buggy file and the fix commit were both retrieved from upstream and compared |
| `full_repo_compile_status` | `not_attempted` | the complete historical Kubernetes tree was **never built** (pre-modules tree: `Godeps` + `vendor`, Go 1.6/1.7 era). This is not a failed build; it is an untried one, and it is listed as a limitation |
| `reproducer_build_status` | `success` | `go build` of `reproducer/` with Go 1.20.14 succeeded (see `build_log.txt` STEP 6) |
| `blocking_occur` | `true` / `false` | whether the run ended with leaked goroutines parked in `select` |
| `mean_growth`, `sd_growth` | numbers | mean / standard deviation of `goroutine_growth` over the 3 repetitions of that same variant |

One row per run; `run_id` 1–3 within each `variant`. The `buggy` rows are the experiment, the
`fixed` rows are the control (a harness that leaks in *both* variants would be a broken harness,
not a reproduced bug).
