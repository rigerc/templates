#!/usr/bin/env python3
"""Repository-level consistency checks for the template monorepo.

Verifies that the root menu, the template directories, the template index, the
vendored skill symlink, and relative documentation links all agree. Template
contents are checked separately by the skill's validator.

Usage:
    python3 scripts/check_repo.py [--strict]

Exits 1 on errors, or on warnings too when --strict is given.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "cargo-generate.toml"
TEMPLATES_DIR = ROOT / "templates"
INDEX = TEMPLATES_DIR / "README.md"
SKILL_DIR = ROOT / ".agents" / "skills" / "cargo-generate-template-builder"
CLAUDE_LINK = ROOT / ".claude" / "skills" / "cargo-generate-template-builder"
SKIP_DIRS = {".git", ".agents", ".claude", "target", "node_modules", "__pycache__"}

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")


class Report:
    def __init__(self) -> None:
        self.issues: list[tuple[str, str, str]] = []

    def add(self, level: str, where: object, message: str) -> None:
        self.issues.append((level, str(where), message))

    def error(self, where: object, message: str) -> None:
        self.add("ERROR", where, message)

    def warn(self, where: object, message: str) -> None:
        self.add("WARN", where, message)

    def emit(self) -> tuple[int, int]:
        order = {"ERROR": 0, "WARN": 1}
        for level, where, message in sorted(
            self.issues, key=lambda i: (i[1], order[i[0]], i[2])
        ):
            print(f"{level} {where}: {message}")
        errors = sum(1 for i in self.issues if i[0] == "ERROR")
        warnings = sum(1 for i in self.issues if i[0] == "WARN")
        print(f"\n{errors} error(s), {warnings} warning(s)")
        return errors, warnings


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_config(report: Report) -> list[str]:
    """Return the normalised sub_templates list, reporting problems."""
    if not CONFIG.is_file():
        report.error(rel(CONFIG), "missing root cargo-generate.toml")
        return []
    try:
        with CONFIG.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        report.error(rel(CONFIG), f"invalid TOML: {exc}")
        return []

    template = data.get("template")
    if not isinstance(template, dict):
        report.error(rel(CONFIG), "missing [template] table")
        return []

    entries = template.get("sub_templates")
    if entries is None:
        report.error(rel(CONFIG), "missing template.sub_templates list")
        return []
    if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
        report.error(rel(CONFIG), "template.sub_templates must be a list of strings")
        return []

    normalised: list[str] = []
    for entry in entries:
        clean = entry.strip().rstrip("/")
        if not clean:
            report.error(rel(CONFIG), "empty entry in template.sub_templates")
            continue
        if Path(clean).is_absolute() or ".." in Path(clean).parts:
            report.error(
                rel(CONFIG), f"sub_templates entry must be relative: {entry!r}"
            )
            continue
        if not clean.startswith("templates/"):
            report.error(
                rel(CONFIG),
                f"sub_templates entry must live under templates/: {entry!r}",
            )
            continue
        normalised.append(clean)

    duplicates = {name for name in normalised if normalised.count(name) > 1}
    for duplicate in sorted(duplicates):
        report.error(rel(CONFIG), f"duplicate sub_templates entry: {duplicate!r}")

    return normalised


def discover_templates(report: Report) -> list[str]:
    if not TEMPLATES_DIR.is_dir():
        report.error(rel(TEMPLATES_DIR), "missing templates/ directory")
        return []
    found = []
    for path in sorted(TEMPLATES_DIR.iterdir()):
        if not path.is_dir() or path.name in SKIP_DIRS or path.name.startswith("."):
            continue
        if (path / "cargo-generate.toml").is_file():
            found.append(f"templates/{path.name}")
        else:
            report.warn(
                rel(path),
                "directory has no cargo-generate.toml; not a template, will be ignored",
            )
    return found


def check_menu(entries: list[str], discovered: list[str], report: Report) -> None:
    for entry in entries:
        path = ROOT / entry
        if not path.is_dir():
            report.error(rel(CONFIG), f"sub_templates entry does not exist: {entry!r}")
        elif not (path / "cargo-generate.toml").is_file():
            report.error(
                rel(CONFIG),
                f"sub_templates entry has no cargo-generate.toml: {entry!r}",
            )

    for missing in sorted(set(discovered) - set(entries)):
        report.error(
            rel(CONFIG),
            f"template {missing!r} exists but is not listed in sub_templates",
        )


def index_names(text: str) -> list[str]:
    """Template names from the 'Available templates' table in the index."""
    names: list[str] = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.strip().lower() == "## available templates"
            continue
        if not in_section:
            continue
        match = TABLE_ROW.match(line.strip())
        if not match:
            continue
        first = match.group(1).split("|", 1)[0].strip()
        if not first or set(first) <= set("-: "):
            continue
        if first.lower() == "template":
            continue
        link = re.match(r"\[([^\]]+)\]", first)
        name = (link.group(1) if link else first).strip("`* ")
        if not name or name.startswith("_"):
            continue
        names.append(name)
    return names


def check_index(discovered: list[str], report: Report) -> None:
    if not INDEX.is_file():
        report.error(rel(INDEX), "missing template index")
        return
    listed = index_names(INDEX.read_text(encoding="utf-8"))
    expected = {Path(entry).name for entry in discovered}
    for name in sorted(expected - set(listed)):
        report.error(rel(INDEX), f"template {name!r} is missing from the index table")
    for name in sorted(set(listed) - expected):
        report.error(rel(INDEX), f"index table lists unknown template {name!r}")
    duplicates = {name for name in listed if listed.count(name) > 1}
    for duplicate in sorted(duplicates):
        report.error(rel(INDEX), f"duplicate index row for {duplicate!r}")


def check_symlink(report: Report) -> None:
    if not SKILL_DIR.is_dir():
        report.error(rel(SKILL_DIR), "vendored skill directory is missing")
        return
    if not CLAUDE_LINK.exists() and not CLAUDE_LINK.is_symlink():
        report.error(rel(CLAUDE_LINK), "missing .claude skill symlink")
        return
    if not CLAUDE_LINK.is_symlink():
        report.warn(
            rel(CLAUDE_LINK), "expected a symlink, found a regular file or directory"
        )
        return
    target = (CLAUDE_LINK.parent / CLAUDE_LINK.readlink()).resolve()
    if target != SKILL_DIR.resolve():
        report.error(
            rel(CLAUDE_LINK), f"symlink points to {target}, expected {SKILL_DIR}"
        )
    elif not target.exists():
        report.error(rel(CLAUDE_LINK), "symlink target does not exist")


def check_links(report: Report) -> None:
    docs = [ROOT / "README.md", ROOT / "AGENTS.md", INDEX]
    docs.extend(sorted((ROOT / "docs").glob("*.md")))
    for doc in docs:
        if not doc.is_file():
            continue
        for match in MD_LINK.finditer(doc.read_text(encoding="utf-8")):
            target = match.group(1)
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path = (doc.parent / target.split("#", 1)[0]).resolve()
            if not path.exists():
                report.error(rel(doc), f"broken relative link: {target}")


def check_artifacts(report: Report) -> None:
    """Tracked artifacts always fail; untracked caches only under templates/."""
    try:
        tracked = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        tracked = []

    for name in tracked:
        path = Path(name)
        if (
            path.name in {"__pycache__", ".DS_Store"}
            or path.suffix in {".pyc", ".pyo"}
            or "target" in path.parts
        ):
            report.error(name, "generated artifact is tracked; remove it")

    if not TEMPLATES_DIR.is_dir():
        return
    for pattern in ("__pycache__", "*.pyc", "*.pyo", ".DS_Store"):
        for path in TEMPLATES_DIR.rglob(pattern):
            report.error(rel(path), "generated artifact inside templates/; remove it")
    for path in TEMPLATES_DIR.rglob("target"):
        if path.is_dir():
            report.error(rel(path), "build output directory inside templates/")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="treat warnings as errors"
    )
    args = parser.parse_args()

    report = Report()
    entries = load_config(report)
    discovered = discover_templates(report)
    check_menu(entries, discovered, report)
    check_index(discovered, report)
    check_symlink(report)
    check_links(report)
    check_artifacts(report)

    errors, warnings = report.emit()
    if errors or (args.strict and warnings):
        return 1
    print("PASS: repository structure is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
