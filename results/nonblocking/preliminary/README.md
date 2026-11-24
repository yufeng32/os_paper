# Preliminary attempt — excluded from final results

This natural-matrix attempt was interrupted after a checkpoint slice-copy race corrupted the case ID in one RESULT record. The parser correctly rejected that record as wrong_case_result. No mismatch was silently accepted as a valid execution.

The original source/driver snapshots, raw_results.csv and logs.zip preserve the attempt, including the corrupted record. run.json marks the attempt as excluded. The final experiment uses an explicitly documented scalar publication-count reconstruction for this one case, in a new runtime directory. These logs are not combined with the final matrix.
