# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for create action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: branch
author:
    - Benoit Kohler (@bearchitek)
version_added: "1.4.0"
short_description: Creates, Updates or Deletes a branch in Infrahub
description:
    - Creates, Updates or Deletes a branch (InrahubBranch) in Infrahub through Infrahub SDK
requirements:
    - infrahub-sdk
options:
    api_endpoint:
        required: True
        description:
          - Endpoint of the Infrahub API, optional env=INFRAHUB_ADDRESS
        type: str
    token:
        required: True
        description:
            - The API token created through Infrahub, optional env=INFRAHUB_API_TOKEN
        type: str
    timeout:
        required: False
        description: Timeout for Infrahub requests in seconds
        type: int
        default: 10
    name:
        required: True
        description:
            - Name of the branch to create
        type: str
    sync_with_git:
        required: False
        description:
            - Whether to sync the branch with git
        type: bool
        default: False
    description:
        required: False
        description:
            - Description of the branch
        type: str
    validate_certs:
        description:
            - Whether or not to validate SSL of the Infrahub instance
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
- name: Infrahub playbook for opsmill.infrahub.branch
  gather_facts: false
  hosts: localhost

  tasks:
    - name: Create a Branch 'test'
      opsmill.infrahub.branch:
        name: "test"
        sync_with_git: false
        description: "This is a test branch"
        state: present

    - name: Delete a Branch 'test'
      opsmill.infrahub.branch:
        name: "test"
        state: absent
"""

RETURN = """
object:
  description: Serialized Branch object as created or already existent within Infrahub
  returned: success (when I(state=present))
  type: dict
msg:
  description: Message indicating failure or info about what has been achieved
  returned: always
  type: str
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.branch import BranchModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC


def main():
    """
    Main entry point for module execution to create/update/delete InfrahubBranch.
    """
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    argument_spec.update(
        name=dict(required=True, type="str"),
        sync_with_git=dict(required=False, type="bool", default=False),
        description=dict(required=False, type="str"),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)

    branch_module = BranchModule(module=module)
    branch_module.run()


if __name__ == "__main__":  # pragma: no cover
    main()
