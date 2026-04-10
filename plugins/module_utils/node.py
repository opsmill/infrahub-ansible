# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from pathlib import Path

from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    InfrahubModule,
    InfrahubNodesProcessor,
    get_node_identifier,
)


class NodeModule(InfrahubModule):
    """
    This module can be use to create/update/delete any users defined Node
    """

    def run(self) -> None:
        data = self.data

        kind = data.get("kind")
        if not kind:
            self._handle_errors(msg="Missing required parameter: 'kind'")

        file_path = data.get("file_path")
        fetch_file = data.get("fetch_file", False)

        # T009: validate file exists before any API call
        if file_path and not Path(file_path).exists():
            self._handle_errors(msg=f"file_path '{file_path}' does not exist on the controller")

        self.result = {"changed": False}

        schema = self.client.fetch_single_schema(kind=kind, raise_when_missing=False)
        if not schema:
            self._handle_errors(msg=f"Non-existing kind '{kind}'")

        is_file_object = hasattr(schema, "inherit_from") and "CoreFileObject" in (schema.inherit_from or [])

        # file_path and fetch_file are mutually exclusive
        if file_path and fetch_file:
            self._handle_errors(msg="'file_path' and 'fetch_file' are mutually exclusive.")

        # CoreFileObject kinds require either file_path or fetch_file
        if is_file_object and not file_path and not fetch_file:
            self._handle_errors(
                msg=f"Kind '{kind}' inherits from CoreFileObject. 'file_path' or 'fetch_file' is required."
            )

        # Non-CoreFileObject kinds cannot use file_path or fetch_file
        if not is_file_object and (file_path or fetch_file):
            param = "file_path" if file_path else "fetch_file"
            self._handle_errors(
                msg=f"Kind '{kind}' is not a CoreFileObject. '{param}' requires a CoreFileObject kind."
            )

        lookup_data = data.get("data", {})
        self.infrahub_node = self._lookup_node(
            schema=schema, kind=kind, data=lookup_data, file_path=file_path, is_file_object=is_file_object,
        )

        if self.state == "present":
            self._ensure_object_exists(kind=kind, data=data, file_path=file_path)
        elif self.state == "absent":
            self._ensure_object_absent(kind=kind, data=data)

        # US2: return file content if fetch_file is requested
        if fetch_file and not self.check_mode and self.infrahub_node:
            file_content = self.client.fetch_file_content(self.infrahub_node)
            self.result.update(file_content)

        serialized_object = None
        if self.infrahub_node:
            raw = self.infrahub_node.get_raw_graphql_data()
            # After create, raw data lacks server-populated fields (id, file_name,
            # checksum, etc.). Re-fetch to get the complete object.
            if (raw is None or "id" not in raw) and self.infrahub_node.id:
                self.infrahub_node = self.client.fetch_single_node(
                    kind=kind, id=self.infrahub_node.id, raise_when_missing=False
                )
            if self.infrahub_node:
                serialized_object = self.infrahub_node.get_raw_graphql_data()
        self.result.update({kind: serialized_object})

        self.module.exit_json(**self.result)

    def _lookup_node(
        self, schema, kind: str, data: dict, file_path: str | None = None, is_file_object: bool = False,
    ):
        """Look up an existing node in Infrahub.

        For CoreFileObject kinds without an HFID, derives file_name from
        file_path and uses a file_name__value filter for lookup.
        Otherwise, delegates to _get_object which uses id/hfid.

        Parameters:
            schema: The schema definition for this kind.
            kind (str): The Kind of the node.
            data (dict): The user-provided attribute data.
            file_path (str | None): Local file path (CoreFileObject only).
            is_file_object (bool): Whether this kind inherits from CoreFileObject.

        Returns:
            InfrahubNodeSync | None: The existing node or None.
        """
        if is_file_object and not schema.human_friendly_id and "id" not in data:
            file_name = Path(file_path).name
            try:
                return self.client.fetch_single_node(
                    kind=kind, filters={"file_name__value": file_name}, raise_when_missing=False
                )
            except Exception as exc:
                self._handle_errors(
                    msg=f"An error occurred while retrieving {kind} by file_name '{file_name}' due to {exc}"
                )

        return self._get_object(schema=schema, kind=kind, data=data)

    def _ensure_object_exists(self, kind: str, data: dict, file_path=None) -> None:
        """
        Used when `state` is present to make sure an object exists.
        Delegates to file-aware create/update when file_path is set.
        """
        object_data = data.get("data") or {}
        if file_path:
            if not self.infrahub_node:
                self.infrahub_node, diff = self._create_object_with_file(
                    kind=kind, data=object_data, file_path=file_path
                )
                identifier = get_node_identifier(node=self.infrahub_node)
                self.result["msg"] = f"{kind} {identifier} created"
                self.result["changed"] = True
                self.result["diff"] = diff
            else:
                self.infrahub_node, diff = self._update_object_with_file(data=object_data, file_path=file_path)
                identifier = get_node_identifier(node=self.infrahub_node)
                if diff:
                    self.result["msg"] = f"{kind} {identifier} updated"
                    self.result["changed"] = True
                    self.result["diff"] = diff
                else:
                    self.result["msg"] = f"{kind} {identifier} already exists"
        else:
            super()._ensure_object_exists(kind=kind, data=data)

    def _create_object_with_file(self, kind: str, data: dict, file_path: str):
        """
        Create a CoreFileObject node and upload the local file.

        Parameters:
            kind (str): The Kind of the Object to create
            data (dict): The attribute data for this object
            file_path (str): Local path to the file to upload

        Returns:
            tuple(InfrahubNodeSync, dict): The created node and the Ansible diff.
        """
        processor = InfrahubNodesProcessor(client=self.client)
        try:
            node = processor.create_node(kind=kind, data=data)
            if not self.check_mode:
                node.upload_from_path(Path(file_path))
                processor.save_node(node=node)
        except Exception as exc:
            self._handle_errors(msg=str(exc))

        diff = self._build_diff(before={"state": "absent"}, after={"state": "present"})
        return node, diff

    def _update_object_with_file(self, data: dict, file_path: str):
        """
        Update a CoreFileObject node, re-uploading the file only if its SHA-1 checksum changed.

        Parameters:
            data (dict): The attribute data for this object
            file_path (str): Local path to the file to compare/upload

        Returns:
            tuple(InfrahubNodeSync, dict | None): The node and the Ansible diff (None if unchanged).
        """
        local_checksum = self.client.get_file_object_local_checksum(file_path)
        server_checksum = self.infrahub_node.checksum.value
        file_changed = local_checksum != server_checksum

        if file_changed:
            # Apply attr changes in memory before saving
            for attr_name, attr_value in data.items():
                if attr_name in self.infrahub_node._schema.attribute_names:
                    if isinstance(attr_value, dict) and "value" in attr_value:
                        attr_value = attr_value["value"]
                    setattr(self.infrahub_node, attr_name, attr_value)
            if not self.check_mode:
                self.infrahub_node.upload_from_path(Path(file_path))
                self.infrahub_node.save()
            diff = self._build_diff(before={"checksum": server_checksum}, after={"checksum": local_checksum})
            return self.infrahub_node, diff

        # File unchanged — fall through to regular attr update
        return self._update_object(data=data)
