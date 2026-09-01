# Inventory and Lookup Plugins

The collection ships two read-only data plugins that pull from Infrahub's
GraphQL API: a dynamic inventory source and a lookup plugin. Both lean on the
processor classes described in
[infrahub-sdk-usage.md](infrahub-sdk-usage.md); this document is the deep-dive on
how each plugin is wired.

## Inventory Plugin (`plugins/inventory/inventory.py`)

`InventoryModule` inherits from `BaseInventoryPlugin`, `Constructable`, and
`Cacheable`, with `NAME = "opsmill.infrahub.inventory"`. It extends the
`constructed` and `inventory_cache` doc fragments, which supply the `compose`,
`groups`, `keyed_groups`, and caching behavior.

### Config Options

An inventory file (`*.yml` / `*.yaml`, validated by `verify_file`) sets:

- `api_endpoint`, `token` — connection and auth, with `INFRAHUB_ADDRESS` /
  `INFRAHUB_API_TOKEN` env fallbacks; `timeout`, `validate_certs`, `branch`
  (default `main`), and `prefetch_relationships` (default `True`).
- `nodes` — a map of node kind to a config of `filters`, `include`, and
  `exclude` attribute lists. This drives what is fetched.
- `compose`, `groups`, `keyed_groups` — host-var and grouping construction
  (from `Constructable`).
- `hostnames` — an ordered list of attribute paths (e.g. `name`,
  `primary_address.address`, or the special `display_label`) used to pick each
  host's inventory name; first non-empty value wins, falling back to the
  display label.

### Flow

`parse()` is the entry point: it calls `_read_config_data`, reads every option,
runs `_set_authorization` (templating the token on ansible-core ≥ 2.11), then
`main()`. `main()` checks `HAS_INFRAHUBCLIENT`, builds an `InfrahubclientWrapper`,
and uses an `InfrahubNodesProcessor` to `fetch_and_process` the configured
nodes into a `host_node_attributes` dict. The raw (pre-hostname-resolution) data
is cached via `_store_in_cache` (so hostname-config changes always re-resolve on
the next load), then `resolve_hostnames` picks names and `set_hosts_and_groups`
adds each host, sets its variables, and applies composed/keyed groups. Caching
is handled by `_fetch_from_cache` / `_store_in_cache`, keyed by `_cache_key()`
over everything that shapes the fetched data — API endpoint, `branch`, the
`nodes` spec, a digest of the token, `prefetch_relationships`, and a
`CACHE_SCHEMA_VERSION` constant bumped whenever the shape of the cached host
variables changes. The token is in there because Infrahub applies permissions per
token, so a low-privilege run must not be served hosts a privileged one fetched;
only a digest goes in, since the key reaches a cache filename and verbose output. Keying on the endpoint alone would let two
inventory files against one Infrahub share an entry, and switching `branch`
would serve the other branch's hosts. The cache is written only on a miss, so an
entry ages out instead of having its TTL renewed on every run.

### What a run cost

`fetch_and_process` ends by reporting what the run cost, at raised verbosity only:

```text
Inventory fetch cost: 15 request(s) to Infrahub, 41 node(s) loaded in 2 batch(es)
```

The request count comes from a `RequestCounter`
(`plugins/module_utils/metrics.py`) handed to the SDK as its `custom_recorder`
when `InfrahubclientWrapper` builds its `Config`. That is the only place a
truthful count can be taken: the SDK paginates inside `client.filters()`, below
the wrapper, so counting the wrapper's own calls reports fetch *operations* and
misses the pages — the part that actually grows with the estate.

Two things to know before reading the number. It counts **every** HTTP
round-trip, so schema lookups (REST, not GraphQL) are included and the figure is
legitimately higher than a GraphQL-only count. And a wrapper built through
`__new__` — which the integration tests do, to skip re-authenticating — has no
counter attached, so the line reports `unavailable` for requests and still gives
the peer figures.

It goes out through `Display.v`, which Ansible gates behind `-v`; nothing is
printed at default verbosity, and a run served entirely from cache never reaches
this code at all.

String values are passed through `_mark_trusted` before going into the
inventory — on ansible-core 2.19 this tags plugin-supplied strings as
trusted-as-template so `ansible-inventory --list` emits plain JSON instead of
`{"__ansible_unsafe": ...}` wrappers (issue #323). On older cores it is a no-op.

## Lookup Plugin (`plugins/lookup/lookup.py`)

`LookupModule` inherits from `LookupBase`. It is invoked inline in playbooks:

```yaml
query_response: "{{ query('opsmill.infrahub.lookup', query=query_string) }}"
```

### Options and Flow

`run(self, terms, variables=None, query=None, graph_variables=None, **kwargs)`
accepts `api_endpoint`, `token` (with the same env fallbacks), `timeout`,
`branch` (default `main`), `validate_certs`, the required `query` (a GraphQL
string), and optional `graph_variables` (a dict of query variables). After
checking `HAS_INFRAHUBCLIENT` and validating inputs (raising
`AnsibleLookupError` on missing endpoint/token or a bad `query` type), it builds
an `InfrahubclientWrapper` and an `InfrahubQueryProcessor`, calls
`processor.fetch_and_process(query=..., variables=...)`, and flattens the
result: for each top-level kind in the response it extends the result list with
that kind's `edges`. The returned `list` is what the `query()` call yields.

## Relationship to the Processors

Both plugins are thin adapters over the SDK wrapper plus a processor — the
inventory side uses `InfrahubNodesProcessor` (schema-aware attribute extraction
and relationship resolution), the lookup side uses `InfrahubQueryProcessor` (raw
GraphQL). The shared resolution logic lives in `InfrahubBaseProcessor`. See
[infrahub-sdk-usage.md](infrahub-sdk-usage.md) for the processor APIs and
[architecture.md](architecture.md) for where these plugins sit in the data flow.
