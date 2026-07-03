# Processors and the Standard Argument Spec

Two shared building blocks in `plugins/module_utils/infrahub_utils.py` are reused
across every plugin: the `INFRAHUB_ARG_SPEC` standard argument spec and the
processor class hierarchy. This page describes both. For the SDK wrapper they sit
on top of, see [infrahub-sdk-usage.md](infrahub-sdk-usage.md); for how the
inventory and lookup plugins drive the processors, see
[inventory-and-lookup.md](inventory-and-lookup.md).

## INFRAHUB_ARG_SPEC

`INFRAHUB_ARG_SPEC` is the connection-and-state argument spec shared by every
module. It is defined as a `dict(...)` and contains exactly five keys:

```python
INFRAHUB_ARG_SPEC = dict(
    api_endpoint=dict(type="str", required=False, fallback=(env_fallback, ["INFRAHUB_ADDRESS"])),
    token=dict(type="str", required=False, no_log=True, fallback=(env_fallback, ["INFRAHUB_API_TOKEN"])),
    state=dict(required=False, default="present", choices=["present", "absent"]),
    validate_certs=dict(type="bool", default=True),
    timeout=dict(required=False, type="int", default=10),
)
```

Three things to note:

- **Environment fallbacks** — `api_endpoint` and `token` fall back to
  `INFRAHUB_ADDRESS` and `INFRAHUB_API_TOKEN` via Ansible's `env_fallback`, so
  credentials need not be passed as task parameters.
- **`no_log=True`** on `token` keeps the secret out of logs.
- **`state`** is present even though only the CRUD modules (`node`, `branch`)
  act on it; read-mostly modules carry it for a uniform interface.

### The deepcopy extension pattern

A module never mutates `INFRAHUB_ARG_SPEC` in place — that would leak its
module-specific keys into every other module sharing the dict. Instead each
module takes a `deepcopy` and extends the copy:

```python
from copy import deepcopy
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC

argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
argument_spec.update({ ... module-specific args ... })
```

This is the convention in `node.py`, `branch.py`, `schema.py`,
`artifact_generate.py`, and `object_file_fetch.py`. The same rule is stated in
`plugins/AGENTS.md`.

## Processor hierarchy

Processors turn a request (a set of nodes to fetch, or a GraphQL query) into a
shaped result dictionary by calling the SDK through `InfrahubclientWrapper`.
There is one base class and two concrete subclasses:

```text
InfrahubBaseProcessor
├── InfrahubNodesProcessor   # node-set fetch + relationship resolution
└── InfrahubQueryProcessor   # raw GraphQL query execution
```

### InfrahubBaseProcessor

Holds the shared machinery both subclasses need: schema-attribute resolution
(`get_attributes_for_schema`, `_resolve_schema_attribute`), relationship
resolution (`_resolve_many_relationship`, `_resolve_one_relationship`,
`get_related_nodes`), the node-to-dict mapper (`resolve_node_mapping`), a
recursive `deep_update`, and host-name helpers (`resolve_dotted_path`,
`resolve_hostnames`). It does not define `fetch_and_process` itself.

### InfrahubNodesProcessor

`fetch_and_process(nodes, prefetch_relationships=True, include_id=True)` fetches
a set of nodes by kind and renders each into a dictionary, optionally
prefetching relationships. It is the processor used wherever the unit of work is
"a set of objects":

- `plugins/inventory/inventory.py` — builds the dynamic inventory.
- `plugins/module_utils/node.py` — the `NodeModule` read path.

### InfrahubQueryProcessor

`fetch_and_process(query, variables=None, include_id=True)` executes a GraphQL
query (string or built query) and returns its result. It is used where the unit
of work is "a GraphQL query":

- `plugins/action/query_graphql.py` — the `query_graphql` action plugin.
- `plugins/lookup/lookup.py` — the GraphQL lookup plugin.

Both subclasses are constructed with `client=<InfrahubclientWrapper>` and an
optional `display`.

## Conditional-import stubs

All of these live behind the `HAS_INFRAHUBCLIENT` guard. When `infrahub-sdk` is
not importable, the module defines empty placeholder classes
(`InfrahubclientWrapper`, `InfrahubNodesProcessor`, `InfrahubQueryProcessor`,
`InfrahubModule`) so the file still imports cleanly for `ansible-test sanity`.
See [plugin-patterns.md](plugin-patterns.md) for the conditional-import
convention.
