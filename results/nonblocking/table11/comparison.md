# Table 11: Paper vs. Ours

Pinned workbook: f2655063a2278cff64a51121b73801eda05fdcfa; 86 non-blocking records. Paper PDF p. 11.

| Group | Mutex | Channel | Atomic | WaitGroup | Cond | Misc | None |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| traditional | 24 | 3 | 6 | 0 | 0 | 0 | 13 |
| anonymous | 3 | 2 | 3 | 0 | 0 | 0 | 3 |
| waitgroup | 2 | 0 | 0 | 4 | 3 | 0 | 0 |
| shared_lib | 0 | 2 | 1 | 1 | 0 | 1 | 2 |
| channel | 3 | 11 | 0 | 2 | 1 | 2 | 1 |
| message_lib | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| Total | 32 | 19 | 10 | 7 | 4 | 3 | 19 |

Differing non-total cells: **0/42**. Signed differences are in comparison.csv.

Channel is the per-record union of channel-patch and select-patch (select operates on channels).
Misc is the per-record union of once-patch and go-patch. Unions count once per record.
Other primitive columns overlap.
These columns are not a partition of 86 bugs. Raw flags remain in records_detail.csv.
