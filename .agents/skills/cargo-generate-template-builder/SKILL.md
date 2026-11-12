---
name: cargo-generate-template-builder
description: Create, extend, review, and debug cargo-generate project templates for Rust binaries, libraries, and workspaces. Use when the user asks for a cargo-generate.toml, Liquid placeholder substitution, dynamic template files, conditional paths, custom prompts, Rhai hooks, or validation of a cargo generate template. Includes local scaffold, lint, and smoke-test helpers; grounded in cargo-generate v0.26.0.
compatibility: Python 3.11+ is required for helper scripts; cargo-generate and Rust/Cargo are needed for real generation and build tests.
metadata:
  reference: cargo-generate v0.26.0
---

# Build cargo-generate templates

Build **the template repository or directory** that `cargo generate` consumes, not the expanded project. This skill was authored against cargo-generate v0.26.0 source/docs; use that as its compatibility baseline. Build for a different version only when the user specifies it; check feature introductions before adopting new syntax.

## 1. Understand the intended generated project

Determine: bin/lib/workspace or other, output directory structure, Rust edition and toolchain, required options, optional files, intended users, minimum cargo-generate version, CI/platform requirements, and whether Rhai is actually necessary. Proceed with sensible defaults for unspecified noncritical choices; clearly note them. A generated project should build without manual repair.

When starting from scratch, use the bundled starters rather than inventing config syntax (run scripts from the skill root, or supply their absolute paths):

```bash
python3 scripts/scaffold_template.py ./my-rust-template --kind bin
# or --kind lib or --kind workspace
```

The command refuses to overwrite an existing target. For an existing template, inspect before changing anything. Preserve user files and unrelated behavior.

## 2. Author the template

1. Add `cargo-generate.toml` in the template root, with `[template]` and any `[placeholders]`, `[conditional.'...']`, or `[hooks]` sections. Use the lowest version requirement that matches features used.
2. Render user-facing project values with Liquid: `{{ project-name }}` for package/directory naming and `{{ crate_name }}` for valid Rust identifiers. Avoid assuming the two are interchangeable.
3. Prefer `Cargo.toml.liquid`, `README.md.liquid`, or `src/lib.rs.liquid` to make rendered files explicit. The `.liquid` suffix is removed in generated output. Other text files can also be templated depending on include/exclude settings.
4. Define all custom values in `[placeholders]` and provide safe defaults where practical. Prefer lower_snake_case names; use `type`, `prompt`, `choices`, `default`, and `regex` as appropriate.
5. Implement optional files with `[conditional.'expression'] ignore = ["path/in/generated/output"]`; `ignore` removes files from output, whereas `exclude` only bypasses Liquid rendering. `ignore` has no wildcard support.
6. Use inline `{% if ... %}` for content changes and conditional `ignore` for full-file changes. For variants with materially different source layout, separate templates or subtemplates may be clearer.
7. Add hooks only if declarative Liquid/conditional configuration cannot express the required behavior. Rhai may mutate temporary template files, prompt, and set variables; never silently include arbitrary shell command execution. See [hooks and security](references/hooks-and-security.md).
8. Treat GitHub Actions `${{ ... }}` and other double-brace syntaxes as a conflict with Liquid. Prefer disabling Liquid processing for such files with `[template] exclude`, or wrap GitHub expressions in Liquid `{% raw %}...{% endraw %}` when Liquid processing is needed.

Consult [configuration and placeholders](references/configuration.md), [Liquid and project layout](references/liquid-and-layout.md), and [hooks and security](references/hooks-and-security.md) for exact syntax and caveats.

## 3. Validate, then generate for real

Run the bundled static linter (pure Python, no network):

```bash
python3 scripts/validate_template.py ./my-rust-template --strict
```

Resolve errors and warnings. The linter checks TOML, placeholder types/defaults, missing hooks, ignore/include/exclude usage, filename collisions, and some common Liquid mistakes. **Static lint is not a Liquid parser and cannot prove runtime behavior.**

When `cargo generate` and Cargo are installed, test expansion in an isolated temporary directory:

```bash
python3 scripts/smoke_test.py ./my-rust-template --define rust_edition=2021 --define include_ci=true
```

Smoke-test representative branches (e.g., `include_ci=true` and `false`, bin vs lib, edition changes). For workspaces, run `cargo check --workspace` and `cargo test --workspace` after expansion. Run `cargo fmt --check` where relevant. If Rust/cargo-generate are unavailable, report **not runtime-tested** instead of claiming the template works. See [validation matrix](references/testing-and-release.md).

For manual reproduction, run:

```bash
cargo generate --path ./my-rust-template --name demo-crate --silent --vcs none \
  --define rust_edition=2021 --define include_ci=true
```

Supply definitions/defaults for every custom placeholder in silent mode. Test from a working directory outside the template repository, to avoid nesting a generated crate in the template workspace.

## 4. Delivery contract

Deliver the editable template directory or an archive containing it; include a short README stating how to expand the template, example `--define` values, and any dependencies or hook permissions. Report: which files were created/edited, supported settings, validation results, exact commands executed, untested areas, and deliberate tradeoffs. Do not present an unexpanded `.liquid` file as a valid generated `Cargo.toml` or Rust source.

## Troubleshooting priorities

- **Empty substitution:** custom variable not defined or mistyped. Check `cargo-generate.toml` and `--define` names.
- **File unexpectedly present:** `exclude` is not `ignore`; `ignore` matches the path after `.liquid` removal.
- **Broken generated Rust:** inspect expanded output and run `cargo test`; `cargo-generate` formatting warnings do not fail generation.
- **Conditional mismatch:** global placeholders resolve before conditions; values defined inside conditional sections cannot control other conditionals.
- **Hook mismatch:** `init` precedes most variables, `pre` follows placeholder/conditional resolution, and `post` runs before final move; built-in `fmt` runs on the final destination.
- **CI workflow renders incorrectly:** protect `${{...}}` or bypass Liquid for workflow YAML.

## Source of truth

- Repository baseline: user-provided `cargo-generate` v0.26.0 (its `guide/src/templates/`, `guide/src/usage/`, `example-templates/`, and `tests/integration/`).
- Upstream documentation: https://cargo-generate.github.io/cargo-generate/
- Agent Skills format: https://agentskills.io/specification

Always prioritize observed behavior from an installed version's `cargo generate --help` and a real template expansion over assumptions from examples.
