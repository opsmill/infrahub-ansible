# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import InfrahubModule


class NodeModule(InfrahubModule):
    """
    This module can be use to create/update/delete any users defined Node
    """

    def run(self):
        data = self.data

        kind = data.get("kind")
        if not kind:
            self._handle_errors(msg="Missing required parameter: 'kind'")

        self.result = {"changed": False}

        schema = self.client.fetch_single_schema(kind=kind, raise_when_missing=False)
        if not schema:
            self._handle_errors(msg=f"Non-existing kind '{kind}'")

        self.infrahub_node = self._get_object(schema=schema, kind=kind, data=data.get("data", {}))
        if self.state == "present":
            self._ensure_object_exists(kind=kind, data=data)
        elif self.state == "absent":
            self._ensure_object_absent(kind=kind, data=data)

        serialized_object = None
        if self.infrahub_node:
            serialized_object = self.infrahub_node.get_raw_graphql_data()
        self.result.update({kind: serialized_object})

        self.module.exit_json(**self.result)
