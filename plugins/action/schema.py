# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Infrahub Action Plugin to handle schema files on the controller."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from pathlib import Path
from typing import Any

from ansible.errors import AnsibleError
from ansible.plugins.action import ActionBase

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class ActionModule(ActionBase):
    """Action plugin that reads schema files on the Ansible controller before delegating to the module.

    Schema files must be read on the controller (not on remote hosts), so this action plugin
    reads and parses YAML files locally, then passes their contents as inline schemas to the module.
    """

    def run(self, tmp: Any | None = None, task_vars: Any | None = None) -> dict:
        self._supports_check_mode = True
        self._supports_async = True

        result = super(ActionModule, self).run(tmp, task_vars)  # noqa: UP008
        del tmp

        if result.get("skipped"):
            return result

        if result.get("invocation", {}).get("module_args"):
            del result["invocation"]["module_args"]

        args = dict(self._task.args)
        schema_files = args.pop("schema_files", None)

        if schema_files:
            if not HAS_YAML:
                raise AnsibleError("PyYAML is required to load schema files. Install it with: pip install pyyaml")

            file_schemas = self._load_schema_files(schema_files)

            # Merge file-based schemas with any inline schemas
            existing_schemas = args.get("schemas") or []
            args["schemas"] = list(existing_schemas) + file_schemas

        # Delegate to the module with the resolved schemas
        result = self._execute_module(
            module_name="opsmill.infrahub.schema",
            module_args=args,
            task_vars=task_vars,
        )

        return result

    def _load_schema_files(self, file_paths: list[str]) -> list[dict]:
        """Read and parse YAML schema files on the controller.

        Parameters:
            file_paths: List of YAML file paths to read.

        Returns:
            Flat list of schema definitions extracted from files.
        """
        schemas: list[dict] = []
        for file_path in file_paths:
            try:
                # Resolve path relative to the playbook/role
                resolved_path = self._find_needle("files", file_path)
                with Path(resolved_path).open(encoding="utf-8") as fh:
                    data = yaml.safe_load(fh)
            except AnsibleError:
                raise
            except FileNotFoundError:
                raise AnsibleError(f"Schema file not found: {resolved_path}")
            except yaml.YAMLError as exc:
                raise AnsibleError(f"Failed to parse YAML file '{resolved_path}': {exc}")

            if not isinstance(data, dict):
                raise AnsibleError(f"Schema file '{resolved_path}' must contain a YAML mapping.")

            nodes = data.get("nodes") or []
            generics = data.get("generics") or []
            extensions = data.get("extensions") or {}

            schemas.extend(nodes)
            schemas.extend(generics)

            ext_nodes = extensions.get("nodes") or []
            ext_generics = extensions.get("generics") or []
            schemas.extend(ext_nodes)
            schemas.extend(ext_generics)

        return schemas
