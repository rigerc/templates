#!/usr/bin/env python3
"""Validate every template in the monorepo with the vendored skill helpers.

Discovers directories under templates/ that contain a cargo-generate.toml and
runs the skill's static validator (and optionally a real generation + build)
against each one.

Usage:
    python3 scripts/validate_all.py [--strict] [--smoke] [--only name[,name]]
    python3 scripts/validate_all.py --list
    python3 scripts/validate_all.py --list-json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
SKILL = ROOT / ".agents" / "skills" / "cargo-generate-template-builder"
VALIDATOR = SKILL / "scripts" / "validate_template.py"
SMOKE_TEST = SKILL / "scripts" / "smoke_test.py"


def discover() -> list[Path]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(
        path
        for path in TEMPLATES_DIR.iterdir()
        if path.is_dir() and (path / "cargo-generate.toml").is_file()
    )


def filter_changed(templates: list[Path], ref: str) -> list[Path]:
    """Keep only templates touched since ref; a shared change keeps everything."""
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "diff", "--name-only", f"{ref}...HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(
            f"warning: cannot diff against {ref} ({exc}); listing all templates",
            file=sys.stderr,
        )
        return templates

    changed = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not changed:
        return []
    for path in changed:
        if not path.startswith("templates/"):
            return templates
    touched = {path.split("/", 2)[1] for path in changed if path.count("/") >= 2}
    return [template for template in templates if template.name in touched]


def run(command: list[str]) -> int:
    return subprocess.run(command, cwd=ROOT).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="fail on validator warnings"
    )
    parser.add_argument(
        "--smoke", action="store_true", help="also generate and build each template"
    )
    parser.add_argument("--only", help="comma-separated template directory names")
    parser.add_argument("--list", action="store_true", help="print template names")
    parser.add_argument(
        "--list-json", action="store_true", help="print template names as JSON"
    )
    parser.add_argument(
        "--changed-since",
        metavar="REF",
        help="limit to templates touched since REF; shared changes keep all",
    )
    args = parser.parse_args()

    templates = discover()
    if args.changed_since:
        templates = filter_changed(templates, args.changed_since)

    if args.list_json:
        print(json.dumps([path.name for path in templates]))
        return 0
    if args.list:
        for path in templates:
            print(path.name)
        return 0

    if not VALIDATOR.is_file():
        print(f"ERROR: validator not found at {VALIDATOR}", file=sys.stderr)
        return 2

    if args.only:
        requested = [name.strip() for name in args.only.split(",") if name.strip()]
        known = {path.name: path for path in templates}
        unknown = [name for name in requested if name not in known]
        if unknown:
            print(f"ERROR: unknown template(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        templates = [known[name] for name in requested]

    if not templates:
        print("No templates found under templates/; nothing to validate.")
        return 0

    failures: list[str] = []
    for template in templates:
        label = f"templates/{template.name}"
        print(f"\n==> {label}", flush=True)

        command = [sys.executable, str(VALIDATOR), str(template)]
        if args.strict:
            command.append("--strict")
        if run(command) != 0:
            failures.append(f"{label}: static validation failed")
            continue

        if args.smoke:
            if not SMOKE_TEST.is_file():
                failures.append(f"{label}: smoke test helper missing")
                continue
            print(f"--> {label}: generating and building", flush=True)
            if run([sys.executable, str(SMOKE_TEST), str(template)]) != 0:
                failures.append(f"{label}: smoke test failed")

    print()
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        print(f"\n{len(failures)} of {len(templates)} template(s) failed")
        return 1

    mode = "validation + smoke test" if args.smoke else "static validation"
    print(f"PASS: {len(templates)} template(s) passed {mode}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
