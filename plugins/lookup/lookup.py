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
    InfrahubclientWrapper,
    InfrahubQueryProcessor,
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

class LookupModule(LookupBase):
    """
    LookupModule(LookupBase) is defined by Ansible

    Parameters:
        LookupBase (LookupBase): Ansible Lookup Plugin
    """

    def run(self, terms, variables=None, filters=None, **kwargs):
        """Runs Ansible Lookup Plugin for using Infrahub GraphQL endpoint

        Parameters:
            terms
            variables
            filters
            kwargs

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

        timeout = kwargs.get("timeout", 10)
        branch = kwargs.get("branch", "main")

        query_str = terms[0]
        if query_str is None:
            raise AnsibleLookupError("Query parameter was not passed")
        if not isinstance(query_str, str):
            raise AnsibleLookupError("Query parameter must be of type Str")
        if filters is not None and not isinstance(filters, Dict):
            raise AnsibleLookupError("Filters parameter must be a list of Dict")
        
        results = {}
        try:
            self.display.v("Initializing Infrahub Client")
            client = InfrahubclientWrapper(
                api_endpoint=api_endpoint,
                token=token,
                branch=branch,
                timeout=timeout,
            )
            processor = InfrahubQueryProcessor(client=client)
            self.display.v("Processing Query")
            results = processor.fetch_and_process(query=query_str, variables=filters)
        except Exception as exp:
            raise_from(AnsibleLookupError(str(exp)), exp)

        return results
