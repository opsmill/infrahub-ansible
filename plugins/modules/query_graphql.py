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
author: Benoit Kohler (@bearchitek)
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
    api_version:
        required: False
        description:
          - API Version Infrahub API
        type: str
    token:
        required: False
        description:
            - The API token created through Infrahub, optional env=INFRAHUB_TOKEN
        type: str
    query:
        required: True
        description:
            - GraphQL query parameters or filters to send to Infrahub to obtain desired data
        type: str
    graph_variables:
        required: False
        description:
            - Dictionary of keys/values to pass into the GraphQL query
        type: dict
        default: {}
    validate_certs:
        required: False
        description:
            - Whether or not to validate SSL of the Infrahub instance
        default: True
        type: bool
"""

EXAMPLES = """
"""

RETURN = """
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
            validate_certs=dict(required=False, type="bool", default=True),
            api_version=dict(required=False, type="str", default=None),
            query=dict(required=True, type="str"),
            graph_variables=dict(required=False, type="dict", default={}),
        ),
        supports_check_mode=True,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
