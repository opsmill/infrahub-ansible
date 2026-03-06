# Copyright (c) 2025 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Ansible module to manage Infrahub schemas."""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

DOCUMENTATION = """
---
module: schema
author:
    - Benoit Kohler (@bearchitek)
version_added: "2.1.0"
short_description: Load, check, or export schemas in Infrahub
description:
    - Load, check, or export schemas in Infrahub through the Infrahub SDK.
    - Use C(action=load) to load schemas into Infrahub.
    - Use C(action=check) to validate schemas without applying them.
    - Use C(action=export) to export existing schemas from Infrahub.
requirements:
    - infrahub-sdk
options:
    api_endpoint:
        required: True
        description:
            - Endpoint of the Infrahub API, optional env=INFRAHUB_ADDRESS
        type: str
    token:
        required: True
        description:
            - The API token created through Infrahub, optional env=INFRAHUB_API_TOKEN
        type: str
    timeout:
        required: False
        description: Timeout for Infrahub requests in seconds
        type: int
        default: 10
    validate_certs:
        description:
            - Whether or not to validate SSL of the Infrahub instance
        required: False
        type: bool
        default: True
    action:
        required: True
        description:
            - The schema action to perform.
            - C(load) loads schemas into Infrahub.
            - C(check) validates schemas without applying them.
            - C(export) exports existing schemas from Infrahub.
        choices: [ load, check, export ]
        type: str
    branch:
        required: False
        description:
            - Branch in which the request is made
        type: str
        default: main
    schemas:
        required: False
        description:
            - List of inline schema definitions (nodes and generics).
            - For C(load) and C(check), at least one of C(schemas) or C(schema_files) must be provided.
        type: list
        elements: dict
    schema_files:
        required: False
        description:
            - List of YAML file paths containing schema definitions.
            - Files are read on the Ansible controller.
            - For C(load) and C(check), at least one of C(schemas) or C(schema_files) must be provided.
        type: list
        elements: path
    namespaces:
        required: False
        description:
            - List of namespace names to filter the export.
            - Only used with C(action=export).
        type: list
        elements: str
    wait_until_converged:
        required: False
        description:
            - Wait for schema to be synchronized across all workers.
            - Only used with C(action=load).
        type: bool
        default: False
"""

EXAMPLES = """
---
- name: Check schema from inline definition
  opsmill.infrahub.schema:
    action: check
    schemas:
      - name: Site
        namespace: Location
        attributes:
          - name: name
            kind: Text
            unique: true

- name: Load schema from file
  opsmill.infrahub.schema:
    action: load
    schema_files:
      - "schemas/my_schema.yml"

- name: Load schema with convergence wait
  opsmill.infrahub.schema:
    action: load
    schema_files:
      - "schemas/my_schema.yml"
    wait_until_converged: true

- name: Export all schemas
  opsmill.infrahub.schema:
    action: export
  register: result

- name: Export schemas for specific namespaces
  opsmill.infrahub.schema:
    action: export
    namespaces:
      - Infra
      - Location
  register: result
"""

RETURN = """
changed:
    description: Whether the schema was updated (load) or always false (check/export).
    returned: always
    type: bool
schema_updated:
    description: Whether the schema hash changed after loading.
    returned: action=load
    type: bool
hash:
    description: New schema hash after loading.
    returned: action=load
    type: str
previous_hash:
    description: Previous schema hash before loading.
    returned: action=load
    type: str
warnings:
    description: Schema warnings returned during load.
    returned: action=load
    type: list
valid:
    description: Whether the schema passed validation.
    returned: action=check
    type: bool
errors:
    description: Validation errors when schema check fails.
    returned: action=check (on failure)
    type: dict
schemas:
    description: Exported schemas organized by namespace.
    returned: action=export
    type: dict
msg:
    description: Message indicating the result of the operation.
    returned: always
    type: str
"""

from copy import deepcopy

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils import INFRAHUB_ARG_SPEC
from ansible_collections.opsmill.infrahub.plugins.module_utils.schema import SchemaModule


def main():
    """Main entry point for module execution to load/check/export schemas."""
    argument_spec = deepcopy(INFRAHUB_ARG_SPEC)
    # Remove 'state' — not applicable for schema operations
    argument_spec.pop("state", None)
    argument_spec.update(
        action=dict(required=True, type="str", choices=["load", "check", "export"]),
        branch=dict(required=False, type="str", default="main"),
        schemas=dict(required=False, type="list", elements="dict"),
        schema_files=dict(required=False, type="list", elements="path"),
        namespaces=dict(required=False, type="list", elements="str"),
        wait_until_converged=dict(required=False, type="bool", default=False),
    )

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    schema_module = SchemaModule(module=module)
    schema_module.run()


if __name__ == "__main__":  # pragma: no cover
    main()
