# AGENTS.md — plugins/

Plugin development context for the `opsmill.infrahub` Ansible collection.

## Plugin Types

| Directory | Type | Count | Description |
|-----------|------|-------|-------------|
| `modules/` | Module stubs | 5 | User-facing interface — DOCUMENTATION + argument specs |
| `action/` | Action plugins | 3 | Controller-side execution logic |
| `module_utils/` | Shared utilities | 4 | SDK wrapper, base classes, processors |
| `inventory/` | Inventory plugin | 1 | Dynamic inventory from Infrahub |
| `lookup/` | Lookup plugin | 1 | GraphQL query lookup |
| `doc_fragments/` | Doc fragments | 1 | Reusable DOCUMENTATION blocks |

## Required Boilerplate

Every Python file in `plugins/` must have:

```python
from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type
```

This is enforced by `ansible-test sanity`. Omitting it will fail CI.

## Module Pattern

Modules in `modules/` are stubs. They define three docstrings and create an `AnsibleModule`:

```python
DOCUMENTATION = """..."""  # YAML — module name, options, descriptions
EXAMPLES = """..."""       # YAML — playbook examples
RETURN = """..."""         # YAML — return value documentation
```

Actual logic lives in either:
- An **action plugin** in `action/` (same filename) — for API-call-only modules
- A **module_utils class** in `module_utils/` — for state management modules

## INFRAHUB_ARG_SPEC

Standard argument spec for Infrahub connection parameters:

```python
INFRAHUB_ARG_SPEC = {
    "api_endpoint": {"required": True, "type": "str", "fallback": (env_fallback, ["INFRAHUB_ADDRESS"])},
    "token": {"required": True, "type": "str", "no_log": True, "fallback": (env_fallback, ["INFRAHUB_API_TOKEN"])},
    "state": {"required": False, "default": "present", "choices": ["present", "absent"]},
    "validate_certs": {"required": False, "type": "bool", "default": True},
    "timeout": {"required": False, "type": "int", "default": 10},
}
```

Usage: `argument_spec = deepcopy(INFRAHUB_ARG_SPEC)` then `.update()` with module-specific args.

## Conditional Import Pattern

All files using `infrahub-sdk` must guard imports:

```python
try:
    from infrahub_sdk import InfrahubClientSync
    # ... other SDK imports ...
    HAS_INFRAHUBCLIENT = True
except ImportError:
    HAS_INFRAHUBCLIENT = False
```

Check at runtime before using:
- In action plugins: `if not HAS_INFRAHUBCLIENT: raise AnsibleError(...)`
- In modules: `if not HAS_INFRAHUBCLIENT: module.fail_json(...)`

## Key Files

| File | What it contains |
|------|-----------------|
| `module_utils/infrahub_utils.py` | `InfrahubclientWrapper`, `InfrahubModule`, `InfrahubNodesProcessor`, `InfrahubQueryProcessor`, `INFRAHUB_ARG_SPEC` |
| `module_utils/node.py` | `NodeModule` — node create/update/delete |
| `module_utils/branch.py` | `BranchModule` — branch create/delete |
| `module_utils/exception.py` | `handle_infrahub_exceptions_decorator` — SDK error mapping |
| `doc_fragments/fragments.py` | `ModuleDocFragment` — reusable doc blocks |

## After Modifying Plugins

Always run these after changing any file under `plugins/`:

```bash
# 1. Format and lint
invoke format          # Auto-fix formatting
invoke lint            # Verify lint passes

# 2. Sanity tests — catches missing boilerplate, bad imports, doc format issues
invoke tests-sanity

# 3. Unit tests — catches regressions in logic
invoke tests-unit
```

If you changed `DOCUMENTATION`, `EXAMPLES`, or `RETURN` docstrings in any module file:

```bash
# 4. Regenerate reference docs from docstrings
invoke generate-doc
```

## Detailed References

- [../dev/knowledge/plugin-patterns.md](../dev/knowledge/plugin-patterns.md) — full pattern documentation
- [../dev/knowledge/infrahub-sdk-usage.md](../dev/knowledge/infrahub-sdk-usage.md) — SDK wrapper details
- [../dev/knowledge/architecture.md](../dev/knowledge/architecture.md) — data flow and abstractions
- [../dev/guides/creating-a-module.md](../dev/guides/creating-a-module.md) — step-by-step new module guide
