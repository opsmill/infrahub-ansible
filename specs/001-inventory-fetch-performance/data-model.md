# Phase 1 Data Model: Dynamic Inventory Fetch Performance

The spec's Key Entities are conceptual. This maps each to the thing that actually carries it, the fields
that matter, and the rules the requirements impose on it.

## Node

A record in Infrahub — a device, an address, a site. Carried by the SDK's `InfrahubNodeSync`.

| Field | Meaning | Notes |
|---|---|---|
| `id` | Stable identifier | Always queried; the key peers are batched by |
| `hfid` | Human-friendly identifier | Always queried |
| `display_label` | Rendered label | Always queried; usable as a hostname source |
| *attributes* | Named values on the node | What a definition selects from |
| *relationships* | Links to other nodes | Peers may arrive inline, or as bare ids |

### Rules

- `id`, `hfid`, `display_label` are never narrowed away (`ALWAYS_QUERIED` in `projection.py`).
- An attribute whose value is `None` is absent; `False`, `0`, and `""` are **present**. This distinction
  is load-bearing: treating a falsy value as absent is what produced one refetch per node (FR-002).

## Node type

The key a user writes under `nodes:` in the inventory definition. Infrahub calls it a *kind*.

### Rules

- Each node type carries its own attribute selection, independently of the others (FR-003/FR-004 apply
  per type, not globally).
- A node type whose schema cannot be found is skipped, recorded in `HostFetch.failures`, and does not
  abort the run (FR-014).

## Attribute selection → `NodeProjection`

`plugins/module_utils/projection.py`. Translates what the user wrote into what the SDK honours.

| Field | Meaning |
|---|---|
| `attrs` | The full selection, dotted paths included (`site.name`) |
| `roots` | First path segment of each selection — what a query can actually narrow on |
| `include` | Roots that exist on the schema; opts cardinality-many relationships in |
| `exclude` | Complement of `roots` against the schema, merged with any user `exclude` |
| `narrowed` | Whether the user gave a selection at all |

### Rules

- No selection → `narrowed = False`, and the historical wide query is preserved unchanged (FR-004).
- A selection → `exclude` carries the narrowing, because `include` alone does not narrow (see R5).
- `projected(root_attr)` answers "was this attribute asked for?" and is what stops the refill ledger from
  queueing a node for an attribute nobody wanted.

## Related node → `PeerWarmer` / `RefillLedger`

`plugins/module_utils/peers.py`.

`PeerWarmer` state:

| Field | Meaning |
|---|---|
| `store` | The SDK's `NodeStore`, where prefetched peers land |
| `page_size` | `pagination_size - 1` (see R3) |
| `loaded` | Ids that actually came back — not ids that were asked for |

`RefillLedger` state:

| Field | Meaning |
|---|---|
| `projections` | Per-type `NodeProjection`, to tell "not asked for" from "asked for and missing" |
| `already_loaded` | Shared with `PeerWarmer.loaded`; a peer fetched in full is never re-queued |
| `pending` | Node type → set of ids still needing a refill pass |

### Rules

- `collect()` computes the wanted-attribute set **per node type**, not per node.
- A peer is fetched only if its wanted attributes are not already satisfied in the store (FR-007).
- `warm()` records only ids present in the response (FR-008). Recording what was *requested* would mark
  a missing peer as loaded and silently suppress its refill.
- A batch that raises calls `on_error`, which warns and continues; hosts referencing it are still
  produced with the attribute empty (FR-019).
- A relationship whose selection asks only for the peer's id short-circuits: the id is read off the
  relationship and the peer is never fetched (FR-010).

## Host fetch → `HostFetch`

`plugins/module_utils/infrahub_utils.py`. A dataclass (not a tuple — its dict and list fields are
mutated in place during the fetch loop, and readability at the call sites matters more than immutability
here).

| Field | Meaning |
|---|---|
| `nodes` | Fetched host nodes across all types |
| `schemas` | Node type → schema |
| `attrs_by_kind` | Node type → selection |
| `projections` | Node type → `NodeProjection` |
| `failures` | Node type → why it failed |

### Rules

- `nodes` empty **and** `failures` non-empty → raise, naming every failure (FR-015).
- `nodes` empty and `failures` empty → succeed with no hosts (FR-016).

## Cache entry

Ansible's cache plugin holds the value; this feature defines only the key.

### Rules

- Key material: API endpoint, branch, node selection, and `CACHE_SCHEMA_VERSION` (FR-011, FR-012).
- Written only when the run actually fetched from the API (FR-013).

## Run cost report — *not yet implemented*

Required by FR-020 / SC-009. Per R1, carried by a counting `Recorder` passed as `Config.custom_recorder`
from `InfrahubclientWrapper`.

| Field | Meaning |
|---|---|
| `requests` | HTTP responses observed — the true count, below pagination |
| `peers_loaded` | Related nodes loaded; `PeerWarmer.warm()` already returns its call count today and discards it in `_warm_peers` |

### Rules

- Emitted at raised verbosity only (`_handle_display(level="INFO")` → `display.v()`); silent at default.
- A run served entirely from cache fetches nothing and so reports nothing.
