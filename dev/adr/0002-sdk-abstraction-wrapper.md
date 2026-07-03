# ADR-0002: SDK Abstraction Behind InfrahubclientWrapper

**Status**: Accepted
**Date**: 2026-02-25
**Source**: `.specify/memory/constitution.md` (Principle IV) — backfilled from existing code

## Context

This collection talks to Infrahub exclusively through the `infrahub-sdk`
package. Without a discipline around how the SDK is used, every plugin —
modules, action plugins, the inventory source, and the lookup plugin — would
independently construct `InfrahubClientSync`, assemble its `Config`, translate
SDK exceptions into Ansible errors, and reimplement node/branch/GraphQL calls.
That duplication drifts as the SDK evolves and scatters error handling across
the codebase.

## Decision

Route all Infrahub API access through a single wrapper, `InfrahubclientWrapper`,
defined in `plugins/module_utils/infrahub_utils.py`.

- The wrapper builds the SDK `Config` (address, `api_token`, `default_branch`,
  `timeout`, `tls_insecure`) and owns the `InfrahubClientSync` instance. Callers
  never instantiate the SDK client directly.
- It exposes intent-named methods — `fetch_single_node`, `fetch_nodes`,
  `create_node`, `save_node`, `delete_node`, `fetch_single_schema`,
  `fetch_branch`, `create_branch`, `delete_branch`, `execute_graphql`,
  `fetch_single_artifact`, `generate_artifact`.
- Higher-level orchestration sits on top: the `InfrahubModule` base class for
  stateful modules, and the `InfrahubBaseProcessor` /
  `InfrahubNodesProcessor` / `InfrahubQueryProcessor` classes for the inventory
  and lookup plugins.
- SDK exceptions are mapped to Ansible errors in one place via
  `handle_infrahub_exceptions_decorator` (`plugins/module_utils/exception.py`),
  not at each call site.

## Consequences

- A single seam absorbs SDK API changes; call sites stay stable.
- New plugins inherit consistent credential handling, branch awareness, and
  error mapping for free. Usage is documented in
  [../knowledge/infrahub-sdk-usage.md](../knowledge/infrahub-sdk-usage.md) and
  the overall data flow in [../knowledge/architecture.md](../knowledge/architecture.md).
- The wrapper is shared core code (~1500 lines); changes to it affect every
  plugin and warrant extra review.

## Alternatives Considered

- **Direct `InfrahubClientSync` use in each plugin**: rejected — duplicates
  config assembly and error handling, and couples every plugin to the SDK's
  surface.
- **A thin pass-through that only constructs the client**: rejected — leaves
  exception mapping and node/branch/query orchestration to each caller, the very
  duplication this decision avoids.
