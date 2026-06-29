# ADR-0003: Synchronous-Only SDK Usage

**Status**: Accepted
**Date**: 2026-02-25
**Source**: `.specify/memory/constitution.md` (Principle IV) — backfilled from existing code

## Context

The `infrahub-sdk` ships both an asynchronous client (`InfrahubClient`) and a
synchronous one (`InfrahubClientSync`). Ansible modules, action plugins, and
inventory/lookup plugins all execute in a synchronous context — Ansible invokes
them as blocking calls and expects a result dict (or populated inventory) when
they return. Introducing `async`/`await` would mean managing an event loop
inside each plugin and offers no benefit, since the collection issues API calls
serially within a single task.

## Decision

Use `InfrahubClientSync` exclusively. The async `InfrahubClient` is never used.

- `InfrahubclientWrapper` constructs and holds an `InfrahubClientSync`; all
  wrapper methods block until completion.
- The `infrahub-sdk` dependency is pinned `>=1.5, <2.0` with the `[all]` extras,
  which include synchronous support.
- No plugin defines `async def` entry points or runs an event loop.

## Consequences

- Plugins stay simple — straight-line synchronous code with no loop management.
- Aligns with Ansible's execution model; results are available on return.
- Throughput is bounded by serial API calls; this is acceptable for the
  collection's workloads and is the lever tracked separately for inventory
  fetch optimization.
- Contributors must select the sync variant of any new SDK call. The sync-only
  rule is reiterated in
  [../knowledge/infrahub-sdk-usage.md](../knowledge/infrahub-sdk-usage.md).

## Alternatives Considered

- **Async `InfrahubClient` with an event loop per plugin**: rejected — adds
  loop-management complexity to every plugin for no gain in a synchronous
  Ansible context.
- **Mixed sync/async depending on plugin**: rejected — two client lifecycles and
  two error-handling paths for no clear benefit.
