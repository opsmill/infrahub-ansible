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

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections import Counter

pytest.importorskip("infrahub_testcontainers")

from infrahub_sdk import Config, InfrahubClientSync
from infrahub_sdk.testing.docker import TestInfrahubDockerClient
from infrahub_sdk.testing.schemas.animal import (
    TESTING_CAT,
    TESTING_PERSON,
    SchemaAnimal,
)

from conftest import count_graphql, processor_for

# `measurement` marks the heavy schema-load + seed benchmark, so a nightly run can
# select the lighter suite alone with `-m "integration and not measurement"`. Note
# neither suite runs on a pull request: `integration-testcontainers` in
# workflow-ansible-linter-and-tests.yml is gated on `schedule`/`workflow_dispatch`,
# so a regression these catch shows up on the nightly build, not in PR checks.
pytestmark = [pytest.mark.integration, pytest.mark.measurement]


# The budgets below are measured, not derived. They depend on SDK behaviour the
# inventory code does not control -- pagination_size-driven chunking, whether a
# count query is issued, cold-client schema fetches -- so an infrahub-sdk or
# Infrahub upgrade can legitimately shift them by one with no change here.
#
# Measured against: infrahub-sdk 1.20.0, infrahub-testcontainers image 1.9.9.
#
# If one of these fails after a dependency bump and nothing in plugins/ changed,
# re-measure with `-s` (each test prints its own total) and move the number,
# noting the versions. A rise with plugins/ changes is a regression.
def _over_budget(actual: int, budget: int) -> str:
    return (
        f"{actual} GraphQL round-trips, budget {budget}. These budgets are measured, not\n"
        f"aspirational: a rise means a fetch went back to costing one request per node or\n"
        f"per peer. Re-measure before widening one."
    )


def _report(label: str, trackers: Counter[str]) -> None:
    total = sum(trackers.values())
    print(f"\n=== MEASURE [{label}] total_round_trips={total} ===")
    for tracker, n in sorted(trackers.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"    {n:>3}  {tracker}")


class TestFetchRoundTripMeasurement(TestInfrahubDockerClient, SchemaAnimal):
    N_PEOPLE = 3
    CATS_PER_PERSON = 2

    @pytest.fixture(scope="class")
    def seeded(self, client_sync, schema_base, schema_loader) -> dict:
        """Load the animal schema and seed people (with tags) owning cats."""
        resp = schema_loader([schema_base.to_schema_dict()])
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
        processor = processor_for(client)
        with count_graphql(client) as trackers:
            result = processor.fetch_and_process(nodes=nodes)
        _report(label, trackers)
        return result, sum(trackers.values())

    def test_depth1_many_animals(self, infrahub_port, seeded):
        result, count = self._measure(
            infrahub_port, "S3 depth1 animals.name", {TESTING_PERSON: {"include": ["name", "animals.name"]}}
        )
        assert result and len(result) == seeded["people"]
        assert count <= 2, _over_budget(count, 2)
        sample = next(iter(result.values()))
        print(f"    sample person resolved: {sample}")
        # Content must actually be resolved, not just fast-and-empty.
        animals = sample.get("animals")
        assert animals and len(animals) == self.CATS_PER_PERSON
        assert all(a.get("name") for a in animals)

    def test_depth1_many_tags(self, infrahub_port, seeded):
        result, count = self._measure(
            infrahub_port, "S3 depth1 tags.name", {TESTING_PERSON: {"include": ["name", "tags.name"]}}
        )
        assert result and len(result) == seeded["people"]
        assert count <= 2, _over_budget(count, 2)
        sample = next(iter(result.values()))
        tags = sample.get("tags")
        assert tags and len(tags) == seeded["tags"]
        assert all(t.get("name") for t in tags)

    def test_depth2_nested(self, infrahub_port, seeded):
        result, count = self._measure(
            infrahub_port, "S2 depth2 animals.owner.name", {TESTING_PERSON: {"include": ["name", "animals.owner.name"]}}
        )
        assert result and len(result) == seeded["people"]
        assert count <= 3, _over_budget(count, 3)
        sample = next(iter(result.values()))
        print(f"    sample person (depth2) resolved: {sample}")
        animals = sample.get("animals")
        assert animals and len(animals) == self.CATS_PER_PERSON
        # depth-2: each animal carries its owner's name.
        assert all(a.get("owner", {}).get("name") for a in animals)

    def test_combined(self, infrahub_port, seeded):
        result, count = self._measure(
            infrahub_port,
            "combined animals.name+tags.name+animals.owner.name",
            {TESTING_PERSON: {"include": ["name", "animals.name", "tags.name", "animals.owner.name"]}},
        )
        assert result and len(result) == seeded["people"]
        assert count <= 3, _over_budget(count, 3)

        # The most representative shape is the one most worth guarding against a
        # fast-and-empty regression: assert every part of it actually resolved.
        sample = next(iter(result.values()))
        animals = sample.get("animals")
        tags = sample.get("tags")
        assert animals and len(animals) == self.CATS_PER_PERSON
        assert all(a.get("name") for a in animals)
        assert all(a.get("owner", {}).get("name") for a in animals)
        assert tags and len(tags) == seeded["tags"]
        assert all(t.get("name") for t in tags)

    def test_generic_peer_attribute_resolves_and_stays_bounded(self, infrahub_port, seeded):
        """A nested attribute the *declared* peer schema does not expose.

        ``Person.animals`` declares its peer as the ``TestingAnimal`` generic, which
        carries only ``name`` and ``weight``. ``breed`` lives on the concrete
        ``TestingCat``. The SDK builds a relationship's inline payload from the
        declared peer schema, so ``breed`` is never requested and the peers arrive
        without it -- and no amount of retrying the host query changes that.

        This is the single most common shape in real schemas (a device's
        ``location`` declaring a location generic, an address's ``interface``
        declaring an interface generic) and every performance defect found in this
        area has been some version of it. It has to resolve, and it has to do so
        without falling back to one request per peer.
        """
        result, count = self._measure(
            infrahub_port,
            "generic peer animals.breed",
            {TESTING_PERSON: {"include": ["name", "animals.breed"]}},
        )
        assert result and len(result) == seeded["people"]

        sample = next(iter(result.values()))
        animals = sample.get("animals")
        assert animals and len(animals) == self.CATS_PER_PERSON
        # The point of the test: an attribute absent from the generic still arrives.
        assert all(a.get("breed") == "Bengal" for a in animals), (
            f"breed did not resolve through the generic peer: {animals}"
        )
        # ...and it cost a bounded number of requests, not one per peer.
        assert count <= 3, _over_budget(count, 3)

    def test_inherited_attr_cats(self, infrahub_port, seeded):
        # `name` is inherited from the Animal generic -> exercises _resolve_schema_attribute.
        result, count = self._measure(
            infrahub_port, "S4 inherited cat.name+breed", {TESTING_CAT: {"include": ["name", "breed"]}}
        )
        assert result and len(result) == seeded["cats"]
        assert count <= 2, _over_budget(count, 2)
        # Show whether inherited `name` actually resolved (S4: does the refetch even fire?).
        sample = next(iter(result.values()))
        print(f"    sample cat resolved: {sample}")
