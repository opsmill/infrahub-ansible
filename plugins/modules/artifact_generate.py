# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for artifact_generate action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: artifact_generate
author:
    - Opsmill
version_added: "1.7.0"
short_description: Trigger artifact regeneration in Infrahub
description:
    - Triggers the regeneration of artifacts for specified target nodes in Infrahub through Infrahub SDK
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
    target_ids:
        description:
            - List of target node UUIDs to regenerate artifacts for
        required: True
        type: list
        elements: str
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
"""

EXAMPLES = """
---
- name: Infrahub action plugin artifact_generate
  gather_facts: false
  hosts: localhost

  tasks:
    - name: Regenerate Startup Config for multiple devices
      opsmill.infrahub.artifact_generate:
        artifact_name: "Startup Config for Edge devices"
        target_ids:
          - "{{ device1_id }}"
          - "{{ device2_id }}"
          - "{{ device3_id }}"
      register: result

    - name: Regenerate artifact for a single device
      opsmill.infrahub.artifact_generate:
        artifact_name: "Startup Config for Edge devices"
        target_ids:
          - "{{ device_id }}"

    - name: Regenerate artifact by ID
      opsmill.infrahub.artifact_generate:
        artifact_id: "12345678-1234-1234-1234-123456789abc"
        target_ids:
          - "{{ device_id }}"
"""

RETURN = """
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
target_ids:
  description:
    - List of target node UUIDs that artifacts were regenerated for
  type: list
  elements: str
  returned: success
count:
  description:
    - Number of targets for which artifacts were regenerated
  type: int
  returned: success
msg:
  description:
    - Message indicating the result of the operation
  type: str
  returned: always
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main definition of Action Plugin for artifact_generate."""
    mutually_exclusive = [("artifact_name", "artifact_id")]
    required_one_of = [("artifact_name", "artifact_id")]
    AnsibleModule(
        argument_spec=dict(
            api_endpoint=dict(required=False, type="str", default=None),
            token=dict(required=False, type="str", no_log=True, default=None),
            timeout=dict(required=False, type="int", default=10),
            validate_certs=dict(required=False, type="bool", default=True),
            branch=dict(required=False, type="str", default="main"),
            # Module related arguments
            artifact_name=dict(required=False, type="str"),
            artifact_id=dict(required=False, type="str"),
            target_ids=dict(required=True, type="list", elements="str"),
        ),
        mutually_exclusive=mutually_exclusive,
        required_one_of=required_one_of,
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
