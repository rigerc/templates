# Adding a template

A template is a directory that `cargo generate` expands into a new project. The
directory itself is never the output: its files are copied (and optionally
rendered with Liquid) into a destination folder.

Reference material ships with the agent skill in
`.agents/skills/cargo-generate-template-builder/references/`; the summary below
is enough for the common cases.

## 1. Scaffold the directory

```bash
python3 .agents/skills/cargo-generate-template-builder/scripts/scaffold_template.py \
  ./templates/<name> --kind bin    # or --kind lib, --kind workspace
```

The helper copies a working starter and refuses to overwrite an existing
directory. Starting from scratch by hand is fine too; the only required file is
`cargo-generate.toml` at the template root.

## 2. Configure `cargo-generate.toml`

```toml
[template]
cargo_generate_version = ">=0.26.0"

[placeholders]
include_ci = { type = "bool", prompt = "Include CI workflow?", default = true }

[conditional.'include_ci == false']
ignore = [".github/workflows/ci.yml"]
```

Rules that matter most:

- `ignore` removes files from the output; `exclude` only skips Liquid rendering.
  `ignore` takes exact paths and supports **no wildcards**.
- Spell `ignore` paths as the **generated** name (`README.md`), but `include` and
  `exclude` patterns as the **pre-rename** name (`README.md.liquid`).
- Never set `include` and `exclude` together.
- Declare custom values in `[placeholders]` and give them defaults so automated
  generation is deterministic.
- `project-name` and `crate_name` are builtins: the kebab-case directory name and
  its snake_case Rust form. Do not redeclare them.
- Use hooks (Rhai) only when declarative configuration cannot express the
  behavior, and never add silent shell execution.

## 3. Write the files

- Append `.liquid` to any text file that needs Liquid rendering; the suffix is
  dropped in the output (`README.md.liquid` → `README.md`).
- Use `{{ project-name }}` for the project/package name and
  `{{ crate_name }}` where a Rust identifier is required.
- Wrap GitHub Actions expressions (`${{ ... }}`) in
  `{% raw %}...{% endraw %}`, or add the file to `[template] exclude`.
- The generated project should build or run without manual repair.

## 4. Register the template

1. Append `"templates/<name>"` to `sub_templates` in the root
   `cargo-generate.toml`, keeping the most-used templates first.
2. Add a row to the table in `templates/README.md`.

## 5. Validate before committing

Repo consistency and static validation of every template, no network or Rust
toolchain needed:

```bash
make check
```

Real generation and a build, requires `cargo-generate` (v0.26.0+) and Rust:

```bash
make smoke
```

Both must pass before the template is pushed. Generated projects belong in a
temporary directory, never in this repository. CI runs the same scripts and
discovers new templates automatically, so no workflow edit is needed.

## Checklist

- [ ] `templates/<name>/cargo-generate.toml` exists and parses
- [ ] every custom variable is declared with a sensible default
- [ ] `.liquid` files render to the intended output names
- [ ] `ignore`/`exclude` paths use the correct pre- or post-rename form
- [ ] generated project builds (or the non-Rust equivalent runs) unattended
- [ ] root `sub_templates` updated
- [ ] `templates/README.md` table updated
- [ ] `make check` passes
