# cargo-generate.toml reference (baseline v0.26.0)

A template root can be local (`cargo generate --path ./template`) or hosted in Git (`cargo generate --git https://...`). A template lives in its own directory; the generated project is the expanded output.

## Minimal configuration

```toml
[template]
cargo_generate_version = ">=0.26.0"

[placeholders]
rust_edition = { type = "string", prompt = "Rust edition?", choices = ["2021", "2024"], default = "2021" }
include_ci = { type = "bool", prompt = "Include CI workflow?", default = true }

[conditional.'include_ci == false']
ignore = [".github/workflows/ci.yml"]
```

Minimum version is a Cargo-compatible version requirement; avoid unnecessarily raising it. Version 0.26.0 adds built-in formatting and named `fmt` hook, among other changes.

## `[template]` options

| Option | Behavior |
| --- | --- |
| `cargo_generate_version` | Require a version of the cargo-generate CLI. |
| `include = ["..."]` | Gitignore-style patterns selecting files whose **contents** are Liquid-rendered. |
| `exclude = ["..."]` | Gitignore-style patterns selecting files whose contents are **not** Liquid-rendered; they are still copied. |
| `ignore = ["file", "dir"]` | Copy neither file nor directory. Exact file/folder paths only; **no wildcards**. |
| `fmt = false` | Disable the built-in Rust formatter (v0.26+); `--no-fmt` from caller takes precedence. |
| `sub_templates = ["folder1", "folder2"]` | Advertise subtemplates and their selection order. |

**Do not set `include` and `exclude` together.** The engine gives `include` precedence and warns. For an ignore path, spell the generated filename (`README.md`), not `README.md.liquid`. For `include` or `exclude`, match the **pre-rename** filename (`README.md.liquid`). `cargo-generate.toml` is internal configuration, not a project manifest.

## Placeholder definition

```toml
[placeholders]
service = { type = "string", prompt = "Service type?", choices = ["http", "cli"], default = "cli" }
use_metrics = { type = "bool", prompt = "Add metrics?", default = false }
features = { type = "array", prompt = "Select features?", choices = ["serde", "logging"], default = ["serde"] }
about = { type = "text", prompt = "Project description?", default = "Example" }

[placeholders.track]
type = "string"
prompt = "Choose a track"
choices = [{ value = "stable", label = "Stable (recommended)" }, "experimental"]
default = "stable"
```

Supported `type` values: `string`, `text`, `editor`, `bool`, `array`. Array placeholders were added in v0.23.0. `regex` can validate string-like inputs. Prefer defaults to make automated tests deterministic, but verify actual values match types and choices. In conditions, refer to global placeholders and builtins, not conditional-only placeholder definitions.

For arrays, a Liquid expression such as `{% if features contains "serde" %}` is supported. In condition expressions, `features.contains("serde")` is Rhai syntax. The mechanisms are distinct.

## Builtin variables

- `project-name`: generated project name (typically kebab-case, may be overridden with `--force`).
- `crate_name`: Rust-friendly snake_case form of project name.
- `crate_type`: `bin` (default) or `lib` from CLI.
- `authors`, `username`: derived from user's Cargo configuration.
- `os-arch`: platform/architecture identifier.
- `within_cargo_project`, `is_init`: booleans.

Builtins can be overridden via `--define`, value files, or environment variables in supported releases (v0.24+). Avoid declaring redundant custom placeholders for a builtin.

## Conditionals

```toml
[conditional.'crate_type == "lib"']
ignore = ["src/main.rs"]

[conditional.'crate_type == "bin"']
ignore = ["src/lib.rs"]

[conditional.'service == "http"'.placeholders]
port = { type = "string", prompt = "Port?", default = "8080" }
```

Global placeholders are prompted before conditions are evaluated. Conditional placeholders cannot activate later conditionals. Prefer separate subtemplates when structure differs substantially.

## Variable passing

```bash
cargo generate --path ./template --name demo-crate --define service=http --define use_metrics=true
cargo generate --path ./template --name demo-crate --silent --define service=cli --define use_metrics=false
```

The CLI also supports values files and `CARGO_GENERATE_VALUE_<KEY>` environment variables. Consult the installed version's help; its accepted values-file flag aliases and file formats can vary by release. `--path` and `--git` must not be combined. Avoid overriding an existing destination unless explicitly intended.

Source: `guide/src/templates/{template_defined_placeholders,builtin_placeholders,conditional,include_exclude,ignoring,formatting,require_version}.md` in cargo-generate v0.26.0.
