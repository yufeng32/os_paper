# Table 7: Blocking Bug Fix Strategies — Paper vs. Ours

Source: Tu et al., ASPLOS 2019, Table 7, PDF p. 8. Cross-tab of cause (rows) x fix strategy (columns).
Cause rows use the same partition as Table 6; each record has exactly one fix-strategy flag.

| Cause | Adds | Moves | Changes | Removes | Misc | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mutex | 9 | 7 | 2 | 8 | 2 | 28 |
| RWMutex | 0 | 2 | 0 | 3 | 0 | 5 |
| Wait | 0 | 1 | 0 | 1 | 1 | 3 |
| Chan | 15 | 1 | 5 | 4 | 4 | 29 |
| Chan_w | 6 | 3 | 2 | 4 | 1 | 16 |
| Lib | 1 | 0 | 0 | 1 | 2 | 4 |
| **Total** | 31 | 14 | 9 | 21 | 10 | 85 |
| _paper total_ | 31 | 14 | 9 | 21 | 10 | 85 |