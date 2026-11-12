# cargo-generate-template-builder Agent Skill

A portable [Agent Skills](https://agentskills.io/specification) package for creating, debugging, and verifying [cargo-generate](https://github.com/cargo-generate/cargo-generate) templates, based on the uploaded `cargo-generate` **v0.26.0** repository.

## Install

Copy the entire `cargo-generate-template-builder/` directory into your coding agent's skill search path (for example, `.agents/skills/` for clients that scan this convention). Restart/reload the agent if required. The activation instructions are in `SKILL.md`.

## Create a template without an agent

```sh
python3 cargo-generate-template-builder/scripts/scaffold_template.py ./my-template --kind bin
python3 cargo-generate-template-builder/scripts/validate_template.py ./my-template --strict
```

Replace `bin` with `lib` or `workspace` to scaffold a library or two-crate workspace. The scaffold step does not overwrite existing directories.

With Rust and cargo-generate installed:

```sh
python3 cargo-generate-template-builder/scripts/smoke_test.py ./my-template
cargo generate --path ./my-template --name my-project --silent --vcs none
```

The starter uses two template-defined placeholders: `rust_edition` (`2021` or `2024`) and `include_ci` (boolean). Default settings generate a project with a CI workflow; the false branch omits it. Test the false branch with `--define include_ci=false`.

## What's included

- `SKILL.md`: when to invoke, step-by-step authoring workflow, and delivery criteria.
- `references/`: concise, version-specific explanations of config, Liquid, Rhai, testing, and security.
- `assets/bin-template/`, `assets/lib-template/`, and `assets/workspace-template/`: ready-to-customize binary, library, and two-crate workspace starters.
- `scripts/scaffold_template.py`: copies starter templates without overwriting.
- `scripts/validate_template.py`: conservative static linter using Python standard library.
- `scripts/smoke_test.py`: isolated cargo-generate expansion and Rust build/test run.
- `tests/`: unit tests for the included helper scripts.

## Requirements and limits

The helper scripts need Python **3.11+**. `smoke_test.py` additionally needs `cargo` and `cargo-generate` on `PATH`. Static validation does not parse Liquid or Rhai fully and cannot substitute for a real generated-project build. No bundled script requires external Python packages. This archive does not include or redistribute the full cargo-generate source tree.
