"""Prepare a portable, SHA-256-verified Go baseline inside the ignored cache."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[3]
FILENAME = "go1.20.14.windows-amd64.zip"
SIZE = 114273182
SHA256 = "0e0d0190406ead891d94ecf00f961bb5cfa15ddd47499d2649f12eee80aee110"
URL = "https://dl.google.com/go/" + FILENAME


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, default=ROOT / ".cache/nonblocking-toolchain")
    a = p.parse_args()
    directory = a.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    archive = directory / FILENAME
    if not archive.exists() or archive.stat().st_size != SIZE:
        curl = shutil.which("curl.exe") or shutil.which("curl")
        if not curl:
            raise SystemExit("curl is required to download the official archive")
        subprocess.run([curl, "-L", "--fail", "-C", "-", "--connect-timeout", "15", "--max-time", "900",
                        "-o", str(archive), URL], check=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != SHA256:
        raise SystemExit("Archive SHA-256 mismatch; nothing was extracted or executed")
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            member = PurePosixPath(name)
            if member.is_absolute() or ".." in member.parts or "\\" in name or ":" in name:
                raise SystemExit("Unsafe archive member")
        if not (directory / "go/bin/go.exe").exists():
            z.extractall(directory)
    receipt = {"url": URL, "metadata_url": "https://go.dev/dl/?mode=json&include=all",
               "filename": FILENAME, "size": SIZE, "sha256": digest, "version": "go1.20.14"}
    (directory / "download.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print("Verified portable toolchain:", directory / "go/bin/go.exe")


if __name__ == "__main__":
    main()
