# Feature Specification: Collapse develop into a single stable branch

**Feature Branch**: `003-collapse-develop-branch`

**Created**: 2026-09-10

**Status**: Draft

**Input**: User description: "Remove the develop branch and run a single long-lived stable branch, retargeting open PRs, workflows, dependabot, docs and the constitution."

## Context

This collection runs `develop` (active development) and `stable` (releases), with releases cut by merging `develop` into `stable`. The two-branch model costs a permanent reconciliation tax and buys nothing here — the sibling repositories (infrahub-mcp on `stable`, infrahub-skills on `main`) each run one long-lived branch.

The model is already inverted in practice. `origin/stable...origin/develop` is **3 ahead, 0 behind**: `develop` contains nothing `stable` lacks, while `stable` carries three commits `develop` does not. Reconciliation runs *backwards* through a standing "Backport Stable" PR (#405). A branch that only ever receives backports is not an integration branch.

Because nothing unique lives on `develop`, the collapse loses no work — there is no merge to perform, only references to repoint.

**Relationship to spec 002**: `002-towncrier-release-process` replaces the release trigger. Today a release *is* the `develop` → `stable` merge; under 002 it becomes a reviewable release PR merged into the single branch. This spec removes the branch; 002 supplies the release mechanism that replaces what the branch was doing. 002 depends on this landing first.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A contributor targets one obvious branch (Priority: P1)

A contributor opens a pull request and there is exactly one branch to target. No decision about `develop` versus a `stable` hotfix, and no possibility of landing work on a branch that is not the one being released.

**Why this priority**: This is the point of the change, and it is the slice that delivers value on its own — even before any workflow or doc cleanup, retargeting PRs and flipping the default branch stops new work landing in the wrong place.

**Independent Test**: Open a new PR with no explicit base and confirm it targets `stable`; confirm CI runs the full check set on it.

**Acceptance Scenarios**:

1. **Given** a contributor pushes a branch and opens a PR without specifying a base, **When** the PR is created, **Then** its base is `stable`.
2. **Given** an open PR that previously targeted `develop`, **When** the collapse is complete, **Then** it targets `stable` and its CI has re-run green against that base.
3. **Given** the collapse is complete, **When** anyone attempts to push or open a PR against `develop`, **Then** the branch does not exist.

---

### User Story 2 - Automation points at one branch (Priority: P2)

Dependabot, the upstream-tracking workflows and CI triggers all operate against `stable`, with no `develop`-specific paths left behind.

**Why this priority**: Without it, automation keeps recreating branches and PRs against a branch that no longer exists. Necessary for the change to stick, but User Story 1 already delivers the contributor-facing value.

**Independent Test**: Let dependabot run a cycle and confirm its PRs target `stable`; trigger the SDK-tracking workflow and confirm it offers only `stable`.

**Acceptance Scenarios**:

1. **Given** dependabot runs, **When** it opens a dependency PR, **Then** the PR targets `stable`.
2. **Given** the upstream-tracking workflows run, **When** they select a target branch, **Then** `develop` is not offered.
3. **Given** a PR is opened against `stable`, **When** CI runs, **Then** the full check set runs — linter, sanity, unit tests, plus documentation checks.

---

### User Story 3 - Documentation describes the branch model that exists (Priority: P3)

The constitution, git-workflow guideline, release guide and AGENTS.md describe a single-branch model, so contributors and coding agents are not instructed to target a branch that is gone.

**Why this priority**: Stale governance docs are actively misleading — the constitution is binding and currently mandates PRs target `develop`. Lower priority only because the mechanical change works without it; it must not be skipped.

**Independent Test**: Grep the repository for `develop` and confirm every remaining hit is unrelated to the branch model.

**Acceptance Scenarios**:

1. **Given** the constitution is amended, **When** a reader checks the Development Workflow section, **Then** it names one long-lived branch and the amendment is versioned per the constitution's own governance rule.
2. **Given** the docs are updated, **When** an agent reads AGENTS.md and follows its pointers, **Then** nothing instructs it to branch from or target `develop`.

---

### Edge Cases

- **PR #405 "Backport Stable"** (`stable` → `develop`) becomes meaningless and must be closed rather than merged.
- **PR #229** has been open a long time; it may conflict badly when rebased onto `stable` and may be better closed than retargeted. Decide per-PR rather than bulk-retargeting.
- **Dependabot branch names embed the target** (`dependabot/pip/develop/...`); existing ones are abandoned and recreated rather than renamed.
- **Branch protection currently protects `develop`** — its rules must be transferred to `stable`, not simply deleted, or the repo is briefly unprotected.
- **`develop` is deleted while a contributor has it checked out locally** — they need `git remote prune` guidance; local copies are otherwise harmless.
- **A release is in flight during the collapse** — the change must not run concurrently with a release attempt.
- **The three commits on `stable` but not `develop`** need no action, but confirm they are genuinely present in `stable`'s history before deleting `develop`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository's default branch MUST be `stable`.
- **FR-002**: Every open pull request targeting `develop` MUST be retargeted to `stable` or explicitly closed, with a per-PR decision recorded.
- **FR-003**: The `stable` → `develop` backport PR MUST be closed.
- **FR-004**: Branch protection rules on `develop` MUST be transferred to `stable` before `develop` is deleted, leaving no window in which the surviving branch is unprotected.
- **FR-005**: `develop` MUST be deleted only after FR-001 through FR-004 are complete and after confirming it holds no commits absent from `stable`.
- **FR-006**: CI MUST run the full check set — linter, sanity, unit tests, and documentation checks — on every pull request to `stable`.
- **FR-007**: The `develop`-specific PR trigger workflow MUST be removed and its checks preserved on the `stable` path.
- **FR-008**: Dependabot MUST target `stable`. Its existing `develop`-targeted PRs cannot be retargeted in place — the branch name embeds the target (`dependabot/pip/develop/...`) — so they MUST be closed under FR-002 and left for dependabot to recreate against `stable`.
- **FR-009**: The upstream-tracking workflows MUST NOT offer `develop` as a target branch.
- **FR-010**: The constitution MUST be amended to describe a single-branch model, with a version bump and sync-impact record per its own governance rule. Redefining the branch model is a breaking change to a documented workflow rule, so the bump is MAJOR.
- **FR-011**: Every repository file that describes the branch model, or instructs a contributor or agent where to branch from or what to target, MUST describe the single-branch model. Enumerated from the tree at specification time:
  - `dev/guidelines/git-workflow.md` — the branch table, "PRs target `develop`", the CI-trigger table
  - `dev/guidelines/testing.md` — "Tests run on every PR to `develop`" and the `trigger-pr-develop.yml` pointer
  - `dev/guides/releasing-the-collection.md` — the `develop` → `stable` merge presented as the release trigger
  - `dev/guides/running-tests.md` — the `git worktree add ../infrahub-baseline develop` branch-comparison recipe
  - `dev/README.md` — the summaries of the git-workflow guideline and the release guide
  - `AGENTS.md` — the git-workflow pointer, labelled "Branch model (develop/stable)"
  - `README.md` — "Releasing the current major version happens from the `develop` branch"
  - `.github/pull_request_template.md` — the "point your PR to the `develop` branch" banner and the "My PR targets the `develop` branch" checklist item
- **FR-012**: Once FR-007 through FR-011 are complete, no repository file may instruct a contributor or agent to branch from, or target, `develop`. Two classes of remaining `develop` hit are out of scope and MUST NOT be read as violations:
  - `.github/file-filters.yml` — a comment recounting a past incident ("a ruff bump landed on develop"). It records history and instructs nobody; it may be reworded for accuracy but needs no retargeting.
  - `.agents/skills/**` — vendored skill copies that list `develop` among generic long-lived branch names (`main`, `master`, `develop`, `stable`) in branch-discipline guards. They describe no branch model of this repository and are corrected upstream in the skills monorepo, if at all.

### Key Entities

- **`stable`**: the single long-lived branch; default, protected, and the base for all pull requests.
- **`develop`**: removed. Currently the default branch, strictly behind `stable`.
- **Branch protection ruleset**: currently applied to `develop`; transferred to `stable`.
- **Constitution**: binding governance document encoding the branch model in four places; requires a versioned amendment.
- **Open pull requests**: six against `develop`, each retargeted or closed by explicit decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Exactly one long-lived branch exists in the repository.
- **SC-002**: 100% of open pull requests are resolved — retargeted to `stable` or closed with a reason — with none left pointing at a deleted branch.
- **SC-003**: The surviving branch is protected at every point during the change; there is no interval with zero protected long-lived branches.
- **SC-004**: Zero commits are lost — every commit reachable from `develop` before the change remains reachable from `stable` after it.
- **SC-005**: A repository-wide search for `develop` returns no hit that refers to this repository's branch model, excluding the two classes FR-012 places out of scope.
- **SC-006**: The first dependency PR raised after the change targets `stable` without manual intervention.

## Governance Gates Crossed

This specification changes no workflow, branch, pull request or repository setting — it only proposes the collapse. Everything below is the gate the **implementation** will cross and must have approved before that work lands. Nothing here is done yet.

Per this repository's `AGENTS.md` **Ask First** list:

- **Will cross — Modifying CI workflows in `.github/workflows/`**: the implementation removes `trigger-pr-develop.yml`, adds the documentation and changelog checks to the `stable` PR path, and drops `develop` from the target-branch choices in `update-infrahub.yml` and `update-infrahub-sdk.yml`. As of this specification none of that has happened — `trigger-pr-develop.yml` still triggers on pull requests to `develop`.
- **Not crossed — Adding new dependencies**: none.
- **Not crossed — Changing ruff configuration**: not touched.
- **Not crossed — Modifying `plugins/module_utils/infrahub_utils.py`**: not touched.
- **Not crossed — Changing `INFRAHUB_ARG_SPEC`**: not touched.

Beyond that list, the implementation **amends the constitution**, whose Governance section requires that amendments update the document and the corresponding `dev/knowledge/` and `dev/guidelines/` files in sync. That synchronisation is FR-010 and FR-011, and it is the highest-order gate here — higher than the CI change, because the constitution is binding on every future PR.

## Assumptions

- No release is in flight while the collapse runs.
- `develop` holds no unique commits — verified as `3 0` against `stable` at specification time, and to be re-verified immediately before deletion.
- Contributors can be notified to prune local tracking branches; no automated cleanup of clones is attempted.
- The checks currently running on PRs to `stable` are a superset of those on PRs to `develop`, so consolidating onto `stable` loses no coverage.
- Single-branch delivery is the OpsMill default; the sibling repos already run this way, so this removes a divergence rather than inventing a model.

## Out of Scope

- The towncrier release process itself — specified as `002-towncrier-release-process`, which depends on this.
- Changing the release cadence or what triggers a release, beyond removing the `develop` → `stable` merge as the trigger.
- Renaming `stable` to `main` for consistency with infrahub-skills.
- Applying the same collapse to any other repository.
