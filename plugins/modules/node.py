# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for create action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: node
author:
    - Benoit Kohler (@bearchitek)
version_added: "1.4.0"
short_description: Creates, Updates or Deletes a node in Infrahub
description:
    - Creates, Updates or Deletes a node of a given Kind in Infrahub through Infrahub SDK
requirements:
    - infrahub-sdk>=1.19.0
    - "Infrahub server >= 1.8 when using file_path or fetch_file (CoreFileObject support)"
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
    state:
        description:
            - "Use C(present) or C(absent) for adding or removing."
        choices: [ absent, present ]
        default: present
        type: str
    file_path:
        required: False
        description:
            - Local filesystem path to the file to upload when creating or updating a CoreFileObject node.
            - Required when the kind inherits from CoreFileObject (unless C(fetch_file) is used instead).
            - Mutually exclusive with C(fetch_file).
            - When provided, the module computes a SHA-1 checksum and skips the upload if it matches the
              server-side checksum (idempotent).
            - Fails if the kind does not inherit from CoreFileObject.
            - Ignored in check mode (no upload performed).
        type: str
        default: null
    fetch_file:
        required: False
        description:
            - When C(true), download the file content from the CoreFileObject node and include it in the
              result as C(binary) (base64-encoded) and C(text) (UTF-8 decoded for text MIME types, null
              otherwise).
            - Required when the kind inherits from CoreFileObject and C(file_path) is not provided.
            - Mutually exclusive with C(file_path).
            - Ignored in check mode (no download performed).
            - Fails if the kind does not inherit from CoreFileObject.
        type: bool
        default: false
"""

EXAMPLES = """
---
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

RETURN = """
object:
  description: Serialized object as created or already existent within Infrahub
  returned: success (when I(state=present))
  type: dict
msg:
  description: Message indicating failure or info about what has been achieved
  returned: always
  type: str
binary:
  description:
    - Base64-encoded file content downloaded from the CoreFileObject node.
    - Present only when I(fetch_file=true) and not in check mode.
  returned: when fetch_file=true and not check_mode
  type: str
text:
  description:
    - UTF-8 decoded file content for text MIME types (text/plain, application/json, etc.).
    - null for binary MIME types.
    - Present only when I(fetch_file=true) and not in check mode.
  returned: when fetch_file=true and not check_mode
  type: str
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC
from ansible_collections.opsmill.infrahub.plugins.module_utils.node import NodeModule


def main() -> None:
    """
    Main entry point for module execution to create/update/delete Node.
    """
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    argument_spec.update(
        kind=dict(required=True, type="str"),
        data=dict(required=True, type="raw"),
        branch=dict(required=False, type="str", default="main"),
        file_path=dict(required=False, type="str", default=None),
        fetch_file=dict(required=False, type="bool", default=False),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    node_module = NodeModule(module=module)
    node_module.run()


if __name__ == "__main__":  # pragma: no cover
    main()
