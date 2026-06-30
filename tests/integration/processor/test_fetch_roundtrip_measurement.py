"""Round-trip measurement of the inventory processor against a live Infrahub.

Counts the GraphQL round-trips ``fetch_and_process`` makes for representative
inventory shapes (depth-1 many-relationships, depth-2 nesting, inherited
attributes). This is the A/B yardstick used to qualify the fetch-reduction
strategies (S2 prefetch, S3 batch peers, S4 inherited-attr handling): run on the
current resolver to get a baseline, implement a strategy, then re-run and diff.

Run:
  uv run --no-default-groups --group integration pytest \
    tests/integration/processor/test_fetch_roundtrip_measurement.py \
    -m integration -p no:pytest-infrahub-performance-test -s -v
"""

from __future__ import annotations

import contextlib
from collections import Counter

import pytest

pytest.importorskip("infrahub_testcontainers")

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu
from infrahub_sdk import Config, InfrahubClientSync
from infrahub_sdk.testing.docker import TestInfrahubDockerClient
from infrahub_sdk.testing.schemas.animal import (
    TESTING_CAT,
    TESTING_PERSON,
    SchemaAnimal,
)

# `measurement` marks the heavy schema-load + seed benchmark: it gates only the
# scheduled/dispatch runs, not every PR (the convergence step is too slow for a
# standard GitHub runner). The lighter correctness test carries the PR gate.
pytestmark = [pytest.mark.integration, pytest.mark.measurement]


def _processor_for(client_sync: InfrahubClientSync) -> iu.InfrahubNodesProcessor:
    wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
    wrapper.client = client_sync
    return iu.InfrahubNodesProcessor(client=wrapper)


@contextlib.contextmanager
def count_graphql(client: InfrahubClientSync):
    """Count GraphQL round-trips by query tracker while inside the block."""
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


def _report(label: str, trackers: Counter[str]) -> None:
    total = sum(trackers.values())
    print(f"\n=== MEASURE [{label}] total_round_trips={total} ===")
    for tracker, n in sorted(trackers.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"    {n:>3}  {tracker}")


class TestFetchRoundTripMeasurement(TestInfrahubDockerClient, SchemaAnimal):
    N_PEOPLE = 3
    CATS_PER_PERSON = 2

    @pytest.fixture(scope="class")
    def seeded(self, client_sync, schema_base) -> dict:
        """Load the animal schema and seed people (with tags) owning cats."""
        resp = client_sync.schema.load(schemas=[schema_base.to_schema_dict()], wait_until_converged=True)
        assert not resp.errors, resp.errors

        tags = []
        for name in ("red", "blue"):
            tag = client_sync.create(kind="BuiltinTag", name=name)
            tag.save()
            tags.append(tag)

        for i in range(self.N_PEOPLE):
            person = client_sync.create(kind=TESTING_PERSON, name=f"Person{i}", height=170 + i, tags=tags)
            person.save()
            for j in range(self.CATS_PER_PERSON):
                cat = client_sync.create(
                    kind=TESTING_CAT, name=f"Cat{i}-{j}", breed="Bengal", color="#101010", owner=person
                )
                cat.save()

        return {"people": self.N_PEOPLE, "cats": self.N_PEOPLE * self.CATS_PER_PERSON, "tags": len(tags)}

    def _measure(self, infrahub_port, label, nodes):
        # Fresh client per measurement => cold store, so each scenario is measured
        # in isolation (the client store otherwise persists peers across tests).
        client = InfrahubClientSync(
            config=Config(username="admin", password="infrahub", address=f"http://localhost:{infrahub_port}")
        )
        processor = _processor_for(client)
        with count_graphql(client) as trackers:
            result = processor.fetch_and_process(nodes=nodes)
        _report(label, trackers)
        return result, sum(trackers.values())

    def test_depth1_many_animals(self, infrahub_port, seeded):
        result, _count = self._measure(
            infrahub_port, "S3 depth1 animals.name", {TESTING_PERSON: {"include": ["name", "animals.name"]}}
        )
        assert result and len(result) == seeded["people"]
        sample = next(iter(result.values()))
        print(f"    sample person resolved: {sample}")
        # Content must actually be resolved, not just fast-and-empty.
        animals = sample.get("animals")
        assert animals and len(animals) == self.CATS_PER_PERSON
        assert all(a.get("name") for a in animals)

    def test_depth1_many_tags(self, infrahub_port, seeded):
        result, _count = self._measure(
            infrahub_port, "S3 depth1 tags.name", {TESTING_PERSON: {"include": ["name", "tags.name"]}}
        )
        assert result and len(result) == seeded["people"]
        sample = next(iter(result.values()))
        tags = sample.get("tags")
        assert tags and len(tags) == seeded["tags"]
        assert all(t.get("name") for t in tags)

    def test_depth2_nested(self, infrahub_port, seeded):
        result, _count = self._measure(
            infrahub_port, "S2 depth2 animals.owner.name", {TESTING_PERSON: {"include": ["name", "animals.owner.name"]}}
        )
        assert result and len(result) == seeded["people"]
        sample = next(iter(result.values()))
        print(f"    sample person (depth2) resolved: {sample}")
        animals = sample.get("animals")
        assert animals and len(animals) == self.CATS_PER_PERSON
        # depth-2: each animal carries its owner's name.
        assert all(a.get("owner", {}).get("name") for a in animals)

    def test_combined(self, infrahub_port, seeded):
        result, _count = self._measure(
            infrahub_port,
            "combined animals.name+tags.name+animals.owner.name",
            {TESTING_PERSON: {"include": ["name", "animals.name", "tags.name", "animals.owner.name"]}},
        )
        assert result and len(result) == seeded["people"]

    def test_inherited_attr_cats(self, infrahub_port, seeded):
        # `name` is inherited from the Animal generic -> exercises _resolve_schema_attribute.
        result, _count = self._measure(
            infrahub_port, "S4 inherited cat.name+breed", {TESTING_CAT: {"include": ["name", "breed"]}}
        )
        assert result and len(result) == seeded["cats"]
        # Show whether inherited `name` actually resolved (S4: does the refetch even fire?).
        sample = next(iter(result.values()))
        print(f"    sample cat resolved: {sample}")
