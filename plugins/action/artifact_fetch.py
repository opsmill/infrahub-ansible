# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to fetch the content of an artifact."""

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os

from ansible.errors import AnsibleError
from ansible.module_utils.six import raise_from
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
)
from infrahub_sdk import InfrahubClientSync, Config

class ActionModule(ActionBase):
    """
    Ansible Action Module to fetch the content of an artifact.

    Parameters:
        ActionBase (ActionBase): Ansible Action Plugin
    """

    def run(self, tmp=None, task_vars=None):
        """
        Run of action plugin to fetch the content of an artifact.

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

        artifact_name = args.get("artifact_name")
        target_id = args.get("target_id")

        results = {
            "json": None,
            "text": None,
        }

        try:
            Display().v("Initializing Infrahub Client")

            client = InfrahubClientSync(
                address=api_endpoint,
                default_branch=branch,
                config=Config(api_token=token, timeout=timeout),
            )

            artifact_node = client.get(kind="CoreArtifact", name__value=artifact_name, object__ids=[target_id])

            resp = client._get(url=f"{client.address}/api/storage/object/{artifact_node.storage_id.value}")

            if artifact_node.content_type.value == "application/json":
                results["json"] = resp.json()
            else:
                results["text"] = resp.text

        except Exception as exp:
            raise_from(AnsibleError(str(exp)), exp)

        return results
