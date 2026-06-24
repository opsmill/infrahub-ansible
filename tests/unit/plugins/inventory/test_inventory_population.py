# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Unit tests for the inventory plugin's host/group population logic.

These exercise the plugin's own value-add — turning resolved node attributes
into hosts, variables, composed vars, keyed groups, conditional groups and
hostname selection — without any network. The data-fetch boundary
(``InfrahubNodesProcessor.fetch_and_process``) is mocked to return a synthetic
``host_node_attributes`` dict, so the tests are fast and free of GraphQL fixtures.
"""

from __future__ import annotations

import os
from unittest import mock

import pytest
from ansible.errors import AnsibleError
from ansible.inventory.data import InventoryData
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import inventory_loader

FETCH_TARGET = (
    "ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils.InfrahubNodesProcessor.fetch_and_process"
)


def run_inventory(tmp_path, config: str, host_node_attributes: dict) -> InventoryData:
    """Run the inventory plugin against a config, with fetch mocked to return the given data."""
    cfg = tmp_path / "infrahub.yml"
    cfg.write_text(config)

    # endpoint/token are only needed so client construction + auth don't error;
    # no network happens because fetch_and_process is mocked.
    env = {"INFRAHUB_ADDRESS": "http://mock", "INFRAHUB_API_TOKEN": "unit-test-token"}
    plugin = inventory_loader.get("opsmill.infrahub.inventory")
    with mock.patch.dict(os.environ, env), mock.patch(FETCH_TARGET, return_value=host_node_attributes):
        plugin.parse(InventoryData(), DataLoader(), str(cfg))
    return plugin.inventory


BASE_CONFIG = """\
plugin: opsmill.infrahub.inventory
nodes:
  TestingHost:
    include:
      - name
      - role
"""


def _hosts(attrs):
    return {key: dict(value) for key, value in attrs.items()}


def test_hosts_and_plain_variables(tmp_path):
    inv = run_inventory(
        tmp_path,
        BASE_CONFIG,
        _hosts({"web1": {"name": "web1", "role": "edge", "id": "1"}}),
    )
    assert "web1" in inv.hosts
    assert inv.get_host("web1").get_vars()["role"] == "edge"


def test_compose_variables(tmp_path):
    config = BASE_CONFIG + "compose:\n  loud_role: role | upper\n  same_role: role\n"
    inv = run_inventory(
        tmp_path,
        config,
        _hosts({"web1": {"name": "web1", "role": "edge", "id": "1"}}),
    )
    host_vars = inv.get_host("web1").get_vars()
    assert host_vars["loud_role"] == "EDGE"
    assert host_vars["same_role"] == "edge"


def test_keyed_groups(tmp_path):
    config = BASE_CONFIG + "keyed_groups:\n  - prefix: role\n    key: role | lower\n"
    inv = run_inventory(
        tmp_path,
        config,
        _hosts(
            {
                "web1": {"name": "web1", "role": "Edge", "id": "1"},
                "web2": {"name": "web2", "role": "Core", "id": "2"},
            }
        ),
    )
    groups = inv.get_groups_dict()
    assert "web1" in groups["role_edge"]
    assert "web2" in groups["role_core"]


def test_conditional_groups(tmp_path):
    config = BASE_CONFIG + "groups:\n  edges: \"role == 'edge'\"\n"
    inv = run_inventory(
        tmp_path,
        config,
        _hosts(
            {
                "web1": {"name": "web1", "role": "edge", "id": "1"},
                "web2": {"name": "web2", "role": "core", "id": "2"},
            }
        ),
    )
    groups = inv.get_groups_dict()
    assert groups["edges"] == ["web1"]


def test_hostnames_priority_rekeys(tmp_path):
    # fetch returns data keyed by id; hostnames re-keys by the `name` attribute.
    config = BASE_CONFIG + "hostnames:\n  - name\n"
    inv = run_inventory(
        tmp_path,
        config,
        _hosts({"id-1": {"name": "web1", "role": "edge", "id": "id-1"}}),
    )
    assert "web1" in inv.hosts
    assert "id-1" not in inv.hosts


def test_keyed_groups_leading_separator_false(tmp_path):
    # No prefix + leading_separator:false => group name is the bare key value.
    config = BASE_CONFIG + (
        "keyed_groups:\n  - key: role | lower\n    leading_separator: false\nleading_separator: false\n"
    )
    inv = run_inventory(
        tmp_path,
        config,
        _hosts({"web1": {"name": "web1", "role": "Edge", "id": "1"}}),
    )
    groups = inv.get_groups_dict()
    assert "edge" in groups
    assert "_edge" not in groups
    assert "web1" in groups["edge"]


def test_strict_raises_on_bad_compose(tmp_path):
    # strict:true turns an undefined reference in compose into a hard error.
    config = BASE_CONFIG + "strict: true\ncompose:\n  bad: this_var_does_not_exist | upper\n"
    with pytest.raises(AnsibleError):
        run_inventory(
            tmp_path,
            config,
            _hosts({"web1": {"name": "web1", "role": "edge", "id": "1"}}),
        )
