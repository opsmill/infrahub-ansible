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
    - Queries Infrahub via its GraphQL API through Infrahub SDK
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
    query:
        required: True
        description:
            - GraphQL query parameters or filters to send to Infrahub to obtain desired data
        type: str
    graph_variables:
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
        type: bool
        default: True
    update_hostvars:
        description:
            - Whether or not to populate data in the in the root (e.g. hostvars[inventory_hostname]) or within the
              'data' key (e.g. hostvars[inventory_hostname]['data']). Beware, that the root keys provided by the query
              will overwrite any root keys already present, leverage the GraphQL alias feature to avoid issues.
        required: False
        default: False
        type: bool
"""

EXAMPLES = """
- name: Infrahub action plugin
  gather_facts: false
  hosts: localhost

  tasks:
    - name: SET FACTS TO SEND TO GRAPHQL ENDPOINT
      ansible.builtin.set_fact:
        variables:
          device_name: "atl1-edge1"
          enabled: true

        query_dict:
          InfraDevice:
            '@filters': {name__value: '$device_name'}
            edges:
              node:
                name:
                  value: null
                interfaces:
                  '@filters': {enabled__value: '$enabled'}
                  edges:
                    node:
                      name:
                        value: null

    - name: Action Plugin
      opsmill.infrahub.query_graphql:
        query: "{{ query_dict }}"
        graph_variables: "{{ variables }}"
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
            graph_variables=dict(required=False, type="dict", default={}),
            update_hostvars=dict(required=False, type="bool", default=False),
        ),
        supports_check_mode=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
