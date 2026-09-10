# Implementation Plan: Towncrier-based release process

**Branch**: `002-towncrier-release-process` | **Date**: 2026-09-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-towncrier-release-process/spec.md`

## Summary

Replace a hand-maintained `CHANGELOG.rst` and `release-drafter` with towncrier news fragments assembled at release time. Contributors write one line per change in the pull request that makes it; a push to `stable` computes the next version from PR labels, assembles `CHANGELOG.md`, and opens a `chore(release): <version>` pull request. Merging that pull request tags the release and publishes it with the assembled changelog as the body, which in turn triggers the existing Ansible Galaxy upload.

No collection code changes. The work is entirely in CI workflows, packaging metadata, and documentation.

## Technical Context

**Language/Version**: No runtime language change. Tooling is Python (>=3.11, <3.15) via `uv`; workflows are GitHub Actions YAML and bash.

**Primary Dependencies**: `towncrier>=25.8.0` (new, dev group); `patrickjahns/version-drafter-action@v1.3.1` (existing, retained); `gh` CLI (preinstalled on runners).

**Storage**: Files only — news fragments in `changelog/`, assembled output in `CHANGELOG.md`.

**Testing**: No unit tests — this feature adds no importable code. Verification is by exercising `towncrier build` and the release-body extraction locally, plus `yamllint` / `rumdl` in CI. The release workflows themselves cannot be exercised before merge because they only trigger on `stable`.

**Target Platform**: GitHub Actions (`ubuntu-latest` / `ubuntu-22.04`).

**Project Type**: Ansible collection published to Galaxy.

**Performance Goals**: N/A — release-time tooling, not a runtime path.

**Constraints**:

- Tags in this repository are **bare** (`1.8.3`), unlike the sibling repos' `v`-prefixed tags. `title_format` and every tag reference must not assume a prefix.
- The version lives in **two** files (`galaxy.yml` canonical, `pyproject.toml` mirrored) that must move together.
- No importable package exposes `__version__`, so towncrier cannot read the version; it is always passed explicitly.
- Version computation must stay isolated in a single step emitting only a version string, so a later migration onto the shared `release-prepare` can consume it as `bump-strategy: manual` + `version:`.

**Scale/Scope**: 4 workflow files, `pyproject.toml`, the changelog scaffolding, and 4 documentation files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

Assessed against `.specify/memory/constitution.md` v1.1.0.

| Principle | Applies? | Assessment |
|---|---|---|
| I. Ansible Collection Standards | No | No plugin file is touched; no boilerplate, docstring, or sanity surface changes. |
| II. Two Plugin Patterns | No | No plugins added or modified. |
| III. Idempotency and State Management | No | No module behaviour changes. |
| IV. SDK Abstraction Layer | No | No API access added. |
| V. Test Coverage and Quality Gates | **Yes** | **Reinforced, not diluted.** The feature *adds* a gate (`changelog-check.yml`) and adds a hard failure when a release would carry no notes. Its "Documentation Accuracy" guardrail is respected: no generated MDX is hand-edited. |

**Development Workflow / Governance**: The constitution's Governance section requires that amendments update the document *and* the corresponding `dev/knowledge/` and `dev/guidelines/` files in sync. This feature does not amend a principle, but it does invalidate concrete statements in `dev/guidelines/git-workflow.md` (changelog is `CHANGELOG.rst`; release drafts via `workflow-release-drafter.yml`) and `dev/guides/releasing-the-collection.md`. Those are updated in the same change, and `dev/guides/creating-a-module.md` — which instructed authors to edit `CHANGELOG.rst` — with them.

**Ask First gates crossed** (from `AGENTS.md`): adding a dependency to `pyproject.toml`, and modifying CI workflows. Both are inherent to the feature and are called out explicitly in the pull request rather than slipped in.

**Result: PASS.** No violation requiring justification; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/002-towncrier-release-process/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Task breakdown
```

`research.md`, `data-model.md`, `contracts/` and `quickstart.md` are **not** generated. There are no unknowns to research (every decision was settled during idea grilling and is recorded in the spec's Assumptions), no data entities beyond files on disk, and no external interface contract — the collection's published surface is unchanged.

### Source Code (repository root)

```text
.github/
├── release-drafter.yml                     # DELETED
└── workflows/
    ├── changelog-check.yml                 # NEW  — PR-time fragment gate
    ├── release-publish.yml                 # NEW  — tag + publish on release-PR merge
    ├── trigger-push-stable.yml             # EDIT — assemble changelog, open release PR
    └── workflow-release-drafter.yml        # DELETED

changelog/                                  # NEW
├── .gitignore                              #       keeps the dir tracked when empty
└── towncrier.md.template                   #       byte-identical to opsmill/infrahub

CHANGELOG.md                                # NEW  — replaces CHANGELOG.rst
CHANGELOG.rst                               # DELETED
pyproject.toml                              # EDIT — [tool.towncrier] + dev dependency

AGENTS.md                                   # EDIT — changelog section
dev/guides/releasing-the-collection.md      # EDIT — new release flow
dev/guides/creating-a-module.md             # EDIT — fragment instead of CHANGELOG.rst
dev/guidelines/git-workflow.md              # EDIT — changelog + CI table
```

**Structure Decision**: No source tree option applies — this feature touches no `plugins/` code. The layout above is the real set of paths changed.

## Complexity Tracking

> No Constitution Check violations. Table intentionally empty.
