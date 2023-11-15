#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2023 Damien Garros
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for artifact_fetch action plugin."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: artifact_fetch
author:
    - Damien Garros (@dgarros)
version_added: "0.0.3"
short_description: Fetch the content of an artifact from Infrahub
description:
    - Fetch the content of an artifact from Infrahub through Infrahub SDK
requirements:
    - infrahub-sdk
options:
    api_endpoint:
        required: False
        description:
          - Endpoint of the Infrahub API, optional env=INFRAHUB_API
        type: str
    token:
        required: False
        description:
            - The API token created through Infrahub, optional env=INFRAHUB_TOKEN
        type: str
    timeout:
        required: False
        description: Timeout for Infrahub requests in seconds
        type: int
        default: 10
    artifact_name:
        required: True
        description:
            - Name of the artifact
        type: str
    target_id:
        description:
            - Id of the target for this artifact
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
            - Whether or not to validate SSL of the Infrahub instance
        required: False
        type: bool
        default: True
"""

EXAMPLES = """
"""

RETURN = """
  json:
    description:
      - Content of the artifact in JSON format.
    type: dict
    returned: success
  text:
    description:
      - Content of the artifact in TEXT format.
    type: str
    returned: success
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main definition of Action Plugin for artifact_fetch."""
    # the AnsibleModule object will be our abstraction working with Ansible
    # this includes instantiation, a couple of common attr would be the
    # args/params passed to the execution, as well as if the module
    # supports check mode
    AnsibleModule(
        argument_spec=dict(
            api_endpoint=dict(required=False, type="str", default=None),
            token=dict(required=False, type="str", no_log=True, default=None),
            timeout=dict(required=False, type="int", default=10),
            validate_certs=dict(required=False, type="bool", default=True),
            branch=dict(required=False, type="str", default="main"),
            artifact_name=dict(required=True, type="str"),
            target_id=dict(required=True, type="str"),
        ),
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
