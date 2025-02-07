# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to create nodes."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import os
from typing import Any

from ansible.errors import AnsibleError
from ansible.module_utils.six import raise_from
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    InfrahubclientWrapper,
    InfrahubNodesProcessor,
)


class ActionModule(ActionBase):
    """
    Ansible Action Module to create nodes in Infrahub.

    Parameters:
        ActionBase (ActionBase): Ansible Action Plugin
    """

    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict:
        """
        Run of action plugin to create nodes.

        Parameters:
            tmp ([type], optional): [description]. Defaults to None.
            task_vars ([type], optional): [description]. Defaults to None.
        """

        if not HAS_INFRAHUBCLIENT:
            raise (AnsibleError("infrahub_sdk must be installed to use this plugin"))

        self._supports_check_mode = True
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)  # noqa: UP008
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

        name = args.get("name")
        description = args.get("description")
        sync_with_git = args.get("sync_with_git", False)

        if not name:
            raise AnsibleError("Missing required parameter: 'name'")

        try:
            Display().v("Initializing Infrahub Client")
            client = InfrahubclientWrapper(
                api_endpoint=api_endpoint,
                token=token,
                branch=branch,
                timeout=timeout,
                validate_certs=validate_certs,
                display=Display(),
            )

            Display().v(f"Creating branch {name}")
            processor = InfrahubNodesProcessor(client=client, display=Display())
            branch = processor.create_branch(name=name, description=description, sync_with_git=sync_with_git)
            if not branch:
                result["response"] = None
            else:
                result["changed"] = True
                result["data"] = {
                    "id": branch.id,
                }
                result["response"] = str(branch)

        except Exception as exp:
            raise_from(AnsibleError(str(exp)), exp)

        return result
