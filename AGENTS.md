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
| `scripts/check_repo.py` | Repo consistency checks: menu ↔ directories ↔ index, symlink, links, artifacts. |
| `scripts/validate_all.py` | Runs the skill validator (optionally a smoke test) over every template. |
| `Makefile` | `check`, `validate`, `smoke` targets; the same commands CI runs. |
| `.github/workflows/ci.yml` | CI: repo checks, per-template validation matrix, smoke test on `main`. |
| `.agents/skills/cargo-generate-template-builder/` | Vendored authoring skill, including reference docs and helper scripts. |
| `.claude/skills/cargo-generate-template-builder` | Symlink to the skill above. |

## Commands

```bash
make check       # repo consistency + static validation of every template
make validate    # static validation only
make smoke       # real generation + build for every template
make help        # list targets
```

Equivalent scripts, when a single template or a CI-style call is needed:

```bash
# repo consistency (menu, index, symlink, links, artifacts)
python3 scripts/check_repo.py --strict

# every template, or just one as CI does per matrix entry
python3 scripts/validate_all.py --strict
python3 scripts/validate_all.py --strict --only <name>
python3 scripts/validate_all.py --strict --smoke --only <name>

# scaffold a new template (refuses to overwrite)
python3 .agents/skills/cargo-generate-template-builder/scripts/scaffold_template.py \
  ./templates/<name> --kind bin        # bin | lib | workspace
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
3. **Validate before committing.** `make check` must pass; it runs
   `check_repo.py --strict` and validates every template with `--strict`. Run
   `make smoke` when `cargo-generate` and Rust are available; if they are not,
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
11. **CI is the gate, not a suggestion.** Do not weaken, skip, or delete checks
    in `.github/workflows/ci.yml` to make a change pass, and do not add
    `continue-on-error` to validation steps. Fix the template or the check
    instead. Local `make check` and CI run the same scripts, so a green local run
    is the expected state before pushing.

## Definition of done

- [ ] template generates cleanly into an empty directory
- [ ] generated project builds or runs without manual repair
- [ ] `make check` passes
- [ ] `make smoke` passes when cargo-generate and Rust are available
- [ ] root `sub_templates` and `templates/README.md` list the template
- [ ] no generated artifacts, caches, or `__pycache__` are staged
- [ ] commit message states which templates changed and why
