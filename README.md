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
│   ├── harness.py               # local generate/build/test harness
│   └── validate_all.py          # runs the skill validator over every template
├── .githooks/pre-commit         # runs make check before each commit
├── .github/workflows/ci.yml     # CI: checks, per-template validation, harness
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
make check          # repo consistency + static validation (runs in pre-commit)
make validate       # static validation only
make harness        # generate, build, and test every template
make harness-matrix # also generate each placeholder alternative
make hooks          # enable the tracked pre-commit hook
make help           # list targets
```

| Command | What it does |
| --- | --- |
| `python3 scripts/check_repo.py --strict` | Verifies `sub_templates`, template directories, and the index table agree, the `.claude` symlink and pre-commit hook are intact, docs links resolve, and no generated artifacts are tracked. |
| `python3 scripts/validate_all.py --strict` | Runs the vendored validator against every directory under `templates/` that has a `cargo-generate.toml`. |
| `python3 scripts/harness.py` | Generates each template into a throwaway directory, rejects unrendered Liquid or leaked `cargo-generate.toml`, then runs `cargo check` and `cargo test`. |
| `python3 scripts/harness.py --matrix` | Adds one generation per non-default placeholder value. |
| `python3 scripts/harness.py --template <name> --no-build` | Generation-only run for a single template. |

Failed harness cases keep their working directory and print the path; `--keep`
keeps successful ones too.

### Git hooks

```bash
make hooks
```

Points `core.hooksPath` at `.githooks/`. The pre-commit hook runs `make check`
(repo consistency plus static validation) and takes about a second. It does not
run the harness, so commits stay fast; run `make harness` before pushing template
changes. Hooks are per clone and are not installed automatically.

### CI

`.github/workflows/ci.yml` runs on every push to `main`, every pull request, and
weekly on a schedule:

1. **Repo consistency** — `check_repo.py --strict` plus a compile check of the
   Python helpers.
2. **Validate** — a matrix over discovered templates, one job each, running the
   static validator with `--strict`. An empty `templates/` passes without
   spawning jobs.
3. **Harness** — the same matrix with real generation, `cargo check`, and
   `cargo test`. It runs on pushes to `main`, the weekly schedule, and manual
   dispatch with `smoke` enabled, and is skipped for pull requests to keep them
   fast.

Add a template and CI picks it up automatically; there is no matrix to edit.
Dependabot keeps the workflow actions current.

## Requirements

- `cargo-generate` v0.26.0 or newer (`cargo install cargo-generate --locked`)
- Rust and Cargo for Rust templates and for the harness
- Python 3.11+ for the helper scripts
- `make hooks` once per clone to enable the pre-commit hook

## Agent support

The authoring skill is vendored at
`.agents/skills/cargo-generate-template-builder/` and symlinked into
`.claude/skills/` so Claude-based clients discover it too. Edit the skill only
when intentionally upgrading it; see [AGENTS.md](AGENTS.md) for the rules agents
follow in this repository.
