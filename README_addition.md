## Reproducibility (Week 2)

The environment is pinned in `Dockerfile` (`python:3.12.13-slim-bookworm`) and
`.python-version`. `Makefile` wraps the existing `run.py`; it does not add a
second analysis pipeline.

```sh
make setup          # install openpyxl==3.1.5 and et-xmlfile==2.0.0
make check          # preflight: interpreter, packages, git, files, dataset
make run            # Table 5 audit; expected: 171 records and 3 anomalies
make test           # unit tests
make env-record     # write results/environment.json
make docker-build   # pinned container; the build verifies the environment
make docker-run     # run the audit inside the container
```

`make run` needs network access on the first invocation only. It clones the
pinned dataset into ignored `data/upstream`, verifies the workbook SHA-256 and
writes `results/table5`. The analysis itself takes under a second; first-run
clone time varies. `make check` prints `FAIL=0` on a usable machine. A `WARN`
about the Python patch version is acceptable outside the container.

This reproduction is deliberately partial. The claims, the deviations table and
the weekly delivery plan are declared in
[docs/reproduction-scope.md](docs/reproduction-scope.md). Attribution, the
contribution statement and the AI usage statement are in
[ATTRIBUTION.md](ATTRIBUTION.md). Starting commit: `fae5844` (the completed Week 1 submission, pushed 2026-11-07).
