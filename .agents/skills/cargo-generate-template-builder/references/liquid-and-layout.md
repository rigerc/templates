# Liquid rendering, file layout, and authoring rules

Liquid is the template language used for file contents and paths. Use it carefully in generated Rust and TOML, where quotes, backslashes, indentation, and conditional whitespace can break output.

## Simple bin template

```text
my-template/
  cargo-generate.toml
  Cargo.toml.liquid
  README.md.liquid
  src/main.rs.liquid
  .github/workflows/ci.yml
```

`Cargo.toml.liquid`:

```toml
[package]
name = "{{ project-name }}"
version = "0.1.0"
edition = "{{ rust_edition }}"

[dependencies]
```

`src/main.rs.liquid`:

```rust
fn main() {
    println!("Hello from {{ crate_name }}!");
}
```

Use `{{ project-name }}` for Cargo package name and `{{ crate_name }}` for Rust `use` paths or identifiers. Do not inject unvalidated text values directly into quoted Rust/TOML literals; use constrained choices, validation, or a safe encoding strategy.

## Filtering and branching

```liquid
{% if include_ci %}
CI is included.
{% endif %}

{% for item in features %}
- {{ item }}
{% endfor %}
```

Liquid filters include `snake_case`, `kebab_case`, `pascal_case`, `lower_camel_case`, `upper_camel_case`, `shouty_snake_case`, `shouty_kebab_case`, `title_case`, plus `rhai` to invoke a Rhai script. The `rhai` filter warns on errors rather than necessarily halting generation; avoid complex side effects in rendering.

Filename and directory components may contain Liquid: `{{project-name}}/src/...`; names are sanitized after substitution. Keep generated Cargo layout idiomatic and avoid redundant nesting: `cargo generate` normally creates a project-named destination directory already.

## Include/exclude versus ignore

- Render files with Liquid by default unless excluded.
- `exclude` skips Liquid rendering, but retains the file in the result.
- `ignore` omits the file/folder entirely from output.
- Patterns for `include`/`exclude` match source paths (including `.liquid` suffix), while `ignore` names the final path.
- A `.genignore` file is deprecated; use `[template] ignore`.

## GitHub Actions conflict

`${{ github.ref }}` is interpreted as an overlapping syntax in Liquid-enabled files. Easiest fix when no template variables are needed in the workflow:

```toml
[template]
exclude = [".github/workflows/*.yml"]
```

Or when the workflow needs templating, escape each GitHub expression:

```liquid
{% raw %}${{ github.ref }}{% endraw %}
```

Do not add a shell command hook merely to fix GitHub Actions interpolation; a raw block or exclude rule is simpler and safer.

## Rust output correctness

Always inspect the generated `Cargo.toml` and any Rust files, not just the inputs. Where a template has conditional Cargo dependencies or features, test all supported combinations; conditionals that look valid in Liquid can produce invalid TOML. `cargo-generate` 0.26.0 formats created `.rs` files with `rustfmt` after generation but warns rather than failing on formatting errors, so `cargo fmt --check` and `cargo check` remain necessary.

Source: `guide/src/templates/{README,pitfalls,formatting,include_exclude}.md`, example templates and integration tests in cargo-generate v0.26.0.
