# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for artifact_generate action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: artifact_generate
author:
    - Opsmill (@opsmill)
version_added: "1.7.0"
short_description: Trigger artifact regeneration in Infrahub
description:
    - Triggers the regeneration of an artifact for a specified target node in Infrahub.
    - The module looks up the artifact associated with the target node and triggers regeneration.
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
    artifact_name:
        required: False
        description:
            - Name of the artifact (mutually exclusive with artifact_id)
        type: str
    artifact_id:
        required: False
        description:
            - UUID of the artifact (mutually exclusive with artifact_name)
        type: str
    target_id:
        description:
            - UUID of the target node (e.g., device ID) that the artifact is associated with
        required: True
        type: str
    branch:
        required: False
        description:
            - Branch in which the request is made
        type: str
        default: main
    validate_certs:
        description:
            - Whether to validate SSL of the Infrahub instance
        required: False
        type: bool
        default: True
    state:
        description:
            - "Use C(present) or C(absent) for adding or removing."
        choices: [ absent, present ]
        default: present
        type: str
"""

EXAMPLES = """
---
# Example 1: Regenerate artifact by name for a device
- name: Regenerate artifact by name
  gather_facts: false
  hosts: localhost
  connection: local

  tasks:
    - name: Regenerate Startup Config for a device
      opsmill.infrahub.artifact_generate:
        artifact_name: "Startup Config"
        target_id: "{{ device_id }}"
      register: result

    - name: Display regeneration result
      ansible.builtin.debug:
        var: result

---
# Example 2: Regenerate artifact by UUID
- name: Regenerate artifact by ID
  gather_facts: false
  hosts: localhost

  tasks:
    - name: Regenerate specific artifact by ID
      opsmill.infrahub.artifact_generate:
        artifact_id: "12345678-1234-1234-1234-123456789abc"
        target_id: "{{ device_id }}"

---
# Example 3: Using with Infrahub inventory plugin
# Run with: ansible-playbook playbook.yml -i inventory.infrahub.yml -l "*edge*"
- name: Regenerate artifacts using inventory host IDs
  gather_facts: false
  hosts: all
  connection: local

  tasks:
    - name: Regenerate Startup Config for each device
      opsmill.infrahub.artifact_generate:
        artifact_name: "Startup Config"
        target_id: "{{ id }}"
      register: result
"""

RETURN = """
artifact_id:
  description:
    - UUID of the artifact that was regenerated
  type: str
  returned: success
artifact_name:
  description:
    - Name of the artifact that was regenerated
  type: str
  returned: success
definition_id:
  description:
    - UUID of the artifact definition
  type: str
  returned: success
target_id:
  description:
    - UUID of the target node that the artifact is associated with
  type: str
  returned: success
changed:
  description:
    - Whether the artifact regeneration was triggered
  type: bool
  returned: success
msg:
  description:
    - Message indicating the result of the operation
  type: str
  returned: always
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC


def main() -> None:
    """Main definition of Action Plugin for artifact_generate."""
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


if __name__ == "__main__":  # pragma: no cover
    main()
