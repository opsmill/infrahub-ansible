# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for create action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: create_node
author:
    - Benoit Kohler (@bearchitek)
version_added: "1.4.0"
short_description: Creates nodes in Infrahub
description:
    - Creates nodes in Infrahub through Infrahub SDK
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
    allow_upsert:
        description:
            - Allow upsert when saving node
        required: False
        type: bool
        default: True
"""

EXAMPLES = """
- name: Infrahub action plugin create_branch
  gather_facts: false
  hosts: localhost

  tasks:
    - name: Create device
      opsmill.infrahub.create:
        kind: "InfraDevice"
        allow_upsert: true
        data:
          name: "device1"
          status: "active"
"""

RETURN = """
response:
  description:
    - String representation of created node.
  type: dict
  returned: success
data:
  description:
    - Node id and hfid.
  type: str
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main definition of Action Plugin for create_node."""
    AnsibleModule(
        argument_spec=dict(
            api_endpoint=dict(required=False, type="str", default=None),
            token=dict(required=False, type="str", no_log=True, default=None),
            timeout=dict(required=False, type="int", default=10),
            validate_certs=dict(required=False, type="bool", default=True),
            branch=dict(required=False, type="str", default="main"),
            kind=dict(required=True, type="str"),
            data=dict(required=True, type="raw"),
            allow_upsert=dict(required=False, type="bool", default=True),
        ),
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
