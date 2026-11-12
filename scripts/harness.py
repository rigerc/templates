#!/usr/bin/env python3
"""Local harness: generate every template and build the result.

For each template under templates/ the harness runs `cargo generate` into a
throwaway directory, checks that the output contains no unrendered Liquid or
leaked template configuration, then runs `cargo check` and `cargo test` in the
generated project. Failures keep their working directory for inspection.

Usage:
    python3 scripts/harness.py                    # default case per template
    python3 scripts/harness.py --matrix           # plus placeholder variants
    python3 scripts/harness.py --template rust-cli
    python3 scripts/harness.py --no-build         # generation only
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
DEFAULT_TIMEOUT = 900
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".so",
    ".dylib",
    ".dll",
    ".wasm",
}
BUILTIN_PLACEHOLDERS = {
    "project-name",
    "crate_name",
    "crate_type",
    "authors",
    "username",
}
RAW_MARKERS = ("{% raw %}", "{%raw%}", "{% endraw %}", "{%endraw%}")


def discover() -> list[Path]:
    if not TEMPLATES_DIR.is_dir():
        return []
    return sorted(
        path
        for path in TEMPLATES_DIR.iterdir()
        if path.is_dir() and (path / "cargo-generate.toml").is_file()
    )


def load_placeholders(template: Path) -> dict:
    try:
        with (template / "cargo-generate.toml").open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    placeholders = data.get("placeholders")
    return placeholders if isinstance(placeholders, dict) else {}


def collect_placeholder_names(template: Path) -> set[str]:
    """Declared placeholders, including conditional-only ones, plus builtins."""
    names = set(BUILTIN_PLACEHOLDERS)
    try:
        with (template / "cargo-generate.toml").open("rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return names
    placeholders = data.get("placeholders")
    if isinstance(placeholders, dict):
        names.update(placeholders)
    conditionals = data.get("conditional")
    if isinstance(conditionals, dict):
        for settings in conditionals.values():
            if isinstance(settings, dict) and isinstance(
                settings.get("placeholders"), dict
            ):
                names.update(settings["placeholders"])
    return names


def variants(placeholders: dict) -> list[tuple[str, dict[str, str]]]:
    """Default case plus one single-variable variation per alternative value."""
    cases: list[tuple[str, dict[str, str]]] = [("default", {})]
    for name, spec in placeholders.items():
        if not isinstance(spec, dict):
            continue
        kind = spec.get("type", "string")
        default = spec.get("default")
        if kind == "bool":
            alternative = "false" if default else "true"
            cases.append((f"{name}={alternative}", {name: alternative}))
        elif kind in {"string", "text"}:
            choices = spec.get("choices")
            if not isinstance(choices, list):
                continue
            for choice in choices:
                value = choice.get("value") if isinstance(choice, dict) else choice
                if value is None or value == default:
                    continue
                cases.append((f"{name}={value}", {name: str(value)}))
    return cases


def sanitize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "case"


def tail(text: str, lines: int = 25) -> str:
    rows = text.strip().splitlines()
    return "\n".join(rows[-lines:]) if rows else "(no output)"


def run_command(command: list[str], cwd: Path, timeout: int) -> tuple[int, str, float]:
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, time.monotonic() - started
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return (
            124,
            f"{output}\n(timed out after {timeout}s)",
            time.monotonic() - started,
        )
    except OSError as exc:
        return 127, str(exc), time.monotonic() - started


def check_output(root: Path, placeholders: set[str]) -> list[str]:
    """Problems that mean the generated project is not usable as-is."""
    problems: list[str] = []
    leftover = re.compile(
        r"\{\{-?\s*("
        + "|".join(re.escape(name) for name in sorted(placeholders))
        + r")\b"
    )
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if ".git" in rel.parts or path.is_dir():
            continue
        if path.suffix == ".liquid":
            problems.append(f"unrendered template file: {rel}")
            continue
        if path.name == "cargo-generate.toml":
            problems.append(f"template configuration leaked into output: {rel}")
            continue
        if path.suffix.lower() in BINARY_SUFFIXES or path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        # GitHub Actions expressions are legitimately left untouched, and literal
        # braces in the output (Helm charts, docs) are not Liquid leftovers.
        without_actions = re.sub(r"\$\{\{.*?\}\}", "", text, flags=re.DOTALL)
        if leftover.search(without_actions):
            problems.append(f"unrendered placeholder in: {rel}")
        if any(marker in text for marker in RAW_MARKERS):
            problems.append(f"unprocessed raw block in: {rel}")
    return problems


def run_case(
    template: Path,
    case: str,
    defines: dict[str, str],
    placeholders: set[str],
    args: argparse.Namespace,
    work_root: Path,
) -> dict:
    project = f"harness-{sanitize(template.name)}"
    if case != "default":
        project = f"{project}-{sanitize(case)}"
    case_dir = Path(tempfile.mkdtemp(prefix="case-", dir=work_root))

    command = [
        "cargo",
        "generate",
        "--path",
        str(template),
        "--name",
        project,
        "--silent",
        "--vcs",
        "none",
    ]
    for key, value in defines.items():
        command.extend(["--define", f"{key}={value}"])

    code, output, seconds = run_command(command, case_dir, args.timeout)
    if code:
        return {
            "case": case,
            "status": "FAIL",
            "step": "generate",
            "detail": tail(output),
            "dir": case_dir,
            "seconds": seconds,
        }

    generated = case_dir / project
    if not generated.is_dir():
        return {
            "case": case,
            "status": "FAIL",
            "step": "generate",
            "detail": f"expected directory missing: {generated}",
            "dir": case_dir,
            "seconds": seconds,
        }

    problems = check_output(generated, placeholders)
    if problems:
        return {
            "case": case,
            "status": "FAIL",
            "step": "output",
            "detail": "\n".join(problems),
            "dir": case_dir,
            "seconds": seconds,
        }

    if args.build and not (generated / "Cargo.toml").is_file():
        return {
            "case": case,
            "status": "PASS",
            "step": "",
            "detail": "",
            "note": "no Cargo.toml, build skipped",
            "dir": case_dir,
            "seconds": seconds,
        }

    if args.build:
        steps = [["cargo", "check", "--workspace"]]
        if not args.no_tests:
            # cargo test compiles the same targets as check, so skip the duplicate.
            steps = [["cargo", "test", "--workspace"]]
        for step in steps:
            code, output, spent = run_command(step, generated, args.timeout)
            seconds += spent
            if code:
                return {
                    "case": case,
                    "status": "FAIL",
                    "step": " ".join(step[1:]),
                    "detail": tail(output),
                    "dir": case_dir,
                    "seconds": seconds,
                }

    return {
        "case": case,
        "status": "PASS",
        "step": "",
        "detail": "",
        "dir": case_dir,
        "seconds": seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--template",
        action="append",
        default=[],
        metavar="NAME",
        help="template directory name; repeatable (default: all)",
    )
    parser.add_argument(
        "--matrix", action="store_true", help="also try placeholder alternatives"
    )
    parser.add_argument("--define", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, help="per-command timeout"
    )
    parser.add_argument(
        "--keep", action="store_true", help="keep generated projects on success too"
    )
    parser.add_argument(
        "--no-build", dest="build", action="store_false", help="generation only"
    )
    parser.add_argument(
        "--no-tests", action="store_true", help="cargo check without cargo test"
    )
    args = parser.parse_args()

    templates = discover()
    if args.template:
        known = {path.name: path for path in templates}
        unknown = [name for name in args.template if name not in known]
        if unknown:
            print(f"ERROR: unknown template(s): {', '.join(unknown)}", file=sys.stderr)
            return 2
        templates = [known[name] for name in args.template]

    if not templates:
        print("No templates found under templates/; nothing to harness.")
        return 0

    if not shutil.which("cargo-generate"):
        print(
            "ERROR: cargo-generate not found. Install it with "
            "`cargo install cargo-generate --locked`.",
            file=sys.stderr,
        )
        return 2
    if args.build and not shutil.which("cargo"):
        print(
            "ERROR: cargo not found; install Rust or pass --no-build.", file=sys.stderr
        )
        return 2

    for value in args.define:
        if "=" not in value or not value.split("=", 1)[0]:
            parser.error("--define must be of the form KEY=VALUE")
    extra_defines = dict(value.split("=", 1) for value in args.define)

    base = Path(os.environ.get("HARNESS_TMP", "/tmp/opencode"))
    if not base.is_dir() or not os.access(base, os.W_OK):
        base = Path(tempfile.gettempdir())
    work_root = Path(tempfile.mkdtemp(prefix="template-harness-", dir=base))

    results: list[tuple[str, dict]] = []
    failures = 0
    try:
        for template in templates:
            placeholders = load_placeholders(template)
            names = collect_placeholder_names(template)
            cases = variants(placeholders) if args.matrix else [("default", {})]
            for case, defines in cases:
                label = f"templates/{template.name} [{case}]"
                print(f"==> {label}", flush=True)
                merged = dict(extra_defines)
                merged.update(defines)
                result = run_case(template, case, merged, names, args, work_root)
                results.append((label, result))
                if result["status"] == "PASS":
                    suffix = f", {result['note']}" if result.get("note") else ""
                    print(f"    PASS ({result['seconds']:.1f}s{suffix})", flush=True)
                    if not args.keep:
                        shutil.rmtree(result["dir"], ignore_errors=True)
                else:
                    failures += 1
                    print(
                        f"    FAIL at {result['step']} ({result['seconds']:.1f}s)",
                        flush=True,
                    )
                    print(f"    kept: {result['dir']}", flush=True)
                    print("    " + result["detail"].replace("\n", "\n    "), flush=True)
    finally:
        if failures == 0 and not args.keep:
            shutil.rmtree(work_root, ignore_errors=True)

    print()
    for label, result in results:
        print(f"{result['status']} {label} ({result['seconds']:.1f}s)")
    print(f"\n{len(results) - failures} passed, {failures} failed")
    if failures:
        print(f"Generated projects kept under: {work_root}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
