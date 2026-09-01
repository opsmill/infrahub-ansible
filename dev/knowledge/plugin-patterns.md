# Plugin Patterns

Every plugin in this collection follows specific Ansible conventions. This document captures the patterns found across all plugin files.

## Module File Pattern

Module files in `plugins/modules/` are stubs. They define documentation and argument specs but delegate logic elsewhere.

### Required Boilerplate

Every module file starts with:

```python
from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type
```

The `__metaclass__ = type` line and `__future__` imports are required by `ansible-test sanity` for Python 2/3 compatibility headers (even though this collection requires Python 3.10+).

### DOCUMENTATION / EXAMPLES / RETURN Docstrings

Every module must define three module-level string variables:

```python
DOCUMENTATION = """
---
module: <module_name>
author:
    - Opsmill (@opsmill)
version_added: "<version>"
short_description: <one-line summary>
description:
    - <detailed description>
requirements:
    - infrahub-sdk
options:
    api_endpoint:
        required: False
        description:
          - Endpoint of the Infrahub API, optional env=INFRAHUB_ADDRESS
        type: str
    token:
        required: False
        description:
            - The API token created through Infrahub, optional env=INFRAHUB_API_TOKEN
        type: str
    timeout:
        required: False
        description: Timeout for Infrahub requests in seconds
        type: int
        default: 10
    # ... module-specific options ...
"""

EXAMPLES = """
---
- name: Example playbook
  gather_facts: false
  hosts: localhost
  tasks:
    - name: Do something
      opsmill.infrahub.<module_name>:
        param: value
"""

RETURN = """
object:
  description: The result object
  returned: success
  type: dict
msg:
  description: Status message
  returned: always
  type: str
"""
```

These are extracted by `ansible-doc` and by the doc generation pipeline (`tasks/docs.py`).

### Argument Spec Patterns

**Using INFRAHUB_ARG_SPEC (node, branch modules):**

```python
from copy import deepcopy
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC

argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
argument_spec.update(
    kind=dict(required=True, type="str"),
    data=dict(required=True, type="raw"),
    branch=dict(required=False, type="str", default="main"),
)
module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
```

`INFRAHUB_ARG_SPEC` provides: `api_endpoint`, `token`, `state`, `validate_certs`, `timeout`.

**Artifact modules (with mutual exclusion):**

```python
from copy import deepcopy
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC

argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
argument_spec.update(
    artifact_name=dict(required=False, type="str"),
    artifact_id=dict(required=False, type="str"),
    target_id=dict(required=True, type="str"),
    branch=dict(required=False, type="str", default="main"),
)
AnsibleModule(
    argument_spec=argument_spec,
    mutually_exclusive=[("artifact_name", "artifact_id")],
    required_one_of=[("artifact_name", "artifact_id")],
    supports_check_mode=False,
)
```

### Module Execution

Modules that use module_utils:

```python
def main():
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    argument_spec.update(...)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    node_module = NodeModule(module=module)
    node_module.run()


if __name__ == "__main__":  # pragma: no cover
    main()
```

Modules with action plugins have minimal `main()` — the action plugin does the real work.

## Action Plugin Pattern

Action plugins in `plugins/action/` inherit from `ActionBase`:

```python
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible.errors import AnsibleError


class ActionModule(ActionBase):
    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict:
        if not HAS_INFRAHUBCLIENT:
            raise AnsibleError("infrahub_sdk must be installed to use this plugin")

        self._supports_check_mode = False
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        # Extract args
        args = self._task.args
        api_endpoint = args.get("api_endpoint") or os.getenv("INFRAHUB_ADDRESS")
        token = args.get("token") or os.getenv("INFRAHUB_API_TOKEN")

        # Validate
        if api_endpoint is None:
            raise AnsibleError("Missing Infrahub API Endpoint")

        # Create client, call API, return result dict
        client = InfrahubclientWrapper(...)
        result = client.some_method(...)
        return result
```

Key conventions:

- Always check `HAS_INFRAHUBCLIENT` first
- Call `super().run()` and delete `tmp`
- Read credentials from args with environment variable fallback
- Strip trailing `/` from `api_endpoint`
- Raise `AnsibleError` for validation failures

## Conditional Import Pattern

All files that use `infrahub-sdk` must use conditional imports:

```python
try:
    from infrahub_sdk import Config, InfrahubClientSync
    from infrahub_sdk.exceptions import BranchNotFoundError, SchemaNotFoundError

    # ... other imports ...
    HAS_INFRAHUBCLIENT = True
except ImportError:
    HAS_INFRAHUBCLIENT = False
```

Then check at runtime:

```python
if not HAS_INFRAHUBCLIENT:
    module.fail_json(msg="infrahub_sdk must be installed")
    # or: raise AnsibleError("infrahub_sdk must be installed to use this plugin")
```

This allows `ansible-doc` and `ansible-test sanity` to parse the module without requiring the SDK installed.

## Inventory Plugin Pattern

The inventory plugin inherits from multiple bases:

```python
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    NAME = "opsmill.infrahub.inventory"
```

Required methods:

- `verify_file(path)` — validate inventory file extension
- `parse(inventory, loader, path, cache)` — main entry point
- `main()` — business logic (client setup, data fetching, host creation)

## Lookup Plugin Pattern

```python
class LookupModule(LookupBase):
    def run(self, terms, variables=None, query=None, graph_variables=None, **kwargs):
        # Validate, create client, execute query, return results
```

## Doc Fragments

Reusable documentation blocks in `plugins/doc_fragments/fragments.py`:

```python
class ModuleDocFragment:
    BASE = r"""
requirements:
  - infrahub_sdk
options:
  api_endpoint: ...
  token: ...
  timeout: ...
  branch: ...
  validate_certs: ...
"""
```

Referenced in module DOCUMENTATION via `extends_documentation_fragment`.

## State Management Pattern

Modules supporting `state` use idempotent operations:

```python
# In InfrahubModule base class:
def _ensure_object_exists(kind, data):
    # Fetch existing → create if missing, update if different
    # Track diff for --diff mode
    # Set self.result["changed"] appropriately

def _ensure_object_absent(kind, data):
    # Fetch existing → delete if found
    # No-op if already absent
```

## Error Handling

The `handle_infrahub_exceptions_decorator` in `module_utils/exception.py` wraps SDK calls:

- `GraphQLError` → extracts error messages from response
- `SchemaNotFoundError` → "Schema not found" error
- `BranchNotFoundError` → "Branch not found" error
- `ServerNotReachableError` / `ServerNotResponsiveError` → connectivity errors
- Generic `Exception` → fallback with traceback

## Copyright Header

Every Python file starts with:

```python
# Copyright (c) <year> Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
```
