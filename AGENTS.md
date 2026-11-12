# AGENTS.md

Instructions for AI agents and humans working in this repository. Read this
before creating, editing, or reviewing a template.

## What this repository is

A monorepo of [cargo-generate](https://cargo-generate.github.io/cargo-generate/)
templates. Each directory under `templates/` is one self-contained template that
`cargo generate` expands into a new project. The repository is not itself a
generated project and never contains generated output.

## Map

| Path | Role |
| --- | --- |
| `cargo-generate.toml` | Root menu. `sub_templates` lists template paths in menu order. |
| `templates/<name>/` | One template: its own `cargo-generate.toml`, placeholders, files. |
| `templates/README.md` | Human-readable index; keep it in sync with `sub_templates`. |
| `docs/adding-a-template.md` | Authoring workflow and checklist. |
| `.agents/skills/cargo-generate-template-builder/` | Vendored authoring skill, including reference docs and helper scripts. |
| `.claude/skills/cargo-generate-template-builder` | Symlink to the skill above. |

## Commands

```bash
# scaffold a new template (refuses to overwrite)
python3 .agents/skills/cargo-generate-template-builder/scripts/scaffold_template.py \
  ./templates/<name> --kind bin        # bin | lib | workspace

# static validation, required before every commit
python3 .agents/skills/cargo-generate-template-builder/scripts/validate_template.py \
  ./templates/<name> --strict

# real generation + build, requires cargo-generate and Rust
python3 .agents/skills/cargo-generate-template-builder/scripts/smoke_test.py \
  ./templates/<name>

# validate every template
for t in templates/*/; do
  python3 .agents/skills/cargo-generate-template-builder/scripts/validate_template.py "$t" --strict || exit 1
done
```

Use `cargo generate --path ./templates/<name> --name demo --silent` for manual
generation; `--path` and `--git` must never be combined.

## Rules

1. **Templates are self-contained.** Never read from a sibling template or from
   the repository root. `cargo-generate` does not merge parent directories; copy
   shared content in or produce it with a hook.
2. **Update both indexes.** Adding, renaming, or removing a template means
   editing `sub_templates` in the root `cargo-generate.toml` *and* the table in
   `templates/README.md` in the same commit.
3. **Validate before committing.** `validate_template.py --strict` must pass. Run
   `smoke_test.py` when `cargo-generate` and Rust are available; if they are not,
   say so instead of claiming a runtime test passed.
4. **Generate outside the repo.** Use a temporary directory (for example
   `/tmp/opencode/...`); never commit an expanded project or a `target/`.
5. **Declare every variable.** Custom values belong in `[placeholders]` with a
   default, so generation is deterministic and unattended. Do not redeclare the
   builtins `project-name` or `crate_name`.
6. **Respect `ignore` vs `exclude`.** `ignore` drops files from the output and
   takes exact paths with no wildcards; `exclude` only disables Liquid rendering.
   `ignore` paths use generated names, `include`/`exclude` patterns use
   pre-rename names such as `README.md.liquid`.
7. **Hooks are a last resort.** Use Rhai only when declarative configuration
   cannot express the behavior, and never add silent shell execution.
8. **Do not edit the vendored skill casually.** `.agents/skills/` is an imported
   package; change it only when the task is to upgrade the skill, and keep the
   `.claude/skills` symlink intact (git mode `120000`). Do not replace the
   symlink with a copy.
9. **Naming.** Template directories are kebab-case without a `-template` suffix;
   the directory name is the CLI argument users type.
10. **Docs stay true.** If behavior, paths, or commands change, update
    `README.md`, `templates/README.md`, and this file in the same change.

## Definition of done

- [ ] template generates cleanly into an empty directory
- [ ] generated project builds or runs without manual repair
- [ ] `validate_template.py --strict` passes
- [ ] root `sub_templates` and `templates/README.md` list the template
- [ ] no generated artifacts, caches, or `__pycache__` are staged
- [ ] commit message states which templates changed and why
