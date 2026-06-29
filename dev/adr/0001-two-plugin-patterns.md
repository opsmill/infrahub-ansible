# ADR-0001: Two Plugin Patterns (Module-Utils vs Action Plugin)

**Status**: Accepted
**Date**: 2026-02-25
**Source**: `.specify/memory/constitution.md` (Principle II) — backfilled from existing code

## Context

Every Ansible operation in this collection is exposed as a module under
`plugins/modules/`, but the modules differ sharply in what they do. Some
(`node`, `branch`) perform stateful CRUD that must be idempotent, support
`check_mode`, and emit `--diff` output. Others (`query_graphql`,
`artifact_fetch`, `artifact_generate`, `object_file_fetch`, `schema`) are
read-mostly operations against the Infrahub API that do not map cleanly onto
present/absent state. Forcing both into a single execution model would either
saddle read-only queries with unused idempotency machinery or strip stateful
modules of the state tracking they need.

## Decision

Support two distinct implementation patterns, chosen per module:

- **Module-utils pattern** — for stateful CRUD. The module stub in
  `plugins/modules/` builds an `AnsibleModule` from `deepcopy(INFRAHUB_ARG_SPEC)`
  and delegates to an `InfrahubModule` subclass in `plugins/module_utils/`
  (`NodeModule`, `BranchModule`). These subclasses implement `run()`, support
  `state` (present/absent), `check_mode`, and `--diff` via the base class's
  `_ensure_object_exists` / `_ensure_object_absent` and diff helpers.
- **Action plugin pattern** — for read-mostly operations. The module stub
  carries documentation and the arg spec; an `ActionModule` in `plugins/action/`
  runs the real logic controller-side, instantiating `InfrahubclientWrapper`
  directly and returning a result dict.

**Decision criteria**: use the module-utils pattern for anything requiring
idempotency and state management; use the action plugin pattern for read-only
queries or operations that cannot be made idempotent.

## Consequences

- Contributors must classify a new module up front. The procedure is documented
  in [../guides/creating-a-module.md](../guides/creating-a-module.md) (Step 2a
  vs 2b), and the patterns are detailed in
  [../knowledge/plugin-patterns.md](../knowledge/plugin-patterns.md).
- Both paths share the same SDK wrapper and credential handling, so divergence
  is contained to the execution model, not the API surface.
- `node` and `branch` are the only module-utils modules today; the remaining
  modules use action plugins.

## Alternatives Considered

- **Single module-utils path for everything**: rejected — read-only queries gain
  no benefit from state/diff machinery and would need awkward no-op semantics.
- **Single action-plugin path for everything**: rejected — action plugins have no
  built-in idempotency or `--diff` support, which `node`/`branch` require.
