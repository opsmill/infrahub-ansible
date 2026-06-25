# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the schema action plugin's controller-side file loading.

`_load_schema_files` reads + parses YAML schema files on the controller and
flattens nodes/generics/extensions. We bypass ActionBase.__init__ and stub
`_find_needle` (path resolution) so the method reads the temp files we give it.
"""

from __future__ import annotations

import pytest
from ansible.errors import AnsibleError
from ansible_collections.opsmill.infrahub.plugins.action.schema import ActionModule


def _action():
    action = ActionModule.__new__(ActionModule)
    # _find_needle normally resolves a path relative to the role's files/ dir;
    # here we hand back the path unchanged so it reads our temp file directly.
    action._find_needle = lambda _kind, path: path
    return action


def test_loads_and_flattens_nodes_and_generics(tmp_path):
    schema_file = tmp_path / "schema.yml"
    schema_file.write_text(
        "nodes:\n"
        "  - {namespace: Testing, name: Thing}\n"
        "generics:\n"
        "  - {namespace: Testing, name: GenericThing}\n"
        "extensions:\n"
        "  nodes:\n"
        "    - {namespace: Testing, name: ExtThing}\n"
    )

    result = _action()._load_schema_files([str(schema_file)])

    names = {item["name"] for item in result}
    assert names == {"Thing", "GenericThing", "ExtThing"}


def test_missing_file_raises_ansible_error(tmp_path):
    with pytest.raises(AnsibleError, match="Schema file not found"):
        _action()._load_schema_files([str(tmp_path / "does-not-exist.yml")])


def test_invalid_yaml_raises_ansible_error(tmp_path):
    bad = tmp_path / "bad.yml"
    bad.write_text("nodes: [unterminated\n")
    with pytest.raises(AnsibleError, match="Failed to parse YAML file"):
        _action()._load_schema_files([str(bad)])


def test_non_mapping_raises_ansible_error(tmp_path):
    not_a_map = tmp_path / "list.yml"
    not_a_map.write_text("- just\n- a\n- list\n")
    with pytest.raises(AnsibleError, match="must contain a YAML mapping"):
        _action()._load_schema_files([str(not_a_map)])
