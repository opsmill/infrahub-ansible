---

description: "Task list template for Ansible collection plugin development"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Organization**: Tasks follow the Ansible module creation lifecycle from `dev/guides/creating-a-module.md`.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- `plugins/modules/` — module stubs (DOCUMENTATION/EXAMPLES/RETURN + argument spec)
- `plugins/action/` — action plugins (controller-side execution)
- `plugins/module_utils/` — shared logic classes (InfrahubModule subclasses)
- `plugins/doc_fragments/` — reusable documentation fragments
- `tests/unit/plugins/` — unit tests (pytest with mocked SDK)
- `tests/integration/targets/` — integration test playbooks
- `docs/` — Docusaurus documentation site

<!--
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.

  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Plugin Design section from spec.md (pattern choice, API interactions)
  - Feature requirements from plan.md
  - Constitution gates from plan.md

  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Plugin Scaffold

**Purpose**: Create the module stub and establish the plugin structure

- [ ] T001 Create module stub at `plugins/modules/<name>.py` with complete `DOCUMENTATION`, `EXAMPLES`, `RETURN` docstrings and argument spec
- [ ] T002 [P] Determine plugin pattern (module_utils for stateful CRUD or action plugin for controller-side calls) based on spec's Plugin Design section
- [ ] T003 [P] Update `plugins/doc_fragments/fragments.py` if new shared options are needed

**Checkpoint**: Module stub passes `ansible-test sanity` and `ansible-doc` can parse it

---

## Phase 2: Core Implementation

**Purpose**: Implement the plugin logic following the chosen pattern

### If module_utils pattern (stateful CRUD):

- [ ] T004 Create module utils class at `plugins/module_utils/<name>.py` inheriting from `InfrahubModule`
- [ ] T005 Implement `run()` method with state routing (`_ensure_object_exists` / `_ensure_object_absent`)
- [ ] T006 Implement conditional `HAS_INFRAHUBCLIENT` import and runtime check
- [ ] T007 Implement `check_mode` support — skip all mutations when `module.check_mode`
- [ ] T008 Implement `--diff` support via `_build_diff(before, after)`
- [ ] T009 Update module stub to import and call the module utils class with `deepcopy(INFRAHUB_ARG_SPEC)`

### If action plugin pattern (controller-side):

- [ ] T020 Create action plugin at `plugins/action/<name>.py` inheriting from `ActionBase`
- [ ] T021 Implement `run()` method with credential extraction, validation, and API calls
- [ ] T022 Implement conditional `HAS_INFRAHUBCLIENT` import and runtime check
- [ ] T023 Implement error handling with `handle_infrahub_exceptions_decorator` or try/except

### Common:

- [ ] T010 [P] Add or extend `InfrahubclientWrapper` methods if new SDK operations are needed
- [ ] T011 Verify `invoke lint` passes (Ruff check + format)

**Checkpoint**: Plugin executes successfully against a running Infrahub instance

---

## Phase 3: Test Suite

**Purpose**: Ensure quality through all three test tiers

### Sanity

- [ ] T012 Run `invoke tests-sanity` and fix any violations

### Unit Tests

- [ ] T013 [P] Create unit test file at `tests/unit/plugins/modules/test_<name>.py` (or `test_<name>.py` for module_utils)
- [ ] T024 [P] [US1] Unit test: basic creation (`state: present`, object does not exist → `changed: true`)
- [ ] T025 [P] [US1] Unit test: idempotent no-change (`state: present`, object already matches → `changed: false`)
- [ ] T026 [P] [US1] Unit test: update (`state: present`, object exists but differs → `changed: true`)
- [ ] T027 [P] [US1] Unit test: deletion (`state: absent`, object exists → `changed: true`)
- [ ] T028 [P] [US1] Unit test: absent no-op (`state: absent`, object does not exist → `changed: false`)
- [ ] T029 [P] Unit test: error handling (SDK exceptions mapped to Ansible errors)
- [ ] T030 [P] Unit test: `check_mode` (no API calls made, correct `changed` prediction)

### Integration Tests

- [ ] T031 Create integration test playbook at `tests/integration/targets/<name>/tasks/main.yml`

**Checkpoint**: All tests pass — `invoke tests-all`

---

## Phase 4: Documentation and Release

**Purpose**: Generate docs, update changelog, final validation

- [ ] T032 Run `invoke generate-doc` to create MDX reference page
- [ ] T033 Verify generated docs render correctly with `invoke docusaurus`
- [ ] T034 Add changelog entry to `CHANGELOG.rst` noting the new plugin and version
- [ ] T035 Run full test suite: `invoke tests-all`

**Checkpoint**: Plugin is complete and ready for PR

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 (Scaffold)**: No dependencies — start immediately
- **Phase 2 (Core Implementation)**: Depends on Phase 1 completion
- **Phase 3 (Test Suite)**: Depends on Phase 2 completion; all unit tests marked [P] can run in parallel
- **Phase 4 (Documentation and Release)**: Depends on Phases 2 and 3 completion

### Within Each Phase

- Sanity tests should be run after every new Python file
- Unit test files can be created in parallel (different files, no dependencies)
- Integration tests require a running Infrahub instance

### Parallel Opportunities

- All Phase 1 tasks marked [P] can run in parallel
- All unit tests in Phase 3 marked [P] can run in parallel
- Doc generation and changelog (Phase 4) can run in parallel

---

## Notes

- [P] tasks = different files, no dependencies — can run in parallel
- [Story] label maps task to specific user story for traceability
- Commit after each phase completion
- Run `invoke lint` after every Python file change
- Follow `dev/guides/creating-a-module.md` for detailed code patterns and examples
- Reference `dev/knowledge/plugin-patterns.md` for boilerplate and conventions
