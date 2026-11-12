# Copier Agent Skill

![context: 11.5k tokens](https://img.shields.io/badge/context-11.5k_tokens-blue)

A skill for creating, updating, and rendering project templates via
[`copier`](https://copier.readthedocs.io/) CLI.

---

## Installation

This skill requires Python 3.10+, Git 2.27+, and `copier` CLI:

```sh
# on MacOS:
brew install copier
# if `uv` is installed
uv tool install copier
# if `pipx` is installed
pipx install copier
# if `pip` is install
pip install copier
```

### Vercel Skills CLI

```sh
npx skills add thesmart/repo-copier
```

### Manual

Clone into your Claude Code skills directory:

```sh
git clone https://github.com/thesmart/repo-copier.git ~/.claude/skills/repo-copier
```

---

## Development Dependencies

- [Node.js / npx](https://nodejs.org/) — used for prettier formatting, skills management
- [yq](https://github.com/mikefarah/yq#install) — used for YAML frontmatter updates in SKILL.md
- [skill-creator](https://github.com/anthropics/skills) — skill creation, evaluation, and
  optimization

---


## Keeping Copier guidance current

This repository has **two independent versions**: `VERSION` / `metadata.version`
track the skill itself, while `metadata.copier_version` tracks the upstream
[Copier](https://github.com/copier-org/copier) release documented by this skill.
The initial upstream target is **Copier 9.19.1** (released October 13, 2026).

Run the dependency-free Python updater from the skill repository root:

```sh
make update-copier                   # fetch latest stable GitHub release
python3 scripts/update_copier.py --version 9.19.1  # pin a particular stable release
python3 scripts/update_copier.py --dry-run         # preview without writing
make check-copier                    # exit 1 if official snapshots are out of sync
make test-updater                    # local unit tests (no network)
```

The updater queries GitHub's latest stable release and downloads the **six official
Markdown guides, upstream license, and changelog at the exact release Git tag**.
It writes the official docs to `reference/upstream/`, generates
`reference/copier-version.md` (recent release notes), updates
`metadata.copier_version` in `SKILL.md`, and records SHA-256 hashes in
`reference/copier-upstream.json`. It leaves `VERSION`, `metadata.version`, and the
hand-maintained concise guides intact. Review the resulting Git diff, especially
if upstream documents newly breaking or security-sensitive behavior.

**Network access is required** for a live refresh. The checked-in local reference
summaries remain available offline; the full upstream documents are installed by
running the updater. `--check` detects missing upstream snapshots. The
`--offline-dir PATH --version X.Y.Z` combination can replay a locally saved
Copier release tree for testing or air-gapped operation.

The copied upstream documentation is MIT licensed; the updater saves its upstream
license as `reference/upstream/LICENSE.copier`. The surrounding skill remains
subject to this repository's PolyForm Internal Use license.

---

## Benchmark

Evaluated on 3 tasks (template authoring, update conflict resolution, multi-template setup) against
a baseline of Claude without the skill.

| Metric    | With Skill  | Without Skill | Delta       |
| --------- | ----------- | ------------- | ----------- |
| Pass Rate | 100% ± 0%   | 72% ± 5%      | **+28 pts** |
| Latency   | 45s ± 7s    | 59s ± 8s      | -14s        |
| Tokens    | 2,875 ± 620 | 4,071 ± 668   | -1,196      |

The skill improves accuracy by guiding Claude to copier-idiomatic patterns (e.g.
`_copier_conf.answers_file`, `_copier_answers|to_nice_yaml`) that Claude otherwise misses or
approximates incorrectly.

---

## License Terms

This software is licensed under the [PolyForm Internal Use License 1.0.0](./LICENSE).

Informal license summary:

- **Internal use only**: Use and modify freely within your organization.
- **No distribution**: You cannot redistribute outside your organization, no sublicensing.
- **No warranty**: Provided "as is" with no liability.

Please submit PRs via Github.
