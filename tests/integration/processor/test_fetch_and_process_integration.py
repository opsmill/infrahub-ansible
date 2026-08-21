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

import contextlib
from collections import Counter

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


@contextlib.contextmanager
def count_graphql(client: InfrahubClientSync):
    """Count GraphQL round-trips made inside the block.

    The heavy per-shape budgets live in ``test_fetch_roundtrip_measurement.py``,
    which is ``measurement``-marked and therefore only runs on scheduled builds.
    This lighter counter rides the PR gate so a gross regression -- a fetch that
    goes back to one request per node -- cannot land unnoticed.
    """
    trackers: Counter[str] = Counter()
    original = client.execute_graphql

    def wrapper(*args, **kwargs):
        trackers[kwargs.get("tracker") or "untracked"] += 1
        return original(*args, **kwargs)

    client.execute_graphql = wrapper
    try:
        yield trackers
    finally:
        client.execute_graphql = original


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

    def test_simple_attributes_cost_one_count_and_one_page(
        self, client_sync: InfrahubClientSync, seeded_tags: list[str]
    ) -> None:
        """One kind, plain attributes, no relationships: a count and a page, nothing per node.

        This is the floor the whole fetch path is built on. The defect it guards
        against is real and has shipped before: resolving an attribute that comes
        back empty used to refetch the whole node, one request per node, so the
        count tracked the inventory size instead of the page count.
        """
        processor = _processor_for(client_sync)

        with count_graphql(client_sync) as trackers:
            result = processor.fetch_and_process(nodes={"BuiltinTag": {"include": ["name", "description"]}})

        assert result
        total = sum(trackers.values())
        assert total <= 2, f"expected a count plus one page, got {total}: {dict(trackers)}"

    def test_empty_description_does_not_cost_a_refetch(self, client_sync: InfrahubClientSync) -> None:
        """A null attribute is an answer, not a cache miss.

        ``description`` is optional, so these tags come back with it unset. Asking
        again returns the same null, so nothing here justifies a second request.
        """
        for name in ("no-desc-1", "no-desc-2", "no-desc-3"):
            client_sync.create(kind="BuiltinTag", name=name).save()
        processor = _processor_for(client_sync)

        with count_graphql(client_sync) as trackers:
            result = processor.fetch_and_process(nodes={"BuiltinTag": {"include": ["name", "description"]}})

        assert result
        blank = [attrs for attrs in result.values() if not attrs.get("description")]
        assert blank, "expected at least one tag with an empty description"
        total = sum(trackers.values())
        assert total <= 2, f"empty attributes triggered {total} requests: {dict(trackers)}"

    def test_unknown_kind_is_skipped_not_fatal(self, client_sync: InfrahubClientSync, seeded_tags: list[str]) -> None:
        """One bad kind must not take the rest of the inventory with it.

        A typo in ``nodes:``, or a kind that exists on another branch, reaches the
        schema lookup as a miss. A regression once made that abort the whole run.

        Note this processor is built through ``__new__``, so the wrapper's exception
        decorator is *not* installed -- which is the point. The skip has to come from
        the lookup itself asking not to raise, rather than from the decorator
        happening to convert the error, or it only works for callers built one way.
        """
        processor = _processor_for(client_sync)

        result = processor.fetch_and_process(nodes={"NoSuchKindHere": {}, "BuiltinTag": {"include": ["name"]}})

        assert result, "the valid kind should still resolve"
        resolved_names = {attrs.get("name") for attrs in result.values()}
        for name in seeded_tags:
            assert name in resolved_names
