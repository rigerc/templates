# templates

[![CI](https://github.com/rigerc/templates/actions/workflows/ci.yml/badge.svg)](https://github.com/rigerc/templates/actions/workflows/ci.yml)

A monorepo of [cargo-generate](https://cargo-generate.github.io/cargo-generate/)
templates. One repository, one template per directory, one command to generate a
new project from any of them.

## Status

The monorepo skeleton, local automation, and CI are in place; no templates have
been added yet. See [the authoring guide](docs/adding-a-template.md) to create the
first one.

## Layout

```text
.
├── cargo-generate.toml          # root menu: ordered sub_templates list
├── templates/                   # one self-contained template per directory
│   └── README.md                # template index and conventions
├── docs/
│   └── adding-a-template.md     # step-by-step authoring guide
├── scripts/
│   ├── check_repo.py            # repo consistency checks
│   └── validate_all.py          # runs the skill validator over every template
├── .github/workflows/ci.yml     # CI: checks, per-template validation, smoke test
├── Makefile                     # local entry points, identical to CI
├── AGENTS.md                    # rules for AI agents working in this repo
├── .agents/skills/              # vendored cargo-generate authoring skill
└── .claude/skills/              # symlink to the same skill for Claude clients
```

Each directory under `templates/` that contains a `cargo-generate.toml` is a
template. The root `cargo-generate.toml` lists them in `sub_templates` to control
the order of the interactive menu; the first entry is the default.

## Using a template

Interactive selection, ordered by the root menu:

```bash
cargo generate --git https://github.com/rigerc/templates.git
```

Pick a template explicitly, which is what CI and scripts should do:

```bash
cargo generate --git https://github.com/rigerc/templates.git templates/<name> --name my-project
```

Or from a local checkout (`--path` cannot be combined with `--git`):

```bash
cargo generate --path ./templates/<name> --name my-project
```

## Adding a template

```bash
python3 .agents/skills/cargo-generate-template-builder/scripts/scaffold_template.py \
  ./templates/<name> --kind bin
```

Then follow [docs/adding-a-template.md](docs/adding-a-template.md): configure
placeholders, write the Liquid files, append the path to `sub_templates`, and add
a row to the [template index](templates/README.md).

## Automation

Everything CI runs is available locally through the Makefile; the workflows call
the same scripts, so local and CI results cannot drift.

```bash
make check     # repo consistency + static validation of every template
make validate  # static validation only
make smoke     # real generation and build (needs cargo-generate and Rust)
make help      # list targets
```

| Command | What it does |
| --- | --- |
| `python3 scripts/check_repo.py --strict` | Verifies `sub_templates`, template directories, and the index table agree, the `.claude` symlink is intact, docs links resolve, and no generated artifacts are tracked. |
| `python3 scripts/validate_all.py --strict` | Runs the vendored validator against every directory under `templates/` that has a `cargo-generate.toml`. |
| `python3 scripts/validate_all.py --smoke` | Adds a real `cargo generate` run plus a build for each template. |
| `python3 scripts/validate_all.py --only <name>` | Restricts the run to one template, as CI does per matrix entry. |

### CI

`.github/workflows/ci.yml` runs on every push to `main`, every pull request, and
weekly on a schedule:

1. **Repo consistency** — `check_repo.py --strict` plus a compile check of the
   Python helpers.
2. **Validate** — a matrix over discovered templates, one job each, running the
   static validator with `--strict`. An empty `templates/` passes without
   spawning jobs.
3. **Smoke test** — the same matrix with real generation and a build. It runs on
   pushes to `main`, the weekly schedule, and manual dispatch with `smoke`
   enabled, and is skipped for pull requests to keep them fast.

Add a template and CI picks it up automatically; there is no matrix to edit.
Dependabot keeps the workflow actions current.

## Requirements

- `cargo-generate` v0.26.0 or newer (`cargo install cargo-generate --locked`)
- Rust and Cargo for Rust templates and for the smoke test
- Python 3.11+ for the helper scripts

## Agent support

The authoring skill is vendored at
`.agents/skills/cargo-generate-template-builder/` and symlinked into
`.claude/skills/` so Claude-based clients discover it too. Edit the skill only
when intentionally upgrading it; see [AGENTS.md](AGENTS.md) for the rules agents
follow in this repository.
