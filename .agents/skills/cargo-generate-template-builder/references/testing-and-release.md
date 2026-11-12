# Validation and release checklist

## Static validation

```bash
python3 scripts/validate_template.py ./template --strict
```

The included helper checks structural/configuration mistakes, but does not execute Liquid or Rhai; false negatives and occasionally false positives are possible. If a variable is defined by a `pre` hook, an undefined-placeholder diagnostic may be intentional; manually verify.

## Runtime smoke tests

```bash
python3 scripts/smoke_test.py ./template --define rust_edition=2021 --define include_ci=true
python3 scripts/smoke_test.py ./template --define rust_edition=2024 --define include_ci=false
```

The helper uses `cargo generate --path ... --name ... --silent --vcs none` in a temporary directory, then runs `cargo check` and `cargo test`. It requires installed `cargo` and `cargo-generate`, and preserves the output with `--keep` when debugging. It **does not** pass `--allow-commands`; templates requiring privileged command hooks should be reviewed individually and run with explicit user authorization, never implicitly.

For workspaces, prefer after-generation:

```bash
cargo check --workspace
cargo test --workspace
cargo fmt --all --check
```

For advanced templates add a matrix with: bin versus lib, conditional true versus false, values file versus `--define`, relevant editions, platform-specific hooks, and `--init` if supported. Test in a clean directory away from the template repository. The template's generated code should remain valid in the minimum supported toolchain.

## Release gate

- All template inputs and hooks committed; no generated output or credentials checked in.
- All custom placeholders have documented types, examples, and defaults (when appropriate).
- Conditional branch outputs and ignored files verified.
- Expanded `Cargo.toml` parses and builds; tests and format checks pass.
- `.github` workflows containing `${{ }}` render unchanged or are guarded by raw tags.
- Command hooks disclosed and minimal; no hidden network or system modifications.
- Template README has local and Git usage examples, plus required minimum cargo-generate version.
- Optional: CI uses `cargo-generate/cargo-generate-action` and validates the expanded project on push/weekly schedule.

Source: v0.26.0 `guide/src/templates/authoring.md` and tests/integration.
