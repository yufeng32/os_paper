# syntax=docker/dockerfile:1
# Week 2: pin the OS userland, the Python patch version and the tools used by
# the existing Table 5 audit. The Go toolchain is deliberately NOT installed:
# runtime and detector work belongs to Week 3 and will be pinned there.
#
# If the exact patch tag is unavailable on your registry, change the FROM line
# to `FROM python:3.12-slim-bookworm` and record that substitution in
# docs/reproduction-scope.md before committing.
ARG PYTHON_VERSION=3.12.13
FROM python:${PYTHON_VERSION}-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates git make \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY .python-version requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python scripts/verify_env.py

CMD ["python", "run.py"]
