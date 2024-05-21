# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to Query GraphQL."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
from typing import Dict

from ansible.errors import AnsibleError
from ansible.module_utils.six import raise_from
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    InfrahubclientWrapper,
    InfrahubQueryProcessor,
)


class ActionModule(ActionBase):
    """
    Ansible Action Module to interact with Infrahub GraphQL Endpoint.

    Parameters:
        ActionBase (ActionBase): Ansible Action Plugin
    """

    def run(self, tmp=None, task_vars=None):
        """
        Run of action plugin for interacting with Infrahub GraphQL API.

        Parameters:
            tmp ([type], optional): [description]. Defaults to None.
            task_vars ([type], optional): [description]. Defaults to None.
        """

        if not HAS_INFRAHUBCLIENT:
            raise (AnsibleError("infrahub_sdk must be installed to use this plugin"))

        self._supports_check_mode = True
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        if result.get("skipped"):
            return None

        if result.get("invocation", {}).get("module_args"):
            del result["invocation"]["module_args"]

        args = self._task.args

        api_endpoint = args.get("api_endpoint") or os.getenv("INFRAHUB_ADDRESS")
        token = args.get("token") or os.getenv("INFRAHUB_API_TOKEN")
        if api_endpoint is None:
            raise AnsibleError("Missing Infrahub API Endpoint")
        if token is None:
            raise AnsibleError("Missing Infrahub TOKEN")

        api_endpoint = api_endpoint.strip("/")

        validate_certs = args.get("validate_certs", True)
        if not isinstance(validate_certs, bool):
            raise AnsibleError("validate_certs must be a boolean")

        timeout = args.get("timeout", 10)
        branch = args.get("branch", "main")

        query = args.get("query")
        graph_variables = args.get("graph_variables")
        update_hostvars = args.get("update_hostvars", False)
        if query is None:
            raise AnsibleError("Query parameter was not passed")
        if isinstance(query, (Dict, str)):
            graphql_query = query
        if graph_variables is not None and not isinstance(graph_variables, Dict):
            raise AnsibleError("graph_variables parameter must be a list of Dict")
        if not isinstance(update_hostvars, bool):
            raise AnsibleError("update_hostvars must be a boolean")

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
            response = processor.fetch_and_process(query=graphql_query, variables=graph_variables)
            results["data"] = response
            if update_hostvars:
                results["ansible_facts"] = response

        except Exception as exp:
            raise_from(AnsibleError(str(exp)), exp)

        return results
