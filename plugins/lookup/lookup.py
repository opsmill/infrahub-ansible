# -*- coding: utf-8 -*-
# Copyright (c) 2023 Benoit Kohler
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
A lookup function designed to return data from the Infrahub GraphQL API
"""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = """
    name: lookup
    author:
        - Benoit Kohler (@bearchitek)
    short_description: Queries and returns elements from Infrahub (using GraphQL)
    description:
        - Get inventory hosts from Infrahub
    options:
        api_endpoint:
            description: Endpoint of the Infrahub API
            required: True
            env:
                - name: INFRAHUB_API
        token:
            required: True
            description:
                - Infrahub API token to be able to read against Infrahub.
            env:
                - name: INFRAHUB_TOKEN
        timeout:
            required: False
            description: Timeout for Infrahub requests in seconds
            type: int
            default: 10
        query:
            required: True
            description:
                - GraphQL query to send to Infrahub to obtain desired data
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
            default: True
"""

EXAMPLES = """
# Make API Query without variables
  - name: SET FACT OF STRING
    set_fact:
      query_string: |
        query {
          BuiltinLocation {
            edges {
              node {
                name {
                  value
                }
              }
            }
          }
        }

  # Make query to GraphQL Endpoint
  - name: Obtain list of sites from Infrahub
    set_fact:
      query_response: "{{ query('opsmill.infrahub.lookup', query=query_string, api='https://localhost:8000', token='<redact>') }}"
"""

RETURN = """
  data:
    description:
      - Data result from the Infrahub GraphQL endpoint
    type: dict
"""


import os
from typing import Dict

from ansible.errors import AnsibleError, AnsibleLookupError
from ansible.module_utils.six import raise_from
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    InfrahubclientWrapper,
    InfrahubQueryProcessor,
)


class LookupModule(LookupBase):
    """
    LookupModule(LookupBase) is defined by Ansible

    Parameters:
        LookupBase (LookupBase): Ansible Lookup Plugin
    """

    def run(self, terms, variables=None, query=None, graph_variables=None, **kwargs):
        """Runs Ansible Lookup Plugin for using Infrahub GraphQL endpoint

        Raises:
            AnsibleLookupError: Error in data loaded into the plugin
            AnsibleError: Generic Ansible Error

        Returns:
            dict: Data returned from Infrahub endpoint
        """
        if not HAS_INFRAHUBCLIENT:
            raise (AnsibleError("infrahub_sdk must be installed to use this plugin"))

        api_endpoint = kwargs.get("api_endpoint") or os.getenv("INFRAHUB_API")
        token = kwargs.get("token") or os.getenv("INFRAHUB_TOKEN")
        if api_endpoint is None:
            raise AnsibleLookupError("Missing Infrahub API Endpoint ")
        if token is None:
            raise AnsibleLookupError("Missing Infrahub TOKEN")

        api_endpoint = api_endpoint.strip("/")

        validate_certs = kwargs.get("validate_certs", True)
        if not isinstance(validate_certs, bool):
            raise AnsibleLookupError("validate_certs must be a boolean")

        timeout = kwargs.get("timeout", 10)
        branch = kwargs.get("branch", "main")

        if query is None:
            raise AnsibleLookupError("Query parameter was not passed")
        if isinstance(query, str) or isinstance(query, Dict):
            graphql_query = query
        else:
            raise AnsibleLookupError("Query parameter must be either a string or a Dictionary")
        if graph_variables is not None:
            if not isinstance(graph_variables, Dict):
                raise AnsibleLookupError("graph_variables parameter must be a list of Dict")

        results = {}
        try:
            Display().v("Initializing Infrahub Client")
            client = InfrahubclientWrapper(
                api_endpoint=api_endpoint,
                token=token,
                branch=branch,
                timeout=timeout,
            )
            processor = InfrahubQueryProcessor(client=client)
            Display().v("Processing Query")
            results = processor.fetch_and_process(query=graphql_query, variables=graph_variables)

        except Exception as exp:
            raise_from(AnsibleError(str(exp)), exp)

        return results
