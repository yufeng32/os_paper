"""Fetch the pinned input (or verify a local copy) and audit Table 5."""

import argparse
from pathlib import Path
import subprocess
import sys
import time

from scripts.analyze import analyze
from scripts.dataset import fetch

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--data-dir", type=Path, help="Directory containing the pinned bug table.xlsx")
    source.add_argument("--fetch-dir", type=Path, default=ROOT / "data" / "upstream",
                        help="Clone destination (default: repository data/upstream)")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "table5")
    args = parser.parse_args()
    started = time.perf_counter()
    try:
        data_dir = args.data_dir if args.data_dir is not None else fetch(args.fetch_dir)
        analyze(data_dir, args.output_dir)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Total elapsed: {time.perf_counter() - started:.3f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
