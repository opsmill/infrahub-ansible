# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for create action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: create_branch
author:
    - Benoit Kohler (@bearchitek)
version_added: "1.4.0"
short_description: Creates a new branch in Infrahub
description:
    - Creates a new branch in Infrahub through Infrahub SDK
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
"""

EXAMPLES = """
- name: Infrahub action plugin create_branch
  gather_facts: false
  hosts: localhost

  tasks:
    - name: Create a Branch 'test'
      opsmill.infrahub.create_branch:
        name: "test"
        sync_with_git: false
        description: "This is a test branch"
"""

RETURN = """
response:
  description:
    - String representation of created branch.
  type: dict
  returned: success
data:
  description:
    - branch id.
  type: str
  returned: success
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main definition of Action Plugin for create_branch."""
    AnsibleModule(
        argument_spec=dict(
            api_endpoint=dict(required=False, type="str", default=None),
            token=dict(required=False, type="str", no_log=True, default=None),
            timeout=dict(required=False, type="int", default=10),
            validate_certs=dict(required=False, type="bool", default=True),
            name=dict(required=True, type="str"),
            sync_with_git=dict(required=False, type="bool", default=False),
            description=dict(required=False, type="str"),
        ),
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
