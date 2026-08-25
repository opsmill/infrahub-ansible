# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Integration tests for the node / branch / schema modules against a live Infrahub.

Each playbook self-asserts the module's behaviour (changed / idempotency) via
ansible.builtin.assert; the test runs it with `ansible-playbook` and additionally
cross-checks the resulting state through the SDK. Node writes are isolated on a
per-class Infrahub branch (created via the SDK); the branch is removed only if a
test failed (left in place for debugging otherwise).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("infrahub_testcontainers")

from infrahub_sdk.testing.docker import TestInfrahubDockerClient
from infrahub_testcontainers.container import PROJECT_ENV_VARIABLES

from .schema import THING, load_schema

pytestmark = pytest.mark.integration

ADMIN_TOKEN = PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]
PLAYBOOKS = Path(__file__).parent / "playbooks"
TEST_BRANCH = "ansible-modules-it"


class TestModulesIntegration(TestInfrahubDockerClient):
    @pytest.fixture(scope="class")
    def node_branch(self, client_sync, schema_loader) -> str:
        """A dedicated branch with the TestingThing schema for the node tests."""
        client_sync.branch.create(branch_name=TEST_BRANCH, wait_until_completion=True)
        load_schema(client_sync, branch=TEST_BRANCH, loader=schema_loader)
        return TEST_BRANCH

    # Note: no cleanup_on_failure fixture (unlike demo-dc) — testcontainers tears
    # down the whole Infrahub instance after the class, so branch cleanup is moot.

    def _run_playbook(self, infrahub_port, playbook, extra_vars, *, check=False) -> subprocess.CompletedProcess:
        binary = shutil.which("ansible-playbook")
        if not binary:
            pytest.skip("ansible-playbook not on PATH")
        cmd = [binary, str(PLAYBOOKS / playbook)]
        for key, value in extra_vars.items():
            cmd += ["-e", f"{key}={value}"]
        if check:
            cmd.append("--check")
        env = os.environ.copy()
        env["INFRAHUB_ADDRESS"] = f"http://localhost:{infrahub_port}"
        env["INFRAHUB_API_TOKEN"] = ADMIN_TOKEN
        env["ANSIBLE_HOST_KEY_CHECKING"] = "False"
        return subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)

    def test_node_lifecycle(self, infrahub_port, client_sync, node_branch):
        result = self._run_playbook(infrahub_port, "node_lifecycle.yml", {"infrahub_branch": node_branch})
        assert result.returncode == 0, f"playbook failed:\n{result.stdout}\n{result.stderr}"
        # Playbook ends by deleting the thing — confirm it is gone on the branch.
        remaining = client_sync.filters(kind=THING, name__value="widget-1", branch=node_branch)
        assert remaining == []

    def test_node_check_mode_does_not_write(self, infrahub_port, client_sync, node_branch):
        result = self._run_playbook(infrahub_port, "node_create.yml", {"infrahub_branch": node_branch}, check=True)
        assert result.returncode == 0, f"playbook failed:\n{result.stdout}\n{result.stderr}"
        # --check must not have created the node.
        created = client_sync.filters(kind=THING, name__value="check-widget", branch=node_branch)
        assert created == []

    def test_branch_module_lifecycle(self, infrahub_port, client_sync):
        mod_branch = "ansible-module-managed-branch"
        result = self._run_playbook(infrahub_port, "branch_lifecycle.yml", {"mod_branch_name": mod_branch})
        assert result.returncode == 0, f"playbook failed:\n{result.stdout}\n{result.stderr}"
        # Playbook ends by deleting the branch — confirm it is gone.
        assert mod_branch not in client_sync.branch.all()

    def test_schema_module_check_and_load(self, infrahub_port, node_branch):
        result = self._run_playbook(infrahub_port, "schema_load.yml", {"infrahub_branch": node_branch})
        assert result.returncode == 0, f"playbook failed:\n{result.stdout}\n{result.stderr}"
