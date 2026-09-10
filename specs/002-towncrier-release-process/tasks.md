---
description: "Task list for the towncrier-based release process"
---

# Tasks: Towncrier-based release process

**Input**: Design documents from `/specs/002-towncrier-release-process/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md)

**Tests**: No test tasks. This feature adds no importable code, so there is nothing to unit-test. Verification is by exercising the tooling against real fragments and by the existing lint jobs — see Phase 5.

**Organization**: Grouped by the user stories in spec.md so each is independently deliverable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story the task serves

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Make towncrier available and give it somewhere to read from. Everything else depends on this.

- [x] T001 Add `[tool.towncrier]` to `pyproject.toml` with the seven standard OpsMill types, `directory = "changelog"`, `filename = "CHANGELOG.md"`, and a `title_format` using **bare** tags (no `v` prefix). Omit `package` — no importable module exposes the version.
- [x] T002 Add `towncrier>=25.8.0` to the `dev` dependency group in `pyproject.toml` and refresh `uv.lock`.
- [x] T003 [P] Create `changelog/.gitignore` (`!.gitignore`) so the directory stays tracked once fragments are consumed.
- [x] T004 [P] Create `changelog/towncrier.md.template`, byte-identical to the one in `opsmill/infrahub`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Give towncrier a `CHANGELOG.md` to insert into, and retire the file it replaces. Blocks every user story — without a marker, `towncrier build` has no insertion point.

- [x] T005 Create `CHANGELOG.md` carrying the history from `CHANGELOG.rst`, converted to Markdown, with the `<!-- towncrier release notes start -->` marker above the newest entry.
- [x] T006 Relabel the mislabelled `v1.9.0` section to `1.8.1`. Verified: `bc0ee34` is contained in tags 1.8.1, 1.8.2 and 1.8.3, so that work shipped in 1.8.1.
- [x] T007 Record in `CHANGELOG.md` that entries for 1.8.0, 1.8.2 and 1.8.3 were never captured, rather than reconstructing them from git log.
- [x] T008 Delete `CHANGELOG.rst`.

---

## Phase 3: User Story 1 — A contributor's own words reach the release (P1)

**Goal**: A pull request that changes behaviour cannot merge without a news fragment.

**Independent test**: Open a PR with no fragment → the check fails; add one → it passes; label `ci/skip-changelog` with no fragment → it passes.

- [x] T009 [US1] Add `.github/workflows/changelog-check.yml`, failing a pull request that adds no file under `changelog/` unless it carries `ci/skip-changelog`. Query the API via `gh pr view --json files` rather than diffing locally, so the result does not depend on checkout depth.
- [x] T010 [US1] Make the failure message actionable — name the `towncrier create` command, the seven types, and the escape-hatch label.

**Checkpoint**: US1 delivers a correct changelog on its own, even if nothing below ships.

---

## Phase 4: User Story 2 — Maintainer cuts a release from a reviewable PR (P2)

**Goal**: The version bump and assembled changelog arrive as a pull request; merging it publishes the release.

**Independent test**: Push to `stable` → a `chore(release): <version>` PR appears containing only version files and the changelog section; publishing is impossible until it merges.

- [x] T011 [US2] In `trigger-push-stable.yml`, keep version computation in its own step whose only output is a version string (the seam for `release-prepare`'s `bump-strategy: manual`).
- [x] T012 [US2] Add a changelog-assembly step that hard-fails when `changelog/` holds no fragments, then runs `towncrier build --version "$VERSION" --yes`.
- [x] T013 [US2] Replace the direct `stable` commit with a step that creates `release/<version>`, commits `pyproject.toml`, `galaxy.yml`, `uv.lock`, `CHANGELOG.md` and the consumed `changelog/`, and opens the release pull request. Re-running refreshes the same branch instead of opening a second PR.
- [x] T014 [US2] Extend the loop guard to skip `chore(release):` commits so preparing a release cannot trigger preparing another.
- [x] T015 [US2] Add `.github/workflows/release-publish.yml`, which tags and publishes on merge using the assembled section as the body. Key the decision off *"does a tag exist for the version in `galaxy.yml`?"* rather than the commit message, so squash, rebase and merge behave identically.
- [x] T016 [US2] Guard the extracted body: fail if empty, and fail if it does not mention the version being released.
- [x] T017 [US2] Remove `release-drafter` — delete `.github/release-drafter.yml` and `.github/workflows/workflow-release-drafter.yml`, and drop the `release` job that called it.

**Checkpoint**: Releases are auditable and the Galaxy publish path is unchanged.

---

## Phase 5: Verification

**Purpose**: Prove the parts that *can* be proven before merge, and be explicit about the part that cannot.

- [x] T018 Exercise `towncrier build --version 1.8.4` against the converted `CHANGELOG.md`; confirm it inserts after the marker and above the 1.8.1 section.
- [x] T019 Exercise the release-body extraction; confirm it returns exactly the new section and nothing from prior releases, and that the version guard trips when it should.
- [x] T020 Revert the simulation so no assembled changelog or consumed fragment is committed.
- [x] T021 [P] `yamllint` across `.github/workflows/`.
- [x] T022 [P] `rumdl` across every changed Markdown file.
- [ ] T023 **Cannot be done pre-merge**: the release workflows only trigger on `stable`, so the release path gets its first real exercise on the next release. Watch that run.

---

## Phase 6: Documentation

**Purpose**: The constitution's Governance section requires the `dev/` docs to move in step. Stale release docs are actively misleading.

- [x] T024 [P] Rewrite the release flow in `dev/guides/releasing-the-collection.md`, including the release-PR step and the updated checklist.
- [x] T025 [P] Update the changelog and CI-workflow sections of `dev/guidelines/git-workflow.md`.
- [x] T026 [P] Replace the "edit `CHANGELOG.rst`" step in `dev/guides/creating-a-module.md` with the fragment workflow.
- [x] T027 [P] Add a Changelog section to `AGENTS.md`.
- [x] T028 Add a news fragment for this change itself, exercising the workflow it introduces.

---

## Dependencies

- **Phase 1 → Phase 2**: towncrier must be configured before `CHANGELOG.md` has meaning.
- **Phase 2 → Phase 4**: the marker must exist before `towncrier build` can insert.
- **Phase 3 is independent of Phase 4**: US1 ships value alone.
- **T017 → T024–T026**: deleting release-drafter breaks doc links, so the docs must be updated in the same change.

## Deferred

- **US3 (curated release notes)** is not implemented here. `CHANGELOG.md` covers every release; the curated prose page is optional and applies to notable releases only.
- **Single-branch model** is specified separately as `003-collapse-develop-branch`. This feature works under either model.
