# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for object_file_fetch action plugin."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: object_file_fetch
author:
    - Opsmill (@opsmill)
version_added: "1.9.0"
short_description: Fetch file content from a CoreFileObject node in Infrahub
description:
    - Downloads the binary file content stored on a CoreFileObject schema node.
    - Identifies the node by UUID (node_id) or HFID (hfid).
    - Optionally saves the file to a local destination path.
    - Returns base64-encoded binary content and metadata regardless of I(dest).
requirements:
    - infrahub-sdk>=1.19.0
    - "Infrahub server >= 1.8 (CoreFileObject support)"
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
    validate_certs:
        description:
            - Whether or not to validate SSL of the Infrahub instance
        required: False
        type: bool
        default: True
    branch:
        required: False
        description:
            - Branch in which the request is made
        type: str
        default: main
    kind:
        required: True
        description:
            - Schema kind that inherits from CoreFileObject (e.g. C(NetworkCircuitContract))
        type: str
    node_id:
        required: False
        description:
            - UUID of the CoreFileObject node to fetch.
            - One of I(node_id) or I(hfid) is required.
        type: str
    hfid:
        required: False
        description:
            - Human-friendly ID component values for the CoreFileObject node.
            - One of I(node_id) or I(hfid) is required.
        type: list
        elements: str
    dest:
        required: False
        description:
            - Local path to save the file content.
            - When a directory path is given (trailing slash or existing directory),
              the file is saved as `{dest}/{node.file_name}`.
            - When a file path is given, the file is saved exactly at that path.
            - When omitted, file content is returned as variables only.
        type: str
        default: null
"""

EXAMPLES = """
---
- name: Fetch contract PDF by node UUID
  opsmill.infrahub.object_file_fetch:
    kind: NetworkCircuitContract
    node_id: "abc123-uuid"
  register: fetch_result

- name: Write fetched file to disk
  ansible.builtin.copy:
    content: "{{ fetch_result.binary | b64decode }}"
    dest: /tmp/contract.pdf

- name: Fetch and save to directory by HFID
  opsmill.infrahub.object_file_fetch:
    kind: NetworkCircuitContract
    hfid:
      - "contract.pdf"
    dest: /tmp/contracts/
  register: fetch_result
# File saved to /tmp/contracts/contract.pdf
# fetch_result.dest == "/tmp/contracts/contract.pdf"

- name: Fetch and save to explicit file path
  opsmill.infrahub.object_file_fetch:
    kind: NetworkCircuitContract
    node_id: "abc123-uuid"
    dest: /tmp/my-contract.pdf
  register: fetch_result
# File saved to exactly /tmp/my-contract.pdf
"""

RETURN = """
binary:
  description:
    - Base64-encoded file content downloaded from the CoreFileObject node.
  returned: success
  type: str
text:
  description:
    - UTF-8 decoded file content for text MIME types (text/plain, application/json, etc.).
    - null for binary MIME types.
  returned: success
  type: str
file_name:
  description: Original filename as stored in Infrahub.
  returned: success
  type: str
file_type:
  description: MIME type of the file as detected by Infrahub.
  returned: success
  type: str
file_size:
  description: Size of the file in bytes.
  returned: success
  type: int
checksum:
  description: SHA-1 hex digest of the file content as stored in Infrahub.
  returned: success
  type: str
node_id:
  description: UUID of the fetched CoreFileObject node.
  returned: success
  type: str
dest:
  description: Resolved local path where the file was saved. null if I(dest) was not provided.
  returned: success
  type: str
msg:
  description: Status message.
  returned: always
  type: str
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC


def main() -> None:
    """Main definition of Action Plugin for object_file_fetch."""
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    argument_spec.pop("state")
    argument_spec.update(
        branch=dict(required=False, type="str", default="main"),
        kind=dict(required=True, type="str"),
        node_id=dict(required=False, type="str", default=None),
        hfid=dict(required=False, type="list", elements="str", default=None),
        dest=dict(required=False, type="str", default=None),
    )
    AnsibleModule(
        argument_spec=argument_spec,
        required_one_of=[("node_id", "hfid")],
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
