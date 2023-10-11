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
        api_version:
            description: The Infrahub API Version to use
            required: False
        api_endpoint:
            description: Endpoint of the Infrahub API
            required: True
            env:
                - name: INFRAHUB_API
        token:
            required: True
            description: Infrahub API token to be able to read against Infrahub.
            env:
                - name: INFRAHUB_TOKEN
        query:
            required: True
            description: GraphQL query parameters or filters to send to Infrahub to obtain desired data
            type: dict
            default: {}
        graph_variables:
            description:
                - Dictionary of keys/values to pass into the GraphQL query
            required: False
            type: dict
            default: {}
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
      query_response: "{{ query('infrahub.infrahub.lookup', query=query_string, url='https://localhost:8000', token='<redact>') }}"
"""

RETURN = """
"""


import os

from ansible.errors import AnsibleLookupError
from ansible.plugins.lookup import LookupBase
from ansible.utils.display import Display


def infrahub_lookup_graphql(**kwargs):
    """Lookup functionality, broken out to assist with testing

    Returns:
        [type]: [description]
    """
    # Load and Test API (Url, Token and SSL verification)
    url = kwargs.get("url") or os.getenv("INFRAHUB_API")
    Display().v("INFRAHUB API: %s" % url)
    if url is None:
        raise AnsibleLookupError("Missing Infrahub URL ")

    token = kwargs.get("token") or os.getenv("INFRAHUB_TOKEN")
    if token is None:
        raise AnsibleLookupError("Missing Infrahub TOKEN")

    ssl_verify = kwargs.get("validate_certs", True)
    if not isinstance(ssl_verify, bool):
        raise AnsibleLookupError("validate_certs must be a boolean")

    kwargs.get("api_version")

    # Load and Test GraphQL (qeury and variables)
    query = kwargs.get("query")
    Display().v("Query String: %s" % query)
    if query is None:
        raise AnsibleLookupError(
            "Query parameter was not passed. Please verify that query is passed."
        )
    if not isinstance(query, str):
        raise AnsibleLookupError(
            "Query parameter must be of type string. Please see docs for examples."
        )
    graph_variables = kwargs.get("graph_variables")
    Display().v("Graph Variables: %s" % graph_variables)

    # Verify that the variables key coming in is a dictionary
    if graph_variables is not None and not isinstance(graph_variables, dict):
        raise AnsibleLookupError(
            "graph_variables parameter must be of key/value pairs. Please see docs for examples."
        )

    # Init API Call
    # -> "builb" infrahub api == XX
    # -> "builb" infrahub GraphQL request = XX
    # -> "builb" infrahub GraphQL response = XX

    # -> Check GraphQL responses (Exception or Records)

    results = None

    return [results]


class LookupModule(LookupBase):
    """
    LookupModule(LookupBase) is defined by Ansible
    """

    def run(self, terms, variables=None, graph_variables=None, **kwargs):
        """Runs Ansible Lookup Plugin for using Infrahub GraphQL endpoint

        Raises:
            AnsibleLookupError: Error in data loaded into the plugin

        Returns:
            dict: Data returned from GraphQL endpoint
        """
        lookup_info = infrahub_lookup_graphql(
            query=terms[0],
            variables=variables,
            graph_variables=graph_variables,
            **kwargs
        )

        # Results should be the data response of the query to be returned as a lookup
        return lookup_info
