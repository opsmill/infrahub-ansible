# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to fetch the content of an artifact."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import os
from typing import Any

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    InfrahubclientWrapper,
    verify_infrahub_sdk,
)


class ActionModule(ActionBase):
    """
    Ansible Action Module to fetch the content of an artifact.

    Parameters:
        ActionBase (ActionBase): Ansible Action Plugin
    """

    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict[str, Any]:
        """
        Run of action plugin to fetch the content of an artifact.

        Parameters:
            tmp ([type], optional): [description]. Defaults to None.
            task_vars ([type], optional): [description]. Defaults to None.
        """

        verify_infrahub_sdk(exception=AnsibleError)

        self._supports_check_mode = True
        self._supports_async = True

        result: dict[str, Any] = super(ActionModule, self).run(tmp, task_vars)  # noqa: UP008
        del tmp

        if result.get("skipped"):
            return result

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

        artifact_name = args.get("artifact_name")
        target_id = args.get("target_id")
        artifact_id = args.get("artifact_id")

        if not artifact_name and not artifact_id:
            raise AnsibleError("Missing artifact_name or artifact_id")
        if artifact_name and not target_id:
            raise AnsibleError("Missing target_id when using artifact_name")
        if target_id and not artifact_name:
            raise AnsibleError("Missing artifact_name when using target_id")

        if artifact_name:
            filters = {
                "name__value": artifact_name,
                "object__ids": [target_id],
            }
            failure_msg = f"Unable to find '{artifact_name}' for '{target_id}'."
        else:
            filters = {
                "ids": [artifact_id],
            }
            failure_msg = f"Unable to find artifact with id '{artifact_id}'"

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
            Display().v("Fetch Artifacts")
            artifact_result: dict[str, Any] = client.fetch_single_artifact(filters=filters)

            # Better error handling
            if not artifact_result:
                return {
                    "failed": True,
                    "msg": failure_msg,
                }

        except Exception as exp:
            raise AnsibleError(str(exp)) from exp

        return artifact_result
