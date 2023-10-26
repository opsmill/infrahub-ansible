#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible plugin definition for query_graphql action plugin."""
from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: query_graphql
author:
    - Benoit Kohler (@bearchitek)
version_added: "0.0.1"
short_description: Queries and returns elements from Infrahub GraphQL API
description:
    - Queries Infrahub via its GraphQL API through pyinfrahub
requirements:
    - pyinfrahub
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
    query:
        required: True
        description:
            - GraphQL query parameters or filters to send to Infrahub to obtain desired data
        type: str
    filters:
        description:
            - Dictionary of keys/values to pass into the GraphQL query
        required: False
        type: dict
        default: {}
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
        default: True
"""

EXAMPLES = """
"""

RETURN = """
  data:
    description:
      - Data result from the Infrahub GraphQL endpoint
    type: dict
    returned: success
"""

from ansible.module_utils.basic import AnsibleModule


def main():
    """Main definition of Action Plugin for query_graphql."""
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
            query=dict(required=True, type="str"),
            filters=dict(required=False, type="dict", default={}),
        ),
        supports_check_mode=True,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
