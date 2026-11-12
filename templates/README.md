# Template index

One directory per template. Each directory is a complete, self-contained
[cargo-generate](https://cargo-generate.github.io/cargo-generate/) template:
it holds its own `cargo-generate.toml`, its own placeholders, conditionals and
hooks, and the files that get rendered into the generated project.

No templates exist yet. Add the first one with
[the authoring guide](../docs/adding-a-template.md).

## Available templates

| Template | Purpose | Generate |
| --- | --- | --- |
| _none yet_ | | |

When you add a template, add a row here and keep the table sorted by name.

## Conventions

- **Directory name** — kebab-case, no `-template` suffix (`templates/rust-cli/`,
  not `templates/rust-cli-template/`). The directory name is what users type on
  the command line.
- **Self-contained** — a template must not read files from a sibling template or
  from the repository root. `cargo-generate` does not merge parent directories,
  so anything shared has to be copied in or produced by a hook.
- **Root config stays in sync** — every directory listed here must also appear
  in `sub_templates` in the root `cargo-generate.toml`, and vice versa.
- **No generated output** — never commit an expanded project; generate into a
  temporary directory outside the repository.

## Layout of a template

```text
templates/<name>/
├── cargo-generate.toml     # required: template root marker + configuration
├── README.md.liquid        # optional: rendered with Liquid, .liquid suffix dropped
├── src/                    # files copied or rendered into the output
└── .github/workflows/      # optional; exclude or wrap `${{ }}` in raw blocks
```

## Selecting a template

Interactive menu, in `sub_templates` order:

```bash
cargo generate --git https://github.com/rigerc/templates.git
```

Explicit selection, for scripts and CI:

```bash
cargo generate --git https://github.com/rigerc/templates.git templates/<name> --name my-project
```

From a local checkout (`--path` and `--git` cannot be combined):

```bash
cargo generate --path ./templates/<name> --name my-project
```
