# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to fetch file content from a CoreFileObject node."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

import base64
import os
from pathlib import Path
from typing import Any

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase
from ansible.utils.display import Display
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    TEXT_MIME_TYPES,
    InfrahubclientWrapper,
)


class ActionModule(ActionBase):
    """Ansible Action Module to fetch file content from a CoreFileObject node."""

    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict[str, Any]:
        """Run the object_file_fetch action plugin."""
        if not HAS_INFRAHUBCLIENT:
            raise AnsibleError("infrahub_sdk must be installed to use this plugin")

        self._supports_check_mode = False
        self._supports_async = True

        result: dict[str, Any] = super(ActionModule, self).run(tmp, task_vars)  # noqa: UP008
        del tmp

        if result.get("skipped"):
            return result

        if result.get("invocation", {}).get("module_args"):
            del result["invocation"]["module_args"]

        args = self._task.args

        # Credentials
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

        # Module-specific args
        kind = args.get("kind")
        node_id = args.get("node_id")
        hfid = args.get("hfid")
        dest = args.get("dest")

        # Validate: at least one of node_id or hfid required
        if not node_id and not hfid:
            raise AnsibleError("One of 'node_id' or 'hfid' is required")

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

            Display().v(f"Fetching CoreFileObject node kind={kind}")
            result_tuple = client.fetch_file_object(
                kind=kind,
                node_id=node_id,
                hfid=hfid,
                branch=branch,
            )
            if result_tuple is None:
                identifier = node_id or hfid
                raise AnsibleError(
                    f"Failed to fetch {kind} node (id={identifier}). "
                    "Check Infrahub server logs or run with -vvv for details."
                )
            node, content = result_tuple

            # Validate the fetched node is a CoreFileObject
            if not node.is_file_object():
                raise AnsibleError(
                    f"Kind '{kind}' is not a CoreFileObject. 'object_file_fetch' requires a CoreFileObject kind."
                )

        except AnsibleError:
            raise
        except Exception as exp:
            raise AnsibleError(str(exp)) from exp

        # Resolve dest path
        resolved_dest = None
        if dest is not None:
            dest_path = Path(dest)
            if dest.endswith("/") or dest_path.is_dir():
                file_name = node.file_name.value
                resolved_dest = str(dest_path / file_name)
            else:
                resolved_dest = str(dest_path)
            try:
                Path(resolved_dest).parent.mkdir(parents=True, exist_ok=True)
                Path(resolved_dest).write_bytes(content)
            except Exception as exp:
                raise AnsibleError(f"Failed to write file to '{resolved_dest}': {exp}") from exp

        # Build result
        file_type = node.file_type.value
        is_text = file_type in TEXT_MIME_TYPES
        result.update(
            {
                "binary": base64.b64encode(content).decode("ascii"),
                "text": content.decode("utf-8", errors="replace") if is_text else None,
                "file_name": node.file_name.value,
                "file_type": file_type,
                "file_size": node.file_size.value,
                "checksum": node.checksum.value,
                "node_id": str(node.id),
                "dest": resolved_dest,
                "msg": f"Fetched file '{node.file_name.value}' from {kind} node {node.id}",
            }
        )
        return result
