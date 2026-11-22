# Table 6: Blocking Bug Root Causes — Paper vs. Ours

Source: Tu et al., ASPLOS 2019, Table 6, PDF p. 6. Same 85 blocking records as the Table 5 audit.
Each blocking record is assigned to exactly one cause category (partition rule in analyze_table6_7.py).

| Application | Mutex | RWMutex | Wait | Chan | Chan_w | Lib |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Docker | 9 | 0 | 3 | 5 | 2 | 2 |
| Kubernetes | 6 | 2 | 0 | 3 | 6 | 0 |
| etcd | 5 | 0 | 0 | 10 | 5 | 1 |
| CockroachDB | 4 | 3 | 0 | 5 | 0 | 0 |
| gRPC | 2 | 0 | 0 | 6 | 2 | 1 |
| BoltDB | 2 | 0 | 0 | 0 | 1 | 0 |
| Total | 28 | 5 | 3 | 29 | 16 | 4 |

Cells differing from the paper: **0** (bolded above).
Total row: ours = [28, 5, 3, 29, 16, 4], paper = [28, 5, 3, 29, 16, 4].
