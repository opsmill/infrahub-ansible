# Infrahub SDK Usage

This collection wraps the `infrahub-sdk` Python package to interact with the Infrahub API. All SDK usage goes through wrapper classes in `plugins/module_utils/infrahub_utils.py`.

## Dependency

```toml
# pyproject.toml
dependencies = [
    "infrahub-sdk[all]>=1.19.0,<2.0",
]
```

The `[all]` extras include sync support. This collection **only uses synchronous SDK methods** (`InfrahubClientSync`).

## InfrahubclientWrapper

The primary SDK wrapper. Instantiated in action plugins, module_utils classes, and the inventory/lookup plugins.

### Construction

```python
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    InfrahubclientWrapper,
)

client = InfrahubclientWrapper(
    api_endpoint="https://infrahub.example.com",
    token="api-token-here",
    branch="main",
    timeout=10,
    validate_certs=True,
    display=Display(),  # Ansible Display object for logging
)
```

Internally creates an `InfrahubClientSync` with a `Config`:

```python
config = Config(
    address=api_endpoint,
    api_token=token,
    default_branch=branch,
    timeout=timeout,
    tls_insecure=(not validate_certs),
)
self.client = InfrahubClientSync(config=config)
```

### Sync-Only Pattern

This collection is **synchronous only**. It uses `InfrahubClientSync` (not `InfrahubClient`). All methods block until completion. This is intentional — Ansible modules run in a synchronous execution context.

### Key Methods

**Node Operations:**

```python
# Fetch a single node (returns InfrahubNodeSync or None)
node = client.fetch_single_node(
    kind="InfraDevice",
    id=None,
    hfid=["device-name"],
    filters={"name__value": "router01"},
    branch="main",
    raise_when_missing=False,
)

# Fetch multiple nodes
nodes = client.fetch_nodes(
    kind="InfraDevice",
    filters={"name__value": "router01"},
    branch="main",
    populate_store=True,
    partial_match=False,
)

# Create a node
node = client.create_node(
    kind="InfraDevice",
    data={"name": {"value": "router01"}, "status": {"value": "active"}},
    branch="main",
)

# Save/delete (static methods taking node objects)
InfrahubclientWrapper.save_node(node, allow_upsert=False)
InfrahubclientWrapper.delete_node(node)
```

**Schema Operations:**

```python
schema = client.fetch_single_schema(kind="InfraDevice", branch="main")
schemas = client.fetch_schemas(branch="main")
```

**Branch Operations:**

```python
branches = client.fetch_branchs()  # Note: typo preserved from codebase
branch = client.fetch_branch(name="feature-branch")
client.create_branch(name="new-branch", description="...", sync_with_git=True)
client.delete_branch(name="old-branch")
```

**GraphQL:**

```python
result = client.execute_graphql(
    query="query { InfraDevice { edges { node { name { value } } } } }",
    variables={},
    branch="main",
)
```

**Artifacts:**

```python
# Fetch artifact content
artifact = client.fetch_single_artifact(
    filters={"name__value": "Startup Config"},
    branch="main",
)

# Trigger regeneration
result = client.generate_artifact(
    filters={"name__value": "Startup Config"},
    target_id="uuid-of-device",
    branch="main",
)
```

## InfrahubModule

Base class for modules that go through the module_utils path (not action plugins).

### Usage

```python
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    InfrahubModule,
    INFRAHUB_ARG_SPEC,
)


class NodeModule(InfrahubModule):
    def run(self):
        kind = self.data.get("kind")
        schema = self.wrapper.fetch_single_schema(kind=kind, branch=self.branch)
        self.object = self.wrapper.fetch_single_node(...)

        if self.state == "present":
            self._ensure_object_exists(kind, self.data.get("data"))
        else:
            self._ensure_object_absent(kind, self.data.get("data"))
```

### Key Properties and Methods

- `self.module` — the `AnsibleModule` instance
- `self.wrapper` — `InfrahubclientWrapper` instance (auto-created)
- `self.state` — `"present"` or `"absent"`
- `self.data` — module parameters dict
- `self.branch` — target branch name
- `self.result` — result dict (modified in place, passed to `exit_json`)
- `self.object` — current Infrahub node being operated on
- `_ensure_object_exists(kind, data)` — idempotent create/update
- `_ensure_object_absent(kind, data)` — idempotent delete
- `_build_diff(before, after)` — construct Ansible diff output

### Idempotency

The module tracks changes through:

1. Fetch existing object (by `id`, `hfid`, or filters)
2. Compare current state with desired state
3. Only make API calls if changes are needed
4. Report `changed: true/false` accurately

### HFID (Human-Friendly ID)

Infrahub nodes can be identified by UUID or HFID (a list of human-readable values). The module handles normalization:

```python
# UUID → passed directly
# HFID list → used for lookup
# Relationship with UUID → normalized to HFID for idempotent comparison
```

## Processor Classes

### InfrahubNodesProcessor

Used by the inventory plugin to fetch and transform nodes:

```python
processor = InfrahubNodesProcessor(
    client=client,
    display=Display(),
)
# Fetches nodes, resolves relationships, maps to dicts
results = processor.fetch_and_process(
    nodes={"InfraDevice": {"include": ["name", "status"], "exclude": [], "filters": {}}},
    prefetch_relationships=True,
    include_id=True,
)
```

### InfrahubQueryProcessor

Used by the lookup plugin and `query_graphql` action:

```python
processor = InfrahubQueryProcessor(
    client=client,
    display=Display(),
)
result = processor.fetch_and_process(
    query="query { ... }",
    variables={},
    include_id=False,
)
```

## Exception Handling

The `handle_infrahub_exceptions_decorator` wraps SDK calls with proper error mapping:

```python
from ansible_collections.opsmill.infrahub.plugins.module_utils.exception import (
    handle_infrahub_exceptions_decorator,
)

@handle_infrahub_exceptions_decorator(display=self.display)
def some_method(self):
    # SDK calls here — exceptions auto-mapped to display messages
```

Exception mapping:

| SDK Exception | Handling |
|--------------|----------|
| `GraphQLError` | Extract error messages, raise/display |
| `SchemaNotFoundError` | "Schema not found in Infrahub" |
| `BranchNotFoundError` | "Branch not found" |
| `ServerNotReachableError` | "Unable to connect to Infrahub" |
| `ServerNotResponsiveError` | "Infrahub not responding" |
| Generic `Exception` | Fallback with full message |

## Environment Variables

The SDK wrapper respects these environment variables as fallbacks:

| Variable | Purpose |
|----------|---------|
| `INFRAHUB_ADDRESS` | API endpoint URL |
| `INFRAHUB_API_TOKEN` | Authentication token |

## SDK Behaviours That Surprise

Each of these cost real debugging time. They are properties of `infrahub-sdk`, not of this collection,
so they can change under a version bump — re-verify rather than trusting this list blindly.

### `include` does not narrow a query

Only `exclude` narrows. `include` opts cardinality-many relationships *in*; it does not restrict the
attributes requested. Verified by rendering the query both ways: with and without `include`, the SDK
produced byte-identical output.

The consequence is that a user writing `include: [name]` pays for every attribute on the kind unless the
caller computes the complement itself — "everything the schema declares, minus what the user asked for" —
and passes that as `exclude`. `include` still has to carry the top-level name of any cardinality-many
relationship that must be prefetched, so the two lists are derived together, not either/or.

### A relationship's peer payload is projected off the *declared* peer schema

When a relationship declares a generic as its peer (`Device.location` → a location generic), the inline
peer payload carries only what the **generic** exposes. An attribute that lives on the concrete kind is
never requested and never arrives, no matter how many times the host query is retried.

This is the most common shape in real schemas and the source of most apparent "the value is empty"
reports. The fix is to load the peers by id in a second, batched pass — not to retry the host query.

### Hierarchy fields escape an `exclude` complement built from the schema

`parent`, `children`, `ancestors` and `descendants` are pseudo-schemas the SDK synthesises for any kind
with `hierarchy` set (`hierarchical_relationship_schemas`). They are **not** in `relationship_names`, so
an exclude list computed as "everything the schema declares, minus what the user asked for" never
reaches them — and `_process_hierarchical_fields` adds all four to the query whenever
`prefetch_relationships` is on. A narrowed query against Location, Organization or an IPAM prefix
therefore still drags two full hierarchies down on every page unless the four names are added to
`exclude` explicitly. Name them unconditionally: doing so on a non-hierarchical kind is free, because the
SDK only ever tests membership in `exclude`.

### The wrapper swallows exceptions whenever a Display is attached

`handle_infrahub_exceptions_decorator` is applied to every public `InfrahubclientWrapper` method in
`__init__`. With a `Display` (always, in the inventory) it logs and **returns `None`**; only without one
does it re-raise. So `try: ... except Exception` around a wrapper call is dead code in the inventory
path — check for a `None` return instead, and treat it as distinct from an empty list.

### The non-parallel pager costs an extra empty request on a full page

`filters(parallel=False)` stops only once `count - (offset + pagination_size)` goes negative, so a chunk
of exactly `pagination_size` triggers one more, empty round-trip. Batch ids at `pagination_size - 1`.

### `Config.custom_recorder` is the supported instrumentation hook

`Recorder` is a runtime-checkable protocol with a single method, `record(response: httpx.Response)`,
invoked from `InfrahubClientSync._record` on every HTTP response — below pagination. Passing a counter
as `custom_recorder` is how to measure real round-trips without monkeypatching `execute_graphql`.

Note it counts *every* response, REST schema lookups included, so the figure is legitimately higher than
a GraphQL-only count.

### Raising `pagination_size` does not make things faster

Measured on a ~650-device estate: 50 → 500 cut the request count from 20 to 4 and moved wall-clock the
wrong way, 7.10s → 7.60s. Fewer, larger pages is not a win here. Concurrency is the lever that helped.

## Naming Trap: `self.wrapper.client`

`InfrahubclientWrapper` holds the SDK client as `.client`, and the processors hold the *wrapper* as
`.wrapper`. So inside `InfrahubNodesProcessor`:

```python
self.wrapper  # the InfrahubclientWrapper
self.wrapper.client  # the raw InfrahubClientSync
self.wrapper.client.store  # the SDK's NodeStore
```

`self.wrapper.client` is two layers deep by design. Verify with
`processor.wrapper.client.store is wrapper.client.store` before changing anything in this area.
