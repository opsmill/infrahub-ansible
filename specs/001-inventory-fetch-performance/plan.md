# Implementation Plan: Dynamic Inventory Fetch Performance

**Branch**: `perf/inventory-projection-and-peer-batching` (feature id `001-inventory-fetch-performance`) | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-inventory-fetch-performance/spec.md`

## Summary

Cut the cost of building a dynamic inventory from *proportional to the database* to *proportional to what was asked for*, without changing a single byte of the inventory produced.

Four defects compounded into the reported slowness: related nodes were fetched a whole type at a time rather than by the ids actually referenced; the attribute selection a user wrote was never translated into a narrower request; any attribute that came back empty triggered a refetch of the node that owned it, one request per node; and the cache key ignored the branch and the node selection. The refetch turned out to be load-bearing — it was the only thing making attributes resolve when a relationship declares a broad peer type — so removing it required replacing it with a bounded, batched warm-up pass.

**Status of this plan**: all 20 functional requirements are implemented. Nineteen shipped in PR #374, measured and green. The twentieth, **FR-020 / SC-009** — a run reporting its own cost at raised verbosity — was added during `/speckit.clarify` and ships in PR #381, built to the design Phase 0 research below settled.

## Technical Context

**Language/Version**: Python >=3.11, <3.15 (`pyproject.toml`)

**Primary Dependencies**: `ansible-core>=2.19.11rc1`; `infrahub-sdk[all]>=1.19.0,<2.0` (synchronous client only)

**Storage**: N/A for the fetch path. Inventory results may be persisted through Ansible's own cache plugin interface (`jsonfile` by default); this feature only defines the cache *key*, never the backend.

**Testing**: `pytest` unit tests with a mocked SDK client; `ansible-test sanity` for plugin compliance; `pytest` integration tests against a live Infrahub via `infrahub-testcontainers`, split by marker into `integration` and `measurement`. Neither gates a pull request: both run on the nightly schedule and manual dispatch only, because the schema-convergence step is too slow for a standard runner. PRs are gated by `ansible-test sanity`, `ansible-lint` and the unit-test job

**Target Platform**: Ansible controller (Linux, macOS)

**Project Type**: Ansible collection — inventory plugin plus shared `module_utils`

**Performance Goals**: The invariant of FR-001 — request count determined by node types, pages, and distinct related-node types, never by host count. Measured on a ~650-host estate: 102.71s → 3.23s, 700 → 15 requests, 3758 KB → 1555 KB.

**Constraints**: Output must be byte-identical to the previous behaviour (FR-018). Synchronous SDK only. No new user-facing configuration option. All Infrahub access mediated by `InfrahubclientWrapper`.

**Scale/Scope**: Measured at 652 hosts (one type) and 1508 hosts (two types). No maximum estate size is specified — see the spec's Assumptions on why a host-count ceiling would mislead.

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.1.0.*

| Principle | Gate | Verdict |
|---|---|---|
| I — Ansible Collection Standards | New `module_utils` files carry the copyright header, GPLv3 reference, `from __future__` imports, and `__metaclass__ = type`; `ansible-test sanity` passes | **PASS** — verified on `projection.py` and `peers.py`; sanity matrix green on PR #374 |
| II — Two Plugin Patterns | No new plugin; no hybrid pattern introduced | **PASS** — the inventory plugin keeps its shape; new code is shared `module_utils` |
| III — Idempotency and State Management | Applies to modules that mutate Infrahub | **N/A** — the inventory path is read-only, makes no mutations, and reports no `changed` |
| IV — SDK Abstraction Layer | All API access through `InfrahubclientWrapper`; no ad-hoc `InfrahubClientSync`; sync only; conditional import guard | **PASS WITH DEVIATION** — see Complexity Tracking. Fetching goes through the wrapper (`PeerWarmer` is handed `self.client.fetch_nodes`). Reads of the client's *node store* and `pagination_size` reach past the wrapper; this pattern pre-dates the feature and was extended by it |
| V — Test Coverage and Quality Gates | Sanity + unit + integration; `invoke generate-doc` after any docstring change | **PASS** — 106 unit tests, 14 integration tests; the `timeout` docstring default change (10 → 60) was followed by `invoke generate-doc` |

### Post-design re-check

Re-evaluated after Phase 1. The one design decision this plan introduces — a counting `Recorder` passed
as `Config.custom_recorder` from `InfrahubclientWrapper` (research.md R1) — **improves** Principle IV
compliance rather than straining it: the wrapper stays the sole constructor and configurer of the SDK
client, and the rejected alternative (reassigning `client.execute_graphql` at runtime) was the one that
would have bypassed it. No new gate violations. The Complexity Tracking entries below are unchanged from
the pre-Phase-0 evaluation.

**Constitution staleness noted (not a violation of this feature):** the constitution's Constraints section states Python `>=3.10,<3.14`, `ansible-core>=2.17.7rc1`, and `infrahub-sdk>=1.5,<2.0`. The repository actually pins `>=3.11,<3.15`, `>=2.19.11rc1`, and `>=1.19.0,<2.0`. This feature complies with the real pins. Reconciling the constitution is out of scope here and belongs in an explicit constitution update.

## Project Structure

### Documentation (this feature)

```text
specs/001-inventory-fetch-performance/
├── plan.md              # This file
├── spec.md              # Feature specification (20 FR, 9 SC, 4 clarifications)
├── research.md          # Phase 0 output — resolves the FR-020 design question
├── data-model.md        # Phase 1 output — entities and their real carriers
├── quickstart.md        # Phase 1 output — how to reproduce and verify the numbers
├── contracts/
│   └── inventory-options.md   # The plugin's user-facing contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (all items pass)
└── tasks.md             # Phase 2 output — NOT created by /speckit.plan
```

### Source Code (repository root)

```text
plugins/
├── inventory/
│   └── inventory.py            # Cache key (FR-011..FR-013), timeout default (FR-017), display wiring
└── module_utils/
    ├── infrahub_utils.py       # InfrahubclientWrapper, InfrahubNodesProcessor, HostFetch; orchestration
    ├── projection.py           # NodeProjection — user selection to SDK include/exclude (FR-003, FR-004)
    └── peers.py                # PeerWarmer, RefillLedger — bounded batched peer loading (FR-005..FR-010)

tests/
├── unit/plugins/
│   ├── inventory/test_inventory_cache_key.py
│   └── module_utils/
│       ├── test_projection.py
│       ├── test_peers.py
│       └── test_fetch_and_process_resolution.py
└── integration/
    ├── inventory/schema.py                                  # generic-peer test schema
    └── processor/
        ├── test_fetch_and_process_integration.py            # nightly: correctness + gross-regression counter
        └── test_fetch_roundtrip_measurement.py              # scheduled: per-shape measured budgets
```

**Structure Decision**: No new structure. The feature extracted two focused, SDK-free modules (`projection.py`, `peers.py`) out of `infrahub_utils.py` — both are pure enough to unit-test without a client, which is why the projection and batching rules have direct tests rather than only end-to-end ones. Everything else edits files that already existed.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle IV: reads of `self.client.client.store` and `self.client.client.pagination_size` reach past `InfrahubclientWrapper` to the raw SDK client (7 sites; 4 already existed on `develop`, 3 added here) | Peer resolution reads nodes out of the SDK's own `NodeStore` — that store is where `prefetch_relationships` deposits peers, and there is no wrapper-level view of it. Chunking peer ids correctly requires knowing the client's `pagination_size` | Mirroring the store behind the wrapper would mean maintaining a second copy of state the SDK already owns, and would drift the moment the SDK changes how peers land. Passing a hardcoded page size would silently break for anyone who configures a different one |
| FR-020 requires a query count the wrapper cannot see | The SDK paginates *inside* `client.filters()`, below the wrapper, so no wrapper-level counter can report true round-trips | Reporting only wrapper-level fetch operations would under-report by exactly the amount that matters (pages). See `research.md` for the resolution |
