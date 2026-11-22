# Evidence

Real material pulled from upstream, kept here so the investigation can be re-checked without
network access. Kubernetes is Apache-2.0 licensed; the excerpts below are reproduced for
research/comments only and keep their original attribution.

| File | What it is | Source |
| --- | --- | --- |
| `buggy_ListAndWatch.go.txt` | the buggy version of `ListAndWatch` (lines 233-278 of the file) at the parent commit | `kubernetes/kubernetes`, `pkg/client/cache/reflector.go` @ `6abb4723571fc6b9e4dc05807511569dfc865f83` |
| `fix_commit_991674380.txt` | the full fix commit (`git show`): message + diff | `system-pclub/go-concurrency-bugs`, `blocking-bugs/kubernetes/991674380b7773d73afaeafeac6242bf3b6e6001.txt` |

How the two were obtained is recorded in `../build_log.txt` (STEP 3 / STEP 4).
