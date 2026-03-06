# Creating a New Module

Step-by-step guide for adding a new module to the `opsmill.infrahub` collection.

## Overview

A new module typically involves creating or modifying files in up to 4 areas:

1. **Module stub** — `plugins/modules/<name>.py`
2. **Action plugin** (if the module runs on the controller) — `plugins/action/<name>.py`
3. **Module utils** (if the module uses the InfrahubModule pattern) — `plugins/module_utils/<name>.py`
4. **Tests** — `tests/unit/` and/or `tests/integration/`

Choose your pattern based on the module's needs:
- **Action plugin pattern** — for modules that make API calls directly (like `artifact_fetch`, `artifact_generate`, `query_graphql`)
- **Module utils pattern** — for modules with state management and idempotency (like `node`, `branch`)

## Step 1: Create the Module Stub

Create `plugins/modules/<name>.py`:

```python
# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for <name> action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: <name>
author:
    - Opsmill (@opsmill)
version_added: "<next_version>"
short_description: <one-line description>
description:
    - <detailed description of what the module does>
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
    branch:
        required: False
        description:
            - Branch in which the request is made
        type: str
        default: main
    validate_certs:
        description:
            - Whether or not to validate SSL of the Infrahub instance
        required: False
        type: bool
        default: True
    # Add module-specific options here
"""

EXAMPLES = """
---
- name: Example playbook for <name>
  gather_facts: false
  hosts: localhost
  connection: local

  tasks:
    - name: Do something with Infrahub
      opsmill.infrahub.<name>:
        param: value
      register: result

    - name: Display result
      ansible.builtin.debug:
        var: result
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

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main entry point for module execution."""
    AnsibleModule(
        argument_spec=dict(
            api_endpoint=dict(required=False, type="str", default=None),
            token=dict(required=False, type="str", no_log=True, default=None),
            timeout=dict(required=False, type="int", default=10),
            validate_certs=dict(required=False, type="bool", default=True),
            branch=dict(required=False, type="str", default="main"),
            # Add module-specific args here
        ),
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
```

## Step 2a: Create an Action Plugin (Action Plugin Pattern)

Create `plugins/action/<name>.py`:

```python
# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin for <description>."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import os
from typing import Any

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    InfrahubclientWrapper,
)


class ActionModule(ActionBase):
    """Ansible Action Module for <description>."""

    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict:
        if not HAS_INFRAHUBCLIENT:
            raise AnsibleError("infrahub_sdk must be installed to use this plugin")

        self._supports_check_mode = False
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)  # noqa: UP008
        del tmp

        if result.get("skipped"):
            return result

        if result.get("invocation", {}).get("module_args"):
            del result["invocation"]["module_args"]

        args = self._task.args

        # Credentials
        api_endpoint = args.get("api_endpoint") or os.getenv("INFRAHUB_ADDRESS")
        token = args.get("token") or os.getenv("INFRAHUB_API_TOKEN")
        if api_endpoint is None:
            raise AnsibleError("Missing Infrahub API Endpoint")
        if token is None:
            raise AnsibleError("Missing Infrahub TOKEN")
        api_endpoint = api_endpoint.strip("/")

        validate_certs = args.get("validate_certs", True)
        timeout = args.get("timeout", 10)
        branch = args.get("branch", "main")

        # Module-specific args
        # my_param = args.get("my_param")

        try:
            Display().v("Initializing Infrahub Client")
            client = InfrahubclientWrapper(
                api_endpoint=api_endpoint,
                token=token,
                branch=branch,
                timeout=timeout,
                validate_certs=validate_certs,
                display=Display(),
            )

            # Implement your logic here
            # result = client.some_method(...)

        except Exception as exp:
            raise AnsibleError(str(exp)) from exp

        return result
```

## Step 2b: Create a Module Utils Class (Module Utils Pattern)

Create `plugins/module_utils/<name>.py`:

```python
# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import InfrahubModule


class MyModule(InfrahubModule):
    def run(self):
        data = self.data
        # Implement logic using self.client, self.state, etc.

        if self.state == "present":
            self._ensure_object_exists(kind, data)
        else:
            self._ensure_object_absent(kind, data)
```

Then update the module stub to use it:

```python
from copy import deepcopy
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC
from ansible_collections.opsmill.infrahub.plugins.module_utils.<name> import MyModule


def main():
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    argument_spec.update(
        # module-specific args
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    my_module = MyModule(module=module)
    my_module.run()
```

## Step 3: Write Tests

### Unit Tests

Create `tests/unit/plugins/modules/test_<name>.py`:

```python
from unittest.mock import MagicMock, patch


class TestMyModule:
    def test_basic_creation(self):
        # Mock AnsibleModule, SDK client, etc.
        pass

    def test_idempotent_no_change(self):
        pass

    def test_error_handling(self):
        pass
```

### Run Tests

```bash
invoke tests-sanity
invoke tests-unit
```

## Step 4: Generate Documentation

```bash
# Regenerate reference docs from docstrings
invoke generate-doc

# Verify the docs build
invoke docusaurus
```

## Step 5: Update Changelog

Add a changelog entry to `CHANGELOG.rst` noting the new module and its version.

## Checklist

- [ ] Module stub with complete `DOCUMENTATION`, `EXAMPLES`, `RETURN`
- [ ] Action plugin or module_utils class with implementation
- [ ] `__metaclass__ = type` and `__future__` imports in all files
- [ ] Conditional `HAS_INFRAHUBCLIENT` check
- [ ] `no_log=True` on token parameters
- [ ] Environment variable fallbacks for `api_endpoint` and `token`
- [ ] Unit tests
- [ ] Sanity tests pass
- [ ] Documentation generated and renders correctly
- [ ] Changelog entry added
