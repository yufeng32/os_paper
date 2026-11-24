# Table 9: Paper vs. Ours

Pinned workbook: f2655063a2278cff64a51121b73801eda05fdcfa; 86 non-blocking records. Paper PDF p. 9.

| Group | traditional | anonymous | waitgroup | shared_lib | channel | message_lib |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Docker | 9 | 6 | 0 | 1 | 6 | 1 |
| Kubernetes | 8 | 3 | 1 | 0 | 5 | 0 |
| etcd | 9 | 0 | 2 | 2 | 3 | 0 |
| CockroachDB | 10 | 1 | 3 | 2 | 0 | 0 |
| gRPC | 8 | 1 | 0 | 1 | 2 | 0 |
| BoltDB | 2 | 0 | 0 | 0 | 0 | 0 |
| Total | 46 | 11 | 6 | 6 | 16 | 1 |

Differing non-total cells: **0/36**. Signed differences are in comparison.csv.
