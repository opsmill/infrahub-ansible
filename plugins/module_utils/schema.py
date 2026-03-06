# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from pathlib import Path

from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import (
    HAS_INFRAHUBCLIENT,
    INFRAHUBCLIENT_IMP_ERR,
    InfrahubclientWrapper,
)

if HAS_INFRAHUBCLIENT:

    class SchemaModule:
        """Module to load, check, or export Infrahub schemas."""

        def __init__(self, module, client=None):
            self.module = module
            self.check_mode = self.module.check_mode

            api_endpoint = self.module.params.get("api_endpoint")
            token = self.module.params.get("token")
            if api_endpoint is None:
                self.module.fail_json(msg="Missing Infrahub API Endpoint")
            if token is None:
                self.module.fail_json(msg="Missing Infrahub TOKEN")

            api_endpoint = api_endpoint.strip("/")
            validate_certs = self.module.params.get("validate_certs")
            if not isinstance(validate_certs, bool):
                self.module.fail_json(msg="validate_certs must be a boolean")

            timeout = self.module.params.get("timeout")
            branch = self.module.params.get("branch")

            try:
                if client is None:
                    self.client = InfrahubclientWrapper(
                        api_endpoint=api_endpoint,
                        token=token,
                        branch=branch,
                        timeout=timeout,
                        validate_certs=validate_certs,
                    )
                else:
                    self.client = client
            except Exception as exc:
                self.module.fail_json(msg=str(exc), changed=False)

        def run(self):
            """Dispatch to the appropriate action handler."""
            action = self.module.params["action"]

            if action == "load":
                self._load()
            elif action == "check":
                self._check()
            elif action == "export":
                self._export()

        def _gather_schemas(self):
            """Merge inline schemas and file-based schemas into a single list.

            Returns:
                list[dict]: Combined list of schema definitions.
            """
            schemas = list(self.module.params.get("schemas") or [])
            schema_files = self.module.params.get("schema_files") or []

            if schema_files:
                file_schemas = self._load_schema_files(schema_files)
                schemas.extend(file_schemas)

            if not schemas:
                self.module.fail_json(
                    msg="At least one of 'schemas' or 'schema_files' must be provided for load/check actions."
                )

            return schemas

        def _load_schema_files(self, file_paths):
            """Read and parse YAML schema files, extracting schema lists.

            Parameters:
                file_paths (list[str]): List of YAML file paths to read.

            Returns:
                list[dict]: Flat list of schema definitions extracted from files.
            """
            if not HAS_YAML:
                self.module.fail_json(
                    msg="PyYAML is required to load schema files. Install it with: pip install pyyaml"
                )

            schemas = []
            for file_path in file_paths:
                try:
                    with Path(file_path).open(encoding="utf-8") as fh:
                        data = yaml.safe_load(fh)
                except FileNotFoundError:
                    self.module.fail_json(msg=f"Schema file not found: {file_path}")
                except yaml.YAMLError as exc:
                    self.module.fail_json(msg=f"Failed to parse YAML file '{file_path}': {exc}")

                if not isinstance(data, dict):
                    self.module.fail_json(msg=f"Schema file '{file_path}' must contain a YAML mapping.")

                nodes = data.get("nodes") or []
                generics = data.get("generics") or []
                extensions = data.get("extensions") or {}

                schemas.extend(nodes)
                schemas.extend(generics)

                # Handle extensions (nodes/generics nested under extensions)
                ext_nodes = extensions.get("nodes") or []
                ext_generics = extensions.get("generics") or []
                schemas.extend(ext_nodes)
                schemas.extend(ext_generics)

            return schemas

        def _load(self):
            """Load schemas into Infrahub."""
            schemas = self._gather_schemas()
            branch = self.module.params.get("branch") or "main"
            wait_until_converged = self.module.params.get("wait_until_converged") or False

            # In check mode, run check instead of load
            if self.check_mode:
                self._check_for_check_mode(schemas, branch)
                return

            try:
                response = self.client.client.schema.load(
                    schemas=schemas,
                    branch=branch,
                    wait_until_converged=wait_until_converged,
                )
            except Exception as exc:
                self.module.fail_json(msg=f"Failed to load schema: {exc}", changed=False)

            # SchemaLoadResponse has: hash, previous_hash, errors, warnings, schema_updated
            if response.errors:
                error_msg = response.errors if isinstance(response.errors, str) else str(response.errors)
                self.module.fail_json(
                    msg=f"Schema load returned errors: {error_msg}",
                    errors=response.errors,
                    changed=False,
                )

            result = {
                "changed": bool(response.schema_updated),
                "schema_updated": bool(response.schema_updated),
                "hash": response.hash,
                "previous_hash": response.previous_hash,
                "warnings": response.warnings or [],
                "msg": "Schema loaded successfully" if response.schema_updated else "Schema already up to date",
            }

            self.module.exit_json(**result)

        def _check_for_check_mode(self, schemas, branch):
            """Run schema check as a substitute for load in check mode."""
            try:
                valid, response = self.client.client.schema.check(
                    schemas=schemas,
                    branch=branch,
                )
            except Exception as exc:
                self.module.fail_json(msg=f"Failed to check schema: {exc}", changed=False)

            if not valid:
                self.module.fail_json(
                    msg="Schema validation failed (check mode)",
                    valid=False,
                    errors=response,
                    changed=False,
                )

            self.module.exit_json(
                changed=False,
                valid=True,
                msg="Schema check passed (check mode — no changes applied)",
            )

        def _check(self):
            """Validate schemas without applying them."""
            schemas = self._gather_schemas()
            branch = self.module.params.get("branch") or "main"

            try:
                valid, response = self.client.client.schema.check(
                    schemas=schemas,
                    branch=branch,
                )
            except Exception as exc:
                self.module.fail_json(msg=f"Failed to check schema: {exc}", changed=False)

            if not valid:
                self.module.fail_json(
                    msg="Schema validation failed",
                    valid=False,
                    errors=response,
                    changed=False,
                )

            self.module.exit_json(
                changed=False,
                valid=True,
                msg="Schema validation passed",
            )

        def _export(self):
            """Export schemas from Infrahub."""
            branch = self.module.params.get("branch") or "main"
            namespaces = self.module.params.get("namespaces")

            kwargs = {"branch": branch}
            if namespaces:
                kwargs["namespaces"] = namespaces

            try:
                exported = self.client.client.schema.export(**kwargs)
            except Exception as exc:
                self.module.fail_json(msg=f"Failed to export schema: {exc}", changed=False)

            self.module.exit_json(
                changed=False,
                schemas=exported,
                msg="Schema exported successfully",
            )


if not HAS_INFRAHUBCLIENT:

    class SchemaModule:  # type: ignore[no-redef]
        def __init__(self, module, _client=None):
            module.fail_json(
                msg="infrahub-sdk is required. Install it with: pip install infrahub-sdk",
                exception=INFRAHUBCLIENT_IMP_ERR,
            )

        def run(self):
            pass
