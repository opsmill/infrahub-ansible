# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Integration tests for the inventory plugin against a live Infrahub (testcontainers).

Seeds a small host topology, then exercises the plugin two ways:
- `ansible-inventory --list` as a subprocess (the real Ansible inventory pipeline),
- `InventoryModule.parse()` via the plugin loader (finer-grained assertions).

Both authenticate with the container's seeded initial admin token.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("infrahub_testcontainers")

from ansible.inventory.data import InventoryData
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import inventory_loader
from infrahub_sdk.testing.docker import TestInfrahubDockerClient
from infrahub_testcontainers.container import PROJECT_ENV_VARIABLES

from .schema import seed_dataset

pytestmark = pytest.mark.integration

ADMIN_TOKEN = PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]
CONFIGS = Path(__file__).parent / "configs"
ALL_HOSTS = {"host-a", "host-b", "host-c", "host-d"}


def _parse_cli_inventory(stdout: str) -> tuple[set[str], dict[str, set[str]], dict]:
    data = json.loads(stdout)
    hostvars = data.get("_meta", {}).get("hostvars", {})
    hosts = set(hostvars)
    groups = {
        name: set(body.get("hosts", []))
        for name, body in data.items()
        if name not in ("_meta", "all", "ungrouped") and isinstance(body, dict)
    }
    return hosts, groups, hostvars


class TestInventoryIntegration(TestInfrahubDockerClient):
    @pytest.fixture(scope="class")
    def dataset(self, client_sync) -> dict:
        return seed_dataset(client_sync)

    def _env(self, infrahub_port: int) -> dict:
        env = os.environ.copy()
        env["INFRAHUB_ADDRESS"] = f"http://localhost:{infrahub_port}"
        env["INFRAHUB_API_TOKEN"] = ADMIN_TOKEN
        env["ANSIBLE_INVENTORY_ENABLED"] = "opsmill.infrahub.inventory"
        return env

    def _run_cli(self, infrahub_port: int, config: str) -> tuple[set[str], dict[str, set[str]], dict]:
        binary = shutil.which("ansible-inventory")
        if not binary:
            pytest.skip("ansible-inventory not on PATH")
        result = subprocess.run(
            [binary, "-i", str(CONFIGS / config), "--list"],
            env=self._env(infrahub_port),
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"ansible-inventory failed:\n{result.stderr}"
        return _parse_cli_inventory(result.stdout)

    def test_cli_basic_lists_all_hosts(self, infrahub_port, dataset):
        hosts, _groups, hostvars = self._run_cli(infrahub_port, "basic.yml")
        assert hosts == ALL_HOSTS
        assert hostvars["host-a"]["role"] == "edge"
        assert hostvars["host-d"]["platform"] == "nxos"

    def test_cli_grouping(self, infrahub_port, dataset):
        hosts, groups, _hostvars = self._run_cli(infrahub_port, "grouping.yml")
        assert hosts == ALL_HOSTS
        assert groups["site_paris"] == {"host-a", "host-b"}
        assert groups["site_denver"] == {"host-c", "host-d"}
        assert groups["region_emea"] == {"host-a", "host-b"}
        assert groups["region_amer"] == {"host-c", "host-d"}
        assert groups["edge_devices"] == {"host-a", "host-c"}

    def test_cli_resolves_attributes_behind_a_generic_peer(self, infrahub_port, dataset):
        """``site.name`` has to survive the relationship declaring a generic peer.

        ``Host.site`` points at the ``TestingLocation`` generic, which exposes only
        ``shortname``; ``name`` and ``region`` belong to the concrete ``TestingSite``.
        The SDK builds a relationship's inline payload from the declared peer schema,
        so both arrive empty and the plugin has to go and get them. This is the shape
        real schemas use, and the failure it guards against is host variables coming
        back null.

        Scope, measured by mutation: this asserts the values *resolve*, not what they
        cost. Disabling peer warming entirely still passes here, because the refill
        fallback recovers them -- at 4x the requests. The request budget for this shape
        lives in the processor suite
        (``test_generic_peer_attribute_resolves_and_stays_bounded``), which can count
        round-trips; this path runs ``ansible-inventory`` as a subprocess and cannot.
        """
        hosts, _groups, hostvars = self._run_cli(infrahub_port, "nested.yml")
        assert hosts == ALL_HOSTS

        # Straight off the concrete kind, reached through the generic relationship.
        assert hostvars["host-a"]["site"]["name"] == "paris"
        assert hostvars["host-c"]["site"]["name"] == "denver"
        # And a depth-2 path whose first hop is that same generic relationship.
        assert hostvars["host-a"]["site"]["region"]["name"] == "emea"
        assert hostvars["host-c"]["site"]["region"]["name"] == "amer"

    def test_parse_api_nested_compose(self, infrahub_port, dataset):
        # parse() drives the real fetch (depth-2 site.region.name) and composes vars.
        env = {"INFRAHUB_ADDRESS": f"http://localhost:{infrahub_port}", "INFRAHUB_API_TOKEN": ADMIN_TOKEN}
        plugin = inventory_loader.get("opsmill.infrahub.inventory")
        assert plugin is not None, "inventory plugin opsmill.infrahub.inventory not found"
        with mock.patch.dict(os.environ, env):
            plugin.parse(InventoryData(), DataLoader(), str(CONFIGS / "nested.yml"))

        host_a = plugin.inventory.get_host("host-a")
        assert host_a is not None
        host_vars = host_a.get_vars()
        assert host_vars["location"] == "paris"
        assert host_vars["region"] == "emea"
