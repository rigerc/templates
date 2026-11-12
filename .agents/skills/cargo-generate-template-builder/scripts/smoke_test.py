#!/usr/bin/env python3
"""Generate a cargo-generate template in isolation, then cargo check and test it."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Path to local cargo-generate template")
    parser.add_argument("--name", default="skill-smoke-test", help="Generated project name")
    parser.add_argument("--define", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--workspace", action="store_true", help="Check/test all workspace members")
    parser.add_argument("--skip-build", action="store_true", help="Only test generation")
    parser.add_argument("--keep", action="store_true", help="Keep temporary output for debugging")
    args = parser.parse_args()

    template = args.template.expanduser().resolve()
    if not (template / "cargo-generate.toml").is_file():
        parser.error(f"Not a template root (missing cargo-generate.toml): {template}")
    for value in args.define:
        if "=" not in value or not value.split("=", 1)[0]:
            parser.error("--define must be of the form KEY=VALUE")
    if not shutil.which("cargo"):
        print("ERROR: 'cargo' not found. Install Rust/Cargo to run a generation test.", file=sys.stderr)
        return 2
    if not shutil.which("cargo-generate"):
        print("ERROR: 'cargo-generate' not found. Install it before smoke testing.", file=sys.stderr)
        return 2

    temp_obj = None
    if args.keep:
        working = Path(tempfile.mkdtemp(prefix="cargo-generate-skill-"))
    else:
        temp_obj = tempfile.TemporaryDirectory(prefix="cargo-generate-skill-")
        working = Path(temp_obj.name)

    commands = [["cargo", "generate", "--path", str(template), "--name", args.name, "--silent", "--vcs", "none"]]
    for definition in args.define:
        commands[0].extend(["--define", definition])
    flags = ["--workspace"] if args.workspace else []
    if not args.skip_build:
        commands.extend([["cargo", "check", *flags], ["cargo", "test", *flags]])

    try:
        dest = working / args.name
        for index, command in enumerate(commands):
            cwd = working if index == 0 else dest
            print(f"\n$ {' '.join(command)}\n  (cwd: {cwd})", flush=True)
            result = subprocess.run(command, cwd=cwd, check=False)
            if result.returncode:
                print(f"ERROR: step failed with exit code {result.returncode}", file=sys.stderr)
                return result.returncode
            if index == 0 and not dest.is_dir():
                print(f"ERROR: expected generated directory missing: {dest}", file=sys.stderr)
                return 1
        print(f"PASS: generation{' + Cargo checks' if not args.skip_build else ''}")
        return 0
    except OSError as exc:
        print(f"ERROR: failed to run command: {exc}", file=sys.stderr)
        return 1
    finally:
        if args.keep:
            print(f"Preserved generated output at: {working}")
        elif temp_obj is not None:
            temp_obj.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
