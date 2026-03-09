# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from typing import Any

from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import InfrahubModule


class BranchModule(InfrahubModule):
    """
    This function should have all necessary code for endpoints within the application
    to create/update/delete InfrahubBranch
    """

    def run(self) -> None:
        data = self.data

        branch_name = data.get("name")
        if not branch_name:
            self._handle_errors(msg="Missing required parameter: 'name'")

        self.result: dict[str, Any] = {"changed": False}

        self.branch = self._get_branch(name=branch_name)
        if self.state == "present":
            self._ensure_branch_exists(data=data)
        elif self.state == "absent":
            self._ensure_branch_absent(data=data)

        serialized_object = str(self.branch)
        self.result["branch"] = serialized_object

        self.module.exit_json(**self.result)
