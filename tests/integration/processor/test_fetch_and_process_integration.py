"""Integration tests for the inventory processor against a live Infrahub.

These run a real Infrahub via testcontainers (the SDK's ``TestInfrahubDocker``
helper) so we exercise the genuine GraphQL/query behaviour of
``InfrahubNodesProcessor.fetch_and_process`` — correctness today, and a real
round-trip count for the strategy A/B work (S2-S4) as it lands.

Requirements to run:
  * Docker available locally.
  * ``uv sync --group integration`` (installs ``infrahub-testcontainers``; kept
    in its own dependency group because its ``prefect-client`` dependency pins
    ``cachetools<7`` which conflicts with the dev group's ``tox``).
  * ``INFRAHUB_TESTING_IMAGE_VER`` set to the Infrahub image version to test.

Run with:  ``uv run --group integration pytest tests/integration/processor -m integration``
"""

from __future__ import annotations

import pytest

# Skip cleanly when the testcontainers stack isn't installed (e.g. default dev env).
pytest.importorskip("infrahub_testcontainers")

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu
from infrahub_sdk import InfrahubClientSync
from infrahub_sdk.testing.docker import TestInfrahubDockerClient

pytestmark = pytest.mark.integration


def _processor_for(client_sync: InfrahubClientSync) -> iu.InfrahubNodesProcessor:
    """Wrap a live client in the collection's processor without re-authenticating."""
    wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
    wrapper.client = client_sync
    return iu.InfrahubNodesProcessor(client=wrapper)


class TestFetchAndProcessIntegration(TestInfrahubDockerClient):
    @pytest.fixture(scope="class")
    def seeded_tags(self, client_sync: InfrahubClientSync) -> list[str]:
        """Create a couple of BuiltinTag nodes (part of Infrahub's default schema)."""
        names = ["blue", "green"]
        for name in names:
            client_sync.create(kind="BuiltinTag", name=name, description=f"{name} tag").save()
        return names

    def test_resolves_simple_attributes(self, client_sync: InfrahubClientSync, seeded_tags: list[str]) -> None:
        processor = _processor_for(client_sync)

        result = processor.fetch_and_process(nodes={"BuiltinTag": {"include": ["name", "description"]}})

        assert result is not None
        resolved_names = {attrs.get("name") for attrs in result.values()}
        for name in seeded_tags:
            assert name in resolved_names
