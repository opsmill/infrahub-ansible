# Contract: Inventory Plugin Interface

The collection's external interface for this feature is the inventory plugin's YAML option schema —
what a user writes in `*.infrahub.yml` — plus what the run emits back. Source of truth is the
`DOCUMENTATION` block in `plugins/inventory/inventory.py`; the reference MDX under
`docs/docs/references/plugins/` is generated from it by `invoke generate-doc` and is never hand-edited.

## Input contract

```yaml
plugin: opsmill.infrahub.inventory
api_endpoint: http://localhost:8000     # or INFRAHUB_ADDRESS
token: <token>                          # or INFRAHUB_API_TOKEN; no_log
branch: main
validate_certs: true
timeout: 60                             # FR-017 — default raised from 10
prefetch_relationships: true

nodes:
  InfraDevice:                          # node type
    include:                            # attribute selection; dotted paths allowed
      - name
      - platform.ansible_network_os
      - primary_address.address
      - site.name
      - interfaces
    exclude: []
    filters: {}

compose: {}
keyed_groups: []
hostnames: []
```

### Guarantees

| Guarantee | Requirement |
|---|---|
| No option added, removed, or renamed by this feature | Spec Out of Scope |
| `timeout` default is at least 60 | FR-017 |
| `include` narrows what is requested; omitting it preserves the historical wide query | FR-003, FR-004 |
| Selections are per node type, not global | FR-003, FR-004 |
| A dotted path resolves even when the relationship declares a broad peer type | FR-009 |
| A path naming only a relationship (no attribute) yields peer ids without fetching peers | FR-010 |
| For any definition, produced hosts and host variables are unchanged from before this feature | FR-018 |

## Output contract

### Inventory

Unchanged. Hosts, host variables, groups, and `keyed_groups` behave exactly as before — FR-018 is the
binding statement, verified byte-for-byte across four definition shapes.

### Diagnostics

| Condition | Level | Behaviour |
|---|---|---|
| Node type's schema not found | `warning` | Skipped; other types still resolve (FR-014) |
| Related-node batch fails | `warning` | Names the type; hosts still produced, attribute empty; run succeeds (FR-019) |
| No hosts fetched, at least one type failed | **error** | Run fails, message names each type and reason (FR-015) |
| No hosts fetched, nothing failed | — | Succeeds, no hosts, no error (FR-016) |
| Run cost | `-v` | Requests sent, related nodes loaded, and how many batches it took (FR-020) |
| Run cost | default verbosity | Silent (FR-020) |

## Cache contract

Not a user-facing option, but observable: two definitions differing only in branch, or only in node
selection, occupy distinct cache entries (FR-011). Entries written under an older
`CACHE_SCHEMA_VERSION` are not reused (FR-012). The cache is written only on a run that fetched
(FR-013).

## Compatibility

No migration. Existing inventory files keep working unchanged and get the improvement without edits.
The only user-visible default change is `timeout`, 10 → 60, which lengthens the ceiling on a run that
would previously have aborted; it does not lengthen a run that succeeds.
