---

description: "Task list for Dynamic Inventory Fetch Performance"
---

# Tasks: Dynamic Inventory Fetch Performance

**Input**: Design documents from `/specs/001-inventory-fetch-performance/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks ARE included. This feature's central risk is a fast-but-wrong inventory, and the spec makes identical output a hard requirement (FR-018), so every story carries the test that proves it.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- `- [X]` marks a task **already delivered** in PR #374, verified and green
- `- [ ]` marks **forward work**

## Delivery status

This is a retroactive task list. **All 20 of the spec's functional requirements are implemented and
passing CI.** Phases 1–7 shipped in PR #374; Phase 8 — FR-020 / SC-009, added during
`/speckit.clarify` — ships in PR #381. Phases 1–7 record the earlier work so coverage is traceable
rather than assumed. What remains unchecked is Phase 9 repo hygiene, which gates nothing.

Read `- [X]` as "requirement covered and verified", not as "task someone should do".

## Path Conventions

Ansible collection layout: plugins under `plugins/`, tests under `tests/unit/` and `tests/integration/`.
Paths below are repository-relative, per plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Carve the two SDK-free modules out of `infrahub_utils.py` so projection and batching rules are unit-testable without a client

- [X] T001 Create `plugins/module_utils/projection.py` with collection boilerplate (Opsmill copyright, GPLv3 reference, `from __future__` imports, `__metaclass__ = type`)
- [X] T002 [P] Create `plugins/module_utils/peers.py` with the same boilerplate, keeping `Callable` under `TYPE_CHECKING` so no SDK import is needed at runtime
- [X] T003 [P] Register both modules in the Key Files table in `plugins/AGENTS.md` and update the module_utils count

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Changes every story depends on

**⚠️ CRITICAL**: No story work can begin until this phase is complete

- [X] T004 Add a `parallel: bool = True` parameter to `fetch_nodes` in `plugins/module_utils/infrahub_utils.py` so peer batches can opt out of the parallel pager
- [X] T005 Convert `HostFetch` from a `NamedTuple` to a `@dataclass` in `plugins/module_utils/infrahub_utils.py` (its dict/list fields are mutated in place during the fetch loop)
- [X] T006 Resolve host schemas with `fetch_single_schema(kind=..., raise_when_missing=False)` in `_fetch_host_nodes` in `plugins/module_utils/infrahub_utils.py`, so an unknown kind is skipped regardless of whether the wrapper's exception decorator is installed
- [X] T007 [P] Raise the `timeout` default from 10 to 60 in the `DOCUMENTATION` block of `plugins/inventory/inventory.py`, then run `invoke generate-doc` (FR-017; constitution Principle V)
- [X] T008 Delete the now-unreachable `get_related_nodes` from `plugins/module_utils/infrahub_utils.py`

**Checkpoint**: Foundation ready — story work can proceed

---

## Phase 3: User Story 1 - A large estate builds in seconds, not minutes (Priority: P1) 🎯 MVP

**Goal**: Make fetch cost track what was asked for rather than database size, with byte-identical output

**Independent Test**: Build an inventory of ~650 hosts with attributes reached through relationships; measure wall-clock and count requests; diff the produced inventory against the previous behaviour

### Tests for User Story 1

- [X] T009 [P] [US1] Rewrite resolution unit tests in `tests/unit/plugins/module_utils/test_fetch_and_process_resolution.py`, stubbing `wrapper.client.store.get` and `wrapper.client.pagination_size`
- [X] T010 [P] [US1] Add per-shape measured round-trip budgets in `tests/integration/processor/test_fetch_roundtrip_measurement.py`, marked `measurement` so the heavy schema-convergence run stays off the PR gate
- [X] T011 [P] [US1] Add a gross-regression request counter to `tests/integration/processor/test_fetch_and_process_integration.py`, with the budget derived from `pagination_size` rather than hardcoded

### Implementation for User Story 1

- [X] T012 [US1] Build a per-node-type `NodeProjection` in `_fetch_host_nodes` in `plugins/module_utils/infrahub_utils.py` and carry it on `HostFetch.projections`
- [X] T013 [US1] Guard the refill on `node_attr.value is None` in `_resolve_schema_attribute` in `plugins/module_utils/infrahub_utils.py`, so `False`, `0`, and `""` count as present values (FR-002)
- [X] T014 [US1] Orchestrate warm → resolve → refill → resolve in `fetch_and_process` in `plugins/module_utils/infrahub_utils.py`, sharing `warmer.loaded` with the ledger so a fully-fetched peer is never re-queued

**Checkpoint**: Inventory of ~650 hosts builds in 3.23s (was 102.71s) at 15 requests (was 700), output byte-identical

---

## Phase 4: User Story 2 - Asking for less costs less (Priority: P2)

**Goal**: Translate the user's attribute selection into a request the SDK actually narrows

**Independent Test**: Build the same inventory with and without a narrow selection; the narrow run transfers measurably less

### Tests for User Story 2

- [X] T015 [P] [US2] Unit tests for projection build, complement, and `projected()` in `tests/unit/plugins/module_utils/test_projection.py`

### Implementation for User Story 2

- [X] T016 [US2] Implement `NodeProjection.build` in `plugins/module_utils/projection.py`: compute the complement of the selection's roots against the schema and pass it as `exclude`, since `include` alone does not narrow (research.md R5)
- [X] T017 [P] [US2] Preserve the historical wide query when no selection is given (`narrowed = False`) in `plugins/module_utils/projection.py` (FR-004)
- [X] T018 [P] [US2] Short-circuit bare relationships in `_resolve_one_relationship` and `_resolve_many_relationship` in `plugins/module_utils/infrahub_utils.py` — return peer ids without fetching peers (FR-010)

**Checkpoint**: Narrow selections transfer less; wide selections unchanged; US1 still passing

---

## Phase 5: User Story 3 - Attributes on related nodes always arrive (Priority: P3)

**Goal**: Resolve attributes through relationships that declare a broad peer type, without one request per peer

**Independent Test**: Model a relationship whose declared peer type omits the requested attribute; the attribute must resolve, within budget

### Tests for User Story 3

- [X] T019 [P] [US3] Unit tests for `PeerWarmer` and `RefillLedger` in `tests/unit/plugins/module_utils/test_peers.py`, with the fake fetch returning a node per requested id and an optional `found` set
- [X] T020 [P] [US3] Add a generic `TestingLocation` plus concrete `TestingSite` to `tests/integration/inventory/schema.py` so a declared-generic peer can be exercised end to end
- [X] T021 [P] [US3] Add `test_generic_peer_attribute_resolves_and_stays_bounded` to `tests/integration/processor/test_fetch_roundtrip_measurement.py`

### Implementation for User Story 3

- [X] T022 [US3] Implement `PeerWarmer.collect` in `plugins/module_utils/peers.py`: compute nested roots per **node type** (not per node), and skip peers already satisfied in the store via `_is_satisfied`
- [X] T023 [US3] Implement `PeerWarmer.warm` in `plugins/module_utils/peers.py`: chunk ids at `pagination_size - 1` (research.md R3), fetch by `{"ids": chunk}` with `parallel=False`, and record only ids present in the response (FR-008)
- [X] T024 [P] [US3] Make `RefillLedger.record` projection-aware in `plugins/module_utils/peers.py` so an attribute nobody asked for is never queued
- [X] T025 [US3] Wire `_warm_peers` in `plugins/module_utils/infrahub_utils.py` to collect then warm, with `Order(disable=True)` and no schema fetch for peer kinds

**Checkpoint**: Generic-peer attributes resolve within a bounded request count; the per-node refetch is gone

---

## Phase 6: User Story 4 - Cached inventories do not collide (Priority: P4)

**Goal**: Key each cache entry to the request that produced it

**Independent Test**: Build cache identities for definitions differing only by branch, and only by node selection; all must differ

### Tests for User Story 4

- [X] T026 [P] [US4] Unit tests for cache-key distinctness in `tests/unit/plugins/inventory/test_inventory_cache_key.py`

### Implementation for User Story 4

- [X] T027 [US4] Hash endpoint, branch, node selection, and `CACHE_SCHEMA_VERSION` into `_cache_key` in `plugins/inventory/inventory.py`, annotating the local for mypy (FR-011, FR-012)
- [X] T028 [US4] Call `_store_in_cache` only when `need_to_load_from_api` in `plugins/inventory/inventory.py` (FR-013)

**Checkpoint**: Two definitions differing only in branch or selection no longer share a cache entry

---

## Phase 7: User Story 5 - A failed fetch says so (Priority: P5)

**Goal**: Skip what fails, report when everything fails, never hand back a silently empty inventory

**Independent Test**: Run one definition with a valid and an invalid node type, and another with only invalid types

### Tests for User Story 5

- [X] T029 [P] [US5] Add `test_unknown_kind_is_skipped_not_fatal` to `tests/integration/processor/test_fetch_and_process_integration.py`, built through `__new__` so the skip cannot come from the exception decorator

### Implementation for User Story 5

- [X] T030 [US5] Record per-type failures in `HostFetch.failures` and warn on an unresolvable schema in `_fetch_host_nodes` in `plugins/module_utils/infrahub_utils.py` (FR-014)
- [X] T031 [US5] Raise a `RuntimeError` naming every failed type when no nodes were fetched and at least one type failed, in `fetch_and_process` in `plugins/module_utils/infrahub_utils.py` (FR-015); return cleanly when nothing failed (FR-016)
- [X] T032 [US5] Pass an `on_error` callback into `PeerWarmer` from `fetch_and_process` in `plugins/module_utils/infrahub_utils.py` that warns and continues, leaving hosts produced with the attribute empty (FR-019)

**Checkpoint**: All five stories independently verified; 106 unit tests and 14 integration tests green

---

## Phase 8: Cross-Cutting - Run cost reporting (FR-020, SC-009) ✅ COMPLETE

**Purpose**: Let a run state its own cost at raised verbosity, so the next field report arrives as a number instead of an anecdote. This is the only unimplemented requirement in the spec.

**Design**: research.md R1 — a counting `Recorder` passed as `Config.custom_recorder` from `InfrahubclientWrapper`. Counts at the true HTTP boundary, below the SDK's pagination, using a supported extension point rather than a monkeypatch.

**Independent Test**: Run an inventory at `-v` against a known estate and confirm the reported request count matches an independent count of HTTP responses; run at default verbosity and confirm silence; run fully from cache and confirm nothing is reported.

- [X] T033 Decide whether the count is reported once per run or once per node type, and record the decision in `specs/001-inventory-fetch-performance/research.md` under R1 (research.md flags this as the one open sub-question; per-type aids diagnosis, a single total is what SC-009 literally asks for)
- [X] T034 [P] Create `plugins/module_utils/metrics.py` with collection boilerplate and a `RequestCounter` implementing the SDK's `Recorder` protocol — a `record(response)` that increments a counter, with the `httpx.Response` annotation under `TYPE_CHECKING` so no SDK import is required at runtime
- [X] T035 [P] Unit tests for `RequestCounter` in `tests/unit/plugins/module_utils/test_metrics.py`: counts increment per call, start at zero, and the module imports without `infrahub_sdk` installed
- [X] T036 Pass the counter as `custom_recorder` in both `Config(...)` constructions in `plugins/module_utils/infrahub_utils.py` (around lines 119 and 126) and expose it on `InfrahubclientWrapper`
- [X] T037 Return the peer-batch count from `_warm_peers` in `plugins/module_utils/infrahub_utils.py` instead of discarding `warmer.warm(...)`'s return value, and total the related nodes loaded
- [X] T038 Emit the report from `fetch_and_process` in `plugins/module_utils/infrahub_utils.py` via `_handle_display(level="INFO")`, which maps to `display.v()` — raised verbosity only, silent at default (FR-020)
- [X] T039 [P] Add a unit test in `tests/unit/plugins/module_utils/test_fetch_and_process_resolution.py` asserting the report is emitted at INFO and absent at default verbosity
- [X] T040 [P] Assert the reported count matches the independently-counted round-trips in `tests/integration/processor/test_fetch_and_process_integration.py`, reusing the existing `count_graphql` helper as the independent reference (SC-009)
- [X] T041 Document the diagnostics behaviour in `dev/knowledge/inventory-and-lookup.md` and confirm `specs/001-inventory-fetch-performance/contracts/inventory-options.md` no longer marks FR-020 as unimplemented
- [X] T042 Update the spec's Status line and `checklists/requirements.md` notes in `specs/001-inventory-fetch-performance/` to drop the "FR-020 not yet implemented" caveat

**Checkpoint**: FR-020 and SC-009 satisfied; the spec becomes fully retroactive

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T043 [P] Fix the `HAS_GIT: unbound variable` failure at `.specify/scripts/bash/update-agent-context.sh:147`, and make feature resolution fall back to `.specify/feature.json` rather than requiring a numbered git branch
- [ ] T044 [P] Trim the run-on "Active Technologies" entry the agent-context script appended to `CLAUDE.md`, or move the generated block inside the `<!-- SPECKIT -->` markers so it stays managed
- [ ] T045 Reconcile the stale Constraints section of `.specify/memory/constitution.md` (Python `>=3.10,<3.14`, `ansible-core>=2.17.7rc1`, `infrahub-sdk>=1.5,<2.0`) against the real pins in `pyproject.toml`, as an explicit constitution amendment

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies
- **Phase 2 (Foundational)** → depends on Phase 1; blocks Phases 3–7
- **Phase 3 (US1)** → depends on Phase 2
- **Phases 4–7 (US2–US5)** → depend on Phase 2; independent of each other
- **Phase 8 (FR-020)** → depends on Phases 2 and 5. It reads `_warm_peers`' return value, so T037 assumes Phase 5's `_warm_peers` exists — already true
- **Phase 9 (Polish)** → independent of everything; T043–T045 are repo hygiene, not feature work

### User Story Dependencies

- **US1 (P1)** is the MVP and stands alone
- **US2, US4, US5** are independent of US1 and of each other
- **US3** shares `peers.py` with US1's orchestration; US1's checkpoint depends on US3's warming existing, because removing the per-node refetch without it makes generic-peer attributes silently empty (research.md R4). Implement US3's warming before declaring US1 done

### Within Each User Story

Tests → models/pure modules → orchestration in `infrahub_utils.py` → verification.

### Parallel Opportunities

- T001/T002/T003 — three different files
- T009/T010/T011 — three different test files
- Phases 4, 6, 7 touch disjoint files and could run concurrently once Phase 2 lands
- **Phase 8**: T034 and T035 are parallel (new module + its test). T036–T038 are sequential — all three edit `infrahub_utils.py`. T039/T040 are parallel afterwards

## Parallel Example: Phase 8

```text
T033 (decide reporting granularity)      # blocks nothing but shapes T038
  ├─ T034 [P] plugins/module_utils/metrics.py
  └─ T035 [P] tests/unit/plugins/module_utils/test_metrics.py
        ↓
T036 → T037 → T038                        # all in infrahub_utils.py, sequential
        ↓
  ├─ T039 [P] unit assertion
  └─ T040 [P] integration assertion
        ↓
T041 → T042                               # docs, then spec status
```

## Implementation Strategy

**Everything through Phase 8 is delivered.** Phases 1–7 shipped in PR #374 at 22/22 checks green.

Phase 8 was taken as the follow-up rather than folded back into #374 — 10 tasks across one new module
plus three edits to `infrahub_utils.py`, a small independently testable increment that left a green,
byte-identical-verified diff closed. It ships in PR #381, at which point the spec is fully retroactive.

Phase 9 is repo hygiene and gates nothing.
