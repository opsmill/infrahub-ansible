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
            description: Timeout for Nautobot requests in seconds
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
# Make API Query without variables
  - name: SET FACT OF STRING
    set_fact:
      query_string: |
        query {
          location {
            id
            name
          }
        }

  # Make query to GraphQL Endpoint
  - name: Obtain list of sites from Infrahub
    set_fact:
      query_response: "{{ query('infrahub.infrahub.lookup', query=query_string, api='https://localhost:8000', token='<redact>') }}"
"""

RETURN = """
  data:
    description:
      - Data result from the Infrahub GraphQL endpoint
    type: dict
"""


import os
from typing import Any, Dict, Optional

from ansible.errors import AnsibleError, AnsibleLookupError
from ansible.module_utils.six import raise_from
from ansible.plugins.lookup import LookupBase
from ansible_collections.infrahub.infrahub.plugins.module_utils.infrahub_utils import (
    initialize_infrahub_client,
)

try:
    from infrahub_client import InfrahubClientSync
except ImportError as imp_exc:
    INFRAHUBCLIENT_IMPORT_ERROR = imp_exc
else:
    INFRAHUBCLIENT_IMPORT_ERROR = None

if INFRAHUBCLIENT_IMPORT_ERROR:
    class InfrahubClientSync:
        pass

def infrahub_lookup_graphql(
    client: InfrahubClientSync,
    query: str = None,
    filters: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """Lookup functionality, broken out to assist with testing

    Returns:
        Optional[Dict[str, Any]]: A dictionary with processed node attributes, or None if no nodes were processed.
    """

    if query is None:
        raise AnsibleLookupError("Query parameter was not passed. Please verify that query is passed.")
    if not isinstance(query, str):
        raise AnsibleLookupError("Query parameter must be of type Str. Please see docs for examples.")
    if filters is not None and not isinstance(filters, Dict):
        raise AnsibleLookupError("Filters parameter must be a list of Dict. Please see docs for examples.")

    # Init API Call
    # -> "builb" infrahub GraphQL request = XX
    # -> "builb" infrahub GraphQL response = XX

    # -> Check GraphQL responses (Exception or Records)

    results = None

    return [results]


class LookupModule(LookupBase):
    """
    LookupModule(LookupBase) is defined by Ansible
    """

    def run(self, terms, variables=None, filters=None, **kwargs):
        """Runs Ansible Lookup Plugin for using Infrahub GraphQL endpoint

        Raises:
            AnsibleLookupError: Error in data loaded into the plugin
            AnsibleError: Generic Ansible Error

        Returns:
            dict: Data returned from Infrahub endpoint
        """
        if INFRAHUBCLIENT_IMPORT_ERROR:
            raise_from(
                AnsibleError("infrahub_client must be installed to use this plugin"),
                INFRAHUBCLIENT_IMPORT_ERROR,
            )

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

        kwargs.get("timeout", 10)
        kwargs.get("branch", "main")

        client = initialize_infrahub_client(
            api_endpoint=api_endpoint,
            branch=self.branch,
            token=self.token,
            timeout=self.timeout,
        )

        lookup_info = infrahub_lookup_graphql(client=client, query=terms[0], filters=filters)

        # Results should be the data response of the query to be returned as a lookup
        return lookup_info
