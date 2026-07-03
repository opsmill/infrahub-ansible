# Architecture

The `opsmill.infrahub` Ansible collection provides modules, plugins, and inventory sources for interacting with [Infrahub](https://github.com/opsmill/infrahub) — an infrastructure data platform.

## Collection Layout

```text
plugins/
  modules/          # Ansible modules (user-facing interface)
  action/           # Action plugins (server-side execution logic)
  inventory/        # Dynamic inventory from Infrahub
  lookup/           # Lookup plugin for GraphQL queries
  module_utils/     # Shared Python utilities (SDK wrapper, base classes)
  doc_fragments/    # Reusable DOCUMENTATION fragments
roles/              # Ansible roles
tests/              # Sanity, unit, and integration tests
docs/               # Docusaurus documentation site
tasks/              # Invoke task definitions (lint, test, build, docs)
```

## Plugin Types

### 1. Modules (`plugins/modules/`)

Modules are the user-facing interface — what users call in playbooks via `opsmill.infrahub.<module_name>`. Each module file is a **stub** that:

- Defines `DOCUMENTATION`, `EXAMPLES`, and `RETURN` docstrings (used by `ansible-doc` and doc generation)
- Creates an `AnsibleModule` with an `argument_spec`
- Delegates to either an action plugin or a `module_utils` class for actual logic

Current modules:

| Module | Purpose |
|--------|---------|
| `node` | Create/update/delete any Infrahub node Kind |
| `branch` | Create/update/delete Infrahub branches |
| `query_graphql` | Execute GraphQL queries against Infrahub |
| `artifact_fetch` | Fetch artifact content (JSON or text) |
| `artifact_generate` | Trigger artifact regeneration |

### 2. Action Plugins (`plugins/action/`)

Action plugins run on the Ansible controller (not the target host). They handle:

- SDK client initialization with credentials
- API calls to Infrahub
- Result formatting

Not every module has a corresponding action plugin. The `node` and `branch` modules use `module_utils` classes directly, while `query_graphql`, `artifact_fetch`, and `artifact_generate` have action plugins.

### 3. Inventory Plugin (`plugins/inventory/inventory.py`)

The dynamic inventory plugin:

- Queries Infrahub for nodes matching configured filters
- Maps node attributes to Ansible host variables
- Supports caching, `compose`, and `keyed_groups` (via `Constructable`)
- Uses `InfrahubNodesProcessor` for fetching and transforming data

### 4. Lookup Plugin (`plugins/lookup/lookup.py`)

The lookup plugin allows inline GraphQL queries in playbooks:

```yaml
query_response: "{{ query('opsmill.infrahub.lookup', query=query_string) }}"
```

Uses `InfrahubQueryProcessor` to execute queries and extract results.

### 5. Module Utils (`plugins/module_utils/`)

Shared utilities — the core logic layer:

| File | Contents |
|------|----------|
| `infrahub_utils.py` | `InfrahubclientWrapper`, `InfrahubModule`, processor classes, `INFRAHUB_ARG_SPEC` |
| `node.py` | `NodeModule` — implements `run()` for node CRUD |
| `branch.py` | `BranchModule` — implements `run()` for branch CRUD |
| `exception.py` | `handle_infrahub_exceptions_decorator` — maps SDK exceptions to Ansible errors |

## Data Flow

### Module → module_utils path (node, branch)

```text
Playbook task
  → plugins/modules/node.py (stub: builds AnsibleModule, calls NodeModule.run())
    → plugins/module_utils/node.py (NodeModule.run())
      → plugins/module_utils/infrahub_utils.py (InfrahubModule base class)
        → InfrahubclientWrapper (wraps infrahub-sdk InfrahubClientSync)
          → Infrahub API
```

### Module → action plugin path (query_graphql, artifact_fetch, artifact_generate)

```text
Playbook task
  → plugins/modules/artifact_fetch.py (stub: defines AnsibleModule for docs/validation)
  → plugins/action/artifact_fetch.py (ActionModule.run() — actual logic)
    → InfrahubclientWrapper → Infrahub API
```

### Inventory plugin path

```text
Inventory file (*.infrahub.yml)
  → plugins/inventory/inventory.py (InventoryModule.parse())
    → InfrahubclientWrapper + InfrahubNodesProcessor
      → Infrahub API
    → Ansible inventory (hosts, groups, hostvars)
```

## Key Abstractions

### InfrahubclientWrapper

Wraps `InfrahubClientSync` from the `infrahub-sdk` package. Provides methods for:

- Node CRUD (`fetch_single_node`, `create_node`, `save_node`, `delete_node`)
- Schema operations (`fetch_single_schema`, `fetch_schemas`)
- Branch management (`fetch_branch`, `create_branch`, `delete_branch`)
- GraphQL execution (`execute_graphql`)
- Artifact operations (`fetch_single_artifact`, `generate_artifact`)

### InfrahubModule

Base class for modules that use the module_utils path. Provides:

- Idempotent state management (`_ensure_object_exists`, `_ensure_object_absent`)
- Diff tracking for `--diff` mode
- HFID (Human-Friendly ID) normalization
- Abstract `run()` method for subclasses

### Processor Classes

- **InfrahubBaseProcessor** — attribute resolution, relationship traversal, display handling
- **InfrahubNodesProcessor** — fetches nodes with schema-aware attribute extraction
- **InfrahubQueryProcessor** — executes GraphQL and processes results
