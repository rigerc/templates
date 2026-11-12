#!/usr/bin/env python3
"""Static, conservative cargo-generate template linter (does not run Liquid/Rhai)."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath
import re
import sys
import tomllib

TYPES = {"string", "text", "editor", "bool", "array"}
BUILTINS = {
    "project-name", "crate_name", "crate_type", "authors", "username", "os-arch",
    "within_cargo_project", "is_init", "forloop", "tablerowloop", "empty", "blank",
    "nil", "null", "true", "false", "continue", "break",
}
VAR = re.compile(r"^[a-zA-Z_][\w-]*")
OUTPUT = re.compile(r"\{\{(.*?)\}\}", re.DOTALL)
TAG = re.compile(r"\{%\s*(.*?)\s*%\}", re.DOTALL)
RAW_BLOCK = re.compile(r"\{%\s*(raw|comment)\s*%\}.*?\{%\s*end\1\s*%\}", re.DOTALL)
PAIRS = {"if": "endif", "unless": "endunless", "for": "endfor", "case": "endcase", "capture": "endcapture", "tablerow": "endtablerow"}
CLOSING = set(PAIRS.values())


@dataclass(frozen=True)
class Diagnostic:
    level: str
    location: str
    message: str


class Checker:
    def __init__(self, root: Path):
        self.root = root
        self.diagnostics: list[Diagnostic] = []
        self.placeholder_names: set[str] = set(BUILTINS)
        self.config: dict = {}

    def add(self, level: str, location: str, message: str) -> None:
        self.diagnostics.append(Diagnostic(level, location, message))

    def check(self) -> None:
        if not self.root.is_dir():
            self.add("ERROR", ".", "Not a directory")
            return
        config_file = self.root / "cargo-generate.toml"
        if not config_file.is_file():
            self.add("ERROR", "cargo-generate.toml", "Required template config is missing")
            return
        try:
            self.config = tomllib.loads(config_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
            self.add("ERROR", "cargo-generate.toml", f"Invalid TOML: {exc}")
            return
        if not isinstance(self.config, dict):
            self.add("ERROR", "cargo-generate.toml", "Expected TOML table")
            return

        self.check_config()
        files = []
        for path in sorted(self.root.rglob("*")):
            rel = path.relative_to(self.root).as_posix()
            if ".git" in path.relative_to(self.root).parts:
                continue
            if path.is_symlink():
                self.add("ERROR", rel, "Symlinks must be reviewed; may escape the template directory")
                continue
            if path.is_file():
                files.append(path)
        self.check_filepaths(files)
        for path in files:
            rel = path.relative_to(self.root).as_posix()
            if rel == "cargo-generate.toml" or path.suffix == ".rhai":
                continue
            if not self.should_render(rel):
                continue
            try:
                body = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue  # binary asset
            except OSError as exc:
                self.add("ERROR", rel, f"Unable to read: {exc}")
                continue
            self.check_liquid(body, rel)
        self.check_ignores(files)

    def check_config(self) -> None:
        config = self.config
        template = config.get("template", {})
        if not isinstance(template, dict):
            self.add("ERROR", "[template]", "Must be a TOML table")
            template = {}
        if "cargo_generate_version" not in template:
            self.add("WARN", "[template]", "Add a tested minimum cargo_generate_version")
        elif not isinstance(template["cargo_generate_version"], str):
            self.add("ERROR", "[template]", "cargo_generate_version must be a version requirement string")
        if "fmt" in template and not isinstance(template["fmt"], bool):
            self.add("ERROR", "[template]", "fmt must be boolean")
        self.check_file_lists(template, "[template]")
        for section_name, section in (("[placeholders]", config.get("placeholders", {})),):
            self.check_placeholders(section, section_name)
        conditions = config.get("conditional", {})
        if not isinstance(conditions, dict):
            self.add("ERROR", "[conditional]", "Must be a TOML table")
            conditions = {}
        for condition, section in conditions.items():
            location = f"[conditional.{condition!r}]"
            if not isinstance(section, dict):
                self.add("ERROR", location, "Must be a TOML table")
                continue
            self.check_file_lists(section, location)
            self.check_placeholders(section.get("placeholders", {}), location + ".placeholders")
        self.check_hooks(config.get("hooks", {}))

    def check_file_lists(self, settings: dict, location: str) -> None:
        if "include" in settings and "exclude" in settings:
            self.add("ERROR", location, "Do not combine include and exclude: include takes precedence")
        for key in ("include", "exclude", "ignore", "sub_templates"):
            if key not in settings:
                continue
            value = settings[key]
            if not isinstance(value, list) or any(not isinstance(v, str) for v in value):
                self.add("ERROR", location, f"{key} must be an array of strings")
                continue
            if key == "ignore":
                for item in value:
                    if any(c in item for c in "*?["):
                        self.add("ERROR", location, f"ignore does not support glob patterns: {item!r}")
                    if not self.safe_relative_path(item):
                        self.add("ERROR", location, f"ignore path escapes template root: {item!r}")

    @staticmethod
    def safe_relative_path(value: str) -> bool:
        path = PurePosixPath(value.replace("\\", "/"))
        return bool(value) and not path.is_absolute() and not any(part == ".." for part in path.parts)

    def check_placeholders(self, data: object, location: str) -> None:
        if not isinstance(data, dict):
            self.add("ERROR", location, "Must be a TOML table")
            return
        for key, spec in data.items():
            where = f"{location}.{key}"
            self.placeholder_names.add(key)
            if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
                self.add("WARN", where, "Prefer lowercase snake_case placeholder keys")
            if key in BUILTINS:
                self.add("WARN", where, "Builtin variable shadows a standard cargo-generate value")
            if not isinstance(spec, dict):
                self.add("ERROR", where, "Expected placeholder table with type and prompt")
                continue
            typ = spec.get("type")
            if typ not in TYPES:
                self.add("ERROR", where, f"Unknown/missing placeholder type {typ!r}; use {sorted(TYPES)}")
                continue
            if not isinstance(spec.get("prompt"), str) or not spec["prompt"].strip():
                self.add("ERROR", where, "Missing/non-string prompt")
            default = spec.get("default")
            if "default" not in spec:
                self.add("WARN", where, "No default; silent generation will require --define or other value")
            elif typ == "bool" and not isinstance(default, bool):
                self.add("ERROR", where, "bool default must be true/false")
            elif typ == "array" and (not isinstance(default, list) or not all(isinstance(v, str) for v in default)):
                self.add("ERROR", where, "array default must be an array of strings")
            elif typ in ("string", "text", "editor") and not isinstance(default, str):
                self.add("ERROR", where, f"{typ} default must be a string")
            choices = spec.get("choices")
            if choices is not None:
                if typ == "bool":
                    self.add("WARN", where, "bool placeholders normally do not need choices")
                if not isinstance(choices, list):
                    self.add("ERROR", where, "choices must be an array")
                    continue
                parsed_choices: set[str] = set()
                for value in choices:
                    if isinstance(value, str):
                        parsed_choices.add(value)
                    elif isinstance(value, dict) and isinstance(value.get("value"), str) and ("label" not in value or isinstance(value["label"], str)):
                        parsed_choices.add(value["value"])
                    else:
                        self.add("ERROR", where, "Each choice must be a string or {value, optional label} table")
                if "default" in spec:
                    selected = default if typ == "array" and isinstance(default, list) else [default]
                    for v in selected:
                        if isinstance(v, str) and v not in parsed_choices:
                            self.add("ERROR", where, f"Default {v!r} is absent from choices")
            if "regex" in spec:
                if typ not in ("string", "text", "editor") or not isinstance(spec["regex"], str):
                    self.add("ERROR", where, "regex requires a string-like placeholder and string pattern")
                else:
                    try:
                        re.compile(spec["regex"])
                    except re.error as exc:
                        self.add("WARN", where, f"Regex may be invalid: {exc}")

    def check_hooks(self, hooks: object) -> None:
        if not isinstance(hooks, dict):
            self.add("ERROR", "[hooks]", "Must be a TOML table")
            return
        for phase, paths in hooks.items():
            location = f"[hooks].{phase}"
            if phase not in ("init", "pre", "post"):
                self.add("WARN", location, "Unknown hook phase")
            if not isinstance(paths, list) or not all(isinstance(x, str) for x in paths):
                self.add("ERROR", location, "Hooks must be arrays of script paths")
                continue
            for path in paths:
                if path == "fmt":
                    if phase != "post":
                        self.add("ERROR", location, "Built-in fmt hook is only valid for post")
                    continue
                if not self.safe_relative_path(path):
                    self.add("ERROR", location, f"Unsafe hook path: {path!r}")
                    continue
                script = self.root / path
                if not script.is_file():
                    self.add("ERROR", location, f"Hook script not found: {path}")
                    continue
                if script.suffix != ".rhai":
                    self.add("WARN", location, f"Hook is usually a .rhai file: {path}")
                try:
                    body = script.read_text(encoding="utf-8")
                    if "system::command" in body:
                        self.add("WARN", path, "Hook runs shell commands; review explicit consent/security implications")
                except (OSError, UnicodeError) as exc:
                    self.add("ERROR", path, f"Could not inspect hook: {exc}")

    def should_render(self, rel: str) -> bool:
        template = self.config.get("template", {})
        if not isinstance(template, dict):
            return True
        if "include" in template and isinstance(template["include"], list):
            return any(isinstance(p, str) and fnmatch(rel, p) for p in template["include"])
        if "exclude" in template and isinstance(template["exclude"], list):
            return not any(isinstance(p, str) and fnmatch(rel, p) for p in template["exclude"])
        return True

    def check_filepaths(self, files: list[Path]) -> None:
        outputs: dict[str, str] = {}
        for file in files:
            rel = file.relative_to(self.root).as_posix()
            if rel == "cargo-generate.toml":
                continue
            target = rel[:-7] if rel.endswith(".liquid") else rel
            if target in outputs:
                self.add("ERROR", rel, f"Output filename collides with {outputs[target]!r} after .liquid stripping")
            outputs[target] = rel
            self.check_liquid(rel, rel + " (path)", check_tags=False)
        template_settings = self.config.get("template", {})
        has_subtemplates = isinstance(template_settings, dict) and bool(template_settings.get("sub_templates"))
        if "Cargo.toml" not in outputs and not has_subtemplates:
            self.add("WARN", ".", "No root Cargo.toml(.liquid); check if this is intended for a non-crate template")

    def check_liquid(self, body: str, location: str, check_tags: bool = True) -> None:
        # Remove regions that Liquid deliberately leaves untouched.
        stripped = RAW_BLOCK.sub("", body)
        if "${{" in stripped:
            self.add("WARN", location, "Found '${{': GitHub Actions expressions need Liquid raw blocks or exclude")
        if stripped.count("{{") != stripped.count("}}"):
            self.add("WARN", location, "Mismatched Liquid output delimiters '{{' and '}}'")
        if stripped.count("{%") != stripped.count("%}"):
            self.add("WARN", location, "Mismatched Liquid tag delimiters '{%' and '%}'")

        local_vars: set[str] = set()
        tags = list(TAG.finditer(stripped)) if check_tags else []
        for match in tags:
            body_text = match.group(1).strip().lstrip("- ").rstrip("- ")
            for_match = re.match(r"(?:for|tablerow)\s+([a-zA-Z_]\w*)\s+in\s+([a-zA-Z_][\w-]*)", body_text)
            if for_match:
                local_vars.add(for_match.group(1))
                self.report_variable(for_match.group(2), location, local_vars)
            assign_match = re.match(r"assign\s+([a-zA-Z_]\w*)\s*=", body_text)
            if assign_match:
                local_vars.add(assign_match.group(1))
            capture_match = re.match(r"capture\s+([a-zA-Z_]\w*)", body_text)
            if capture_match:
                local_vars.add(capture_match.group(1))
        for expression in OUTPUT.finditer(stripped):
            raw_expr = expression.group(1).strip().lstrip("-").strip()
            if not raw_expr or raw_expr[0] in ('"', "'", "[", "(") or raw_expr[0].isdigit():
                continue
            first = raw_expr.split("|", 1)[0].strip()
            variable = VAR.match(first)
            if variable:
                self.report_variable(variable.group(), location, local_vars)

        if check_tags:
            stack: list[str] = []
            for tag in tags:
                text = tag.group(1).strip().lstrip("- ").rstrip("- ")
                name = text.split(maxsplit=1)[0] if text else ""
                if name in PAIRS:
                    stack.append(name)
                elif name in CLOSING:
                    if not stack or PAIRS[stack[-1]] != name:
                        self.add("WARN", location, f"Possibly mismatched Liquid tag: {name}")
                    else:
                        stack.pop()
            if stack:
                self.add("WARN", location, f"Unclosed Liquid block(s): {', '.join(stack)}")

    def report_variable(self, variable: str, location: str, locals_: set[str]) -> None:
        if variable not in self.placeholder_names and variable not in locals_:
            self.add("WARN", location, f"Potentially undefined Liquid variable: {variable}")

    def check_ignores(self, files: list[Path]) -> None:
        paths = [p.relative_to(self.root).as_posix() for p in files]
        generated = [p[:-7] if p.endswith(".liquid") else p for p in paths]
        sections = [self.config.get("template", {})]
        conditions = self.config.get("conditional", {})
        if isinstance(conditions, dict):
            sections.extend(section for section in conditions.values() if isinstance(section, dict))
        for section in sections:
            if not isinstance(section, dict):
                continue
            for ignore in section.get("ignore", []) if isinstance(section.get("ignore", []), list) else []:
                if not isinstance(ignore, str):
                    continue
                item = ignore.rstrip("/")
                if item not in generated and not any(name.startswith(item + "/") for name in generated):
                    self.add("WARN", "ignore", f"Path not found after .liquid stripping: {ignore!r}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Directory containing cargo-generate.toml")
    parser.add_argument("--strict", action="store_true", help="Warnings also cause a nonzero exit")
    args = parser.parse_args()
    checker = Checker(args.template.expanduser().resolve())
    checker.check()
    for diag in checker.diagnostics:
        print(f"{diag.level}: {diag.location}: {diag.message}")
    errors = sum(d.level == "ERROR" for d in checker.diagnostics)
    warnings = sum(d.level == "WARN" for d in checker.diagnostics)
    print(f"Static validation: {errors} error(s), {warnings} warning(s)")
    if not errors and not warnings:
        print("PASS: static checks (not a runtime generation test)")
    return 1 if errors or (warnings and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
