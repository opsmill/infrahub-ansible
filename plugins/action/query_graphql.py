# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to Query GraphQL."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
from typing import Any, Dict, Optional

from ansible.errors import AnsibleError
from ansible.module_utils.six import raise_from
from ansible.plugins.action import ActionBase
from ansible_collections.infrahub.infrahub.plugins.module_utils.infrahub_utils import (
    InfrahubclientWrapper,
    InfrahubQueryProcessor,
    HAS_INFRAHUBCLIENT,
    INFRAHUBCLIENT_IMP_ERR,
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
            raise_from(
                AnsibleError("infrahub_client must be installed to use this plugin"),
                INFRAHUBCLIENT_IMP_ERR,
            )
        
        self._supports_check_mode = True
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp

        if result.get("skipped"):
            return None

        if result.get("invocation", {}).get("module_args"):
            del result["invocation"]["module_args"]

        args = self._task.args

        api_endpoint = args.get("api_endpoint") or os.getenv("INFRAHUB_API")
        token = args.get("token") or os.getenv("INFRAHUB_TOKEN")
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

        query_str = args.get("query")
        filters = args.get("filters")
        if query_str is None:
            raise AnsibleError("Query parameter was not passed")
        if not isinstance(query_str, str):
            raise AnsibleError("Query parameter must be of type Str")
        if filters is not None and not isinstance(filters, Dict):
            raise AnsibleError("Filters parameter must be a list of Dict")

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
            raise_from(AnsibleError(str(exp)), exp)

        return results
