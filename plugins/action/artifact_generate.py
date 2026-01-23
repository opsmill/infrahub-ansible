# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to trigger artifact regeneration."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import os
from typing import Any

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    InfrahubclientWrapper,
)


class ActionModule(ActionBase):
    """
    Ansible Action Module to trigger artifact regeneration.

    Parameters:
        ActionBase (ActionBase): Ansible Action Plugin
    """

    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict:
        """
        Run of action plugin to trigger artifact regeneration.

        Parameters:
            tmp ([type], optional): [description]. Defaults to None.
            task_vars ([type], optional): [description]. Defaults to None.
        """

        if not HAS_INFRAHUBCLIENT:
            raise (AnsibleError("infrahub_sdk must be installed to use this plugin"))

        self._supports_check_mode = False
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)  # noqa: UP008
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
        artifact_id = args.get("artifact_id")
        target_ids = args.get("target_ids")

        if not artifact_name and not artifact_id:
            raise AnsibleError("Missing artifact_name or artifact_id")
        if not target_ids:
            raise AnsibleError("Missing target_ids")

        # Build filters - object__ids is added by generate_artifacts using first target_id
        filters = {"name__value": artifact_name} if artifact_name else {"ids": [artifact_id]}

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
            Display().v("Triggering Artifact Regeneration")
            result = client.generate_artifacts(filters=filters, target_ids=target_ids, branch=branch)
        except Exception as exp:
            raise AnsibleError(str(exp)) from exp

        return result
