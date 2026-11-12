#!/usr/bin/env python3
"""Copy a safe, minimal cargo-generate starter template. Python 3.11+."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New template directory (must not exist)")
    parser.add_argument("--kind", choices=("bin", "lib", "workspace"), default="bin", help="Crate kind")
    args = parser.parse_args()

    source = Path(__file__).resolve().parent.parent / "assets" / f"{args.kind}-template"
    destination = args.destination.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"Bundled starter not found: {source}")
    if destination.exists() or destination.is_symlink():
        parser.error(f"Refusing to overwrite existing path: {destination}")
    try:
        shutil.copytree(source, destination)
    except OSError as exc:
        print(f"ERROR: could not scaffold template: {exc}", file=sys.stderr)
        return 1
    print(f"Created {args.kind} cargo-generate template: {destination}")
    print(f"Lint: python3 {Path(__file__).with_name('validate_template.py')} {destination} --strict")
    print(f"Try: cargo generate --path {destination} --name demo-crate --silent --vcs none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
