# CS340 reproduction - Week 2 build entry points.
# Every target wraps the EXISTING run.py; no second analysis pipeline is added.
# Override the interpreter when needed:  make PYTHON=py -3.12 check
PYTHON ?= python
VENV_PY := $(firstword $(wildcard .venv/bin/python .venv/Scripts/python.exe))
ifeq ($(VENV_PY),)
RUN_PY := $(PYTHON)
else
RUN_PY := $(VENV_PY)
endif

.PHONY: help setup check run test env-record docker-build docker-run clean

help:
	@echo "CS340 Go concurrency bug study - make targets"
	@echo "  make setup          install the pinned Python packages"
	@echo "  make check          preflight: interpreter, packages, git, files, dataset"
	@echo "  make run            run the Table 5 audit (existing run.py)"
	@echo "  make test           run the unit tests"
	@echo "  make env-record     write results/environment.json"
	@echo "  make docker-build   build the pinned container image"
	@echo "  make docker-run     run the audit inside the container"

setup:
	$(RUN_PY) -m pip install -r requirements.txt

check:
	$(RUN_PY) scripts/verify_env.py

run:
	$(RUN_PY) run.py

test:
	$(RUN_PY) -m unittest discover -s tests -v

env-record:
	$(RUN_PY) scripts/verify_env.py --write

docker-build:
	docker build --build-arg PYTHON_VERSION=3.12.13 -t cs340-repro:week2 .

docker-run:
	docker run --rm cs340-repro:week2

clean:
	$(RUN_PY) -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
