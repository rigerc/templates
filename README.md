# templates

A monorepo of [cargo-generate](https://cargo-generate.github.io/cargo-generate/)
templates. One repository, one template per directory, one command to generate a
new project from any of them.

## Status

The monorepo skeleton is in place; no templates have been added yet. See
[the authoring guide](docs/adding-a-template.md) to create the first one.

## Layout

```text
.
├── cargo-generate.toml          # root menu: ordered sub_templates list
├── templates/                   # one self-contained template per directory
│   └── README.md                # template index and conventions
├── docs/
│   └── adding-a-template.md     # step-by-step authoring guide
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

## Validating

Static checks for every template, no Rust toolchain required:

```bash
for t in templates/*/; do
  python3 .agents/skills/cargo-generate-template-builder/scripts/validate_template.py "$t" --strict || exit 1
done
```

Real generation plus a build, for one template:

```bash
python3 .agents/skills/cargo-generate-template-builder/scripts/smoke_test.py ./templates/<name>
```

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
