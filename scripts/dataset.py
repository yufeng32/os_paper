"""Pinned study input and non-destructive acquisition."""

import hashlib
import os
from pathlib import Path
import subprocess
from urllib.request import getproxies

URL = "https://github.com/system-pclub/go-concurrency-bugs.git"
COMMIT = "f2655063a2278cff64a51121b73801eda05fdcfa"
WORKBOOK = "bug table.xlsx"
SHA256 = "a0e5f0103600b3c394b86cb975f403789366f0190312019fae648de0cd8e3235"


def verify(data_dir: Path) -> str:
    """Accept a local directory or export only if workbook bytes match the pin."""
    digest = hashlib.sha256((data_dir / WORKBOOK).read_bytes()).hexdigest()
    if digest != SHA256:
        raise ValueError(f"Workbook SHA-256 mismatch: expected {SHA256}, got {digest}")
    return digest


def fetch(target: Path) -> Path:
    """Clone on first use; never reset, clean, or overwrite an existing checkout."""
    # Git does not automatically read Windows Internet Settings. Honor the
    # existing system proxy for this subprocess only; never change Git config.
    env = os.environ.copy()
    for scheme, proxy in getproxies().items():
        if scheme in ("http", "https"):
            key = f"{scheme.upper()}_PROXY"
            if not any(k.casefold() == key.casefold() for k in env):
                env[key] = proxy
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--no-checkout", URL, str(target)], check=True, env=env)
        subprocess.run(["git", "-C", str(target), "checkout", "--detach", COMMIT], check=True, env=env)
    head = subprocess.check_output(
        ["git", "-C", str(target), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != COMMIT:
        raise ValueError(f"Existing checkout is at {head}; use a new --fetch-dir")
    dirty = subprocess.check_output(
        ["git", "-C", str(target), "status", "--porcelain"], text=True
    ).strip()
    if dirty:
        raise ValueError("Existing checkout has changes; use a new --fetch-dir")
    verify(target)
    return target
