# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for create action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: node
author:
    - Benoit Kohler (@bearchitek)
version_added: "1.4.0"
short_description: Creates, Updates or Deletes a node in Infrahub
description:
    - Creates, Updates or Deletes a node of a given Kind in Infrahub through Infrahub SDK
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
    kind:
        required: True
        description:
            - Kind of node to create
        type: str
    data:
        required: True
        description:
            - Dictionary of node attributes
        type: raw
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
    state:
        description:
            - "Use C(present) or C(absent) for adding or removing."
        choices: [ absent, present ]
        default: present
        type: str
"""

EXAMPLES = r"""
- name: Infrahub playbook for opsmill.infrahub.node
  gather_facts: false
  hosts: localhost

  tasks:
    - name: Create tag1
      opsmill.infrahub.node:
        kind: "BuiltinTag"
        data:
          name: "tag1"
        state: present

    - name: Delete tag1
      opsmill.infrahub.node:
        kind: "BuiltinTag"
        data:
          name: "tag1"
        state: absent
"""

RETURN = r"""
object:
  description: Serialized object as created or already existent within Infrahub
  returned: success (when I(state=present))
  type: dict
msg:
  description: Message indicating failure or info about what has been achieved
  returned: always
  type: str
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC
from ansible_collections.opsmill.infrahub.plugins.module_utils.node import NodeModule


def main():
    """
    Main entry point for module execution to create/update/delete Node.
    """
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    argument_spec.update(
        kind=dict(required=True, type="str"),
        data=dict(required=True, type="raw"),
        branch=dict(required=False, type="str", default="main"),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    node_module = NodeModule(module=module)
    node_module.run()


if __name__ == "__main__":  # pragma: no cover
    main()
