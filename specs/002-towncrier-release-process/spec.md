# Feature Specification: Towncrier-based release process

**Feature Branch**: `002-towncrier-release-process`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Replace the release-drafter based release process with a towncrier-managed changelog, label-driven version bumping, and a reviewable release PR, shaped to match the opsmill-cicd-workflows release-prepare contract for later migration."

## Context

This collection's changelog practice has failed. `CHANGELOG.rst` is a hand-maintained file in antsibull's format, but no antsibull tooling exists in the repo (ADR-0005 explicitly rejected `antsibull-docs`), there is no `changelogs/` directory, no `config.yaml`, and no fragments. Automated `chore: update changelog & docs` commits stopped on 2025-01-29. Since then:

- Releases 1.8.0, 1.8.1, 1.8.2 and 1.8.3 shipped with no changelog entry.
- The newest section documents **v1.9.0**, a version never tagged. Its content (CoreFileObject support, `object_file_fetch`) actually shipped in **1.8.1** — `bc0ee34` is contained in tags 1.8.1, 1.8.2 and 1.8.3.

Release notes today come from `release-drafter`, which lists PR titles. Readers get whatever a PR happened to be called rather than an explanation written for them.

This feature is one of three sibling adoptions (infrahub-mcp, infrahub-skills, infrahub-ansible). All three implement locally but are deliberately shaped to match the `opsmill-cicd-workflows` `release-prepare` contract, so a later migration owned by SRE is workflow rewiring rather than redesign.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A contributor's own words reach the release (Priority: P1)

A contributor changes collection behaviour and records that change in one line, in the same pull request. When the release ships, their line appears in the release notes — nobody reconstructs it afterwards from git history.

**Why this priority**: This is the whole point. Every other part of the pipeline is machinery serving this outcome, and it is the part that failed here — four releases shipped with nothing recorded.

**Independent Test**: Open a PR that changes a module, add a newsfragment, merge it, cut a release, and confirm the line appears verbatim in the published release body. Delivers a truthful changelog even if nothing else in this spec is built.

**Acceptance Scenarios**:

1. **Given** a contributor opens a PR changing behaviour, **When** they merge it with no newsfragment and no `ci/skip-changelog` label, **Then** the PR check fails and names the fragment path to create.
2. **Given** the contributor adds `changelog/+<slug>.<type>.md` and merges, **When** the next release is published, **Then** the release body contains that line under its category heading.
3. **Given** a trivial PR labelled `ci/skip-changelog`, **When** it is merged with no fragment, **Then** the check passes.

---

### User Story 2 - Maintainer cuts a release from a reviewable PR (Priority: P2)

A maintainer promotes accumulated work to a release. The version is computed from PR labels, `CHANGELOG.md` is assembled from fragments, and both arrive as a reviewable pull request rather than as a side effect of a push.

**Why this priority**: Delivers the auditable release path and retires `release-drafter`, but User Story 1 already delivers a correct changelog without it.

**Independent Test**: Trigger the release preparation, confirm a `chore(release): X.Y.Z` PR appears containing only the version files and the assembled changelog section, and that publishing is impossible until it merges.

**Acceptance Scenarios**:

1. **Given** merged PRs labelled `changes/minor`, **When** release preparation runs, **Then** the computed version is the correct minor bump and is emitted as a single version string from a discrete step.
2. **Given** fragments exist in `changelog/`, **When** the release PR is built, **Then** `galaxy.yml` and `pyproject.toml` both carry the new version and `CHANGELOG.md` gains the assembled section.
3. **Given** no fragments exist, **When** release preparation runs, **Then** it fails rather than producing an empty changelog section.
4. **Given** the release PR is merged and the GitHub release published, **Then** the release body is the towncrier-rendered section and the collection publishes to Galaxy at that version.

---

### User Story 3 - Curated notes for a notable release (Priority: P3)

For a release worth explaining, a maintainer produces a workflow-first prose page from the assembled changelog, published to the docs site.

**Why this priority**: Valuable but optional. `CHANGELOG.md` already covers every release; this covers releases where a human has something to teach. Making it mandatory is how the practice gets abandoned — exactly what happened to `CHANGELOG.rst`.

**Independent Test**: Take a published release's changelog section, run the release-notes skill against it, and confirm a docs page renders in the site build.

**Acceptance Scenarios**:

1. **Given** a published minor release, **When** the release-notes skill runs with the towncrier output as input, **Then** a release-notes page is produced and renders in the Docusaurus build.

---

### Edge Cases

- **Dependabot and bot PRs** cannot write fragments — they are auto-labelled `ci/skip-changelog`.
- **A release where every PR was skip-labelled** yields zero fragments: preparation hard-fails and the releaser adds a housekeeping fragment. There is no empty-release opt-out, matching the platform's per-release rule.
- **Two PRs choosing the same fragment slug** collide as an ordinary file conflict, resolved in git.
- **The two version files drift** if only one is written — `galaxy.yml` is canonical for Galaxy, `pyproject.toml` must follow in the same commit.
- **Tags here are bare** (`1.8.3`, no `v` prefix), unlike the sibling repos — `title_format` must not assume a prefix.
- **A hotfix** follows the same path as any other change — branch from `stable`, carry a fragment, merge back. With a single long-lived branch there is no second accumulation point to reconcile.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST fail a pull-request check when the PR adds no newsfragment and carries no `ci/skip-changelog` label.
- **FR-002**: System MUST compute the next version from PR labels (`changes/*`, `type/*` per the existing `version-drafter.yml` mapping) and expose it as a single version string produced by a discrete step.
- **FR-003**: System MUST assemble `CHANGELOG.md` from newsfragments using towncrier at release time, and MUST fail rather than emit an empty section.
- **FR-004**: System MUST use the towncrier-rendered section as the GitHub Release body.
- **FR-005**: System MUST write the computed version to both `galaxy.yml` and `pyproject.toml` in the same change.
- **FR-006**: System MUST store newsfragments in `changelog/` using the seven standard OpsMill types (security, removed, deprecated, added, changed, fixed, housekeeping).
- **FR-007**: Users MUST be able to skip the fragment requirement on a trivial PR via `ci/skip-changelog`.
- **FR-008**: Release changes MUST arrive as a reviewable pull request that requires approval before a tag is created.
- **FR-009**: System MUST NOT retain `release-drafter` — both `.github/release-drafter.yml` and `.github/workflows/workflow-release-drafter.yml` are removed.
- **FR-010**: System MUST replace `CHANGELOG.rst` with `CHANGELOG.md`, carrying existing history across, relabelling the mislabelled `v1.9.0` section to `1.8.1`, and recording that entries for 1.8.0, 1.8.2 and 1.8.3 were never captured.
- **FR-011**: Version computation MUST remain separable from the release job, so it can later be wired into `release-prepare` as `bump-strategy: manual` with an explicit `version:` input.

### Key Entities

- **Newsfragment**: `changelog/<id>.<type>.md`; one per change, one line of Markdown, authored by whoever makes the change.
- **CHANGELOG.md**: the assembled canonical record; replaces `CHANGELOG.rst`.
- **Release PR**: `chore(release): X.Y.Z`; carries version files plus the assembled changelog section and is the approval point.
- **GitHub Release body**: the towncrier-rendered section; replaces the release-drafter PR-title list.
- **Version string**: label-derived; written to `galaxy.yml` and `pyproject.toml`, and used as the bare git tag.
- **Curated release-notes page**: optional prose page on the docs site, generated from the changelog section.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of releases published after adoption carry at least one human-written changelog entry, against a baseline of 0 of the last 4.
- **SC-002**: Zero changelog merge conflicts across all pull requests in the first two release cycles.
- **SC-003**: No release requires a changelog commit after publication — notes are complete at publish time.
- **SC-004**: `galaxy.yml` and `pyproject.toml` report the same version at every tagged commit.
- **SC-005**: A later migration onto the shared workflows changes only workflow wiring — zero edits to fragment content, fragment directory, or category taxonomy.

## Governance Gates Crossed

Per this repository's `AGENTS.md` **Ask First** list:

- [x] **Adding new dependencies to `pyproject.toml`** — towncrier enters the dev dependency group.
- [x] **Modifying CI workflows in `.github/workflows/`** — release-drafter workflow removed; changelog check and release-preparation workflows added.
- [ ] Changing ruff configuration — not touched.
- [ ] Modifying `plugins/module_utils/infrahub_utils.py` — not touched.
- [ ] Changing `INFRAHUB_ARG_SPEC` — not touched.

Constitution (`.specify/memory/constitution.md`): Principles I–IV govern plugin code and are untouched by this feature. Principle V (Test Coverage and Quality Gates) is reinforced — the PR-time fragment check adds a gate rather than relaxing one.

## Assumptions

- PR labels are applied reliably; conventional-commit type prefixes are **not** trustworthy here, which is why the bump stays label-driven rather than adopting the platform's commit-driven `auto-semver`.
- Nothing consumes `CHANGELOG.rst` — Galaxy does not require it, no antsibull tooling reads it, and the docs site does not render it.
- This collection runs a **single long-lived branch, `stable`**. Collapsing the `develop`/`stable` model is delivered by spec `003-collapse-develop-branch` and is a prerequisite for the release path described here; the fragment-accumulation and release-PR flow assume one branch, matching infrahub-mcp and infrahub-skills.
- SRE owns the eventual migration onto the shared reusable workflows, on their own timeline.
- The `opsmill-cicd-workflows` `changelog-towncrier` composite currently hard-codes a `changes/` directory and will need to honour towncrier's configured `directory` before migration; this is tracked separately against that repository.

## Out of Scope

- Migrating onto the shared reusable workflows in `opsmill-cicd-workflows`.
- Reconstructing changelog history for releases 1.8.0, 1.8.2 and 1.8.3.
- Collapsing the `develop`/`stable` branch model — specified separately as `003-collapse-develop-branch`, which this feature depends on.
- Unifying conventional-commit types with towncrier fragment types — they answer different questions and both remain.
