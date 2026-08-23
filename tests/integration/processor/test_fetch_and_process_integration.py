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

import math
import re

import pytest

# Skip cleanly when the testcontainers stack isn't installed (e.g. default dev env).
pytest.importorskip("infrahub_testcontainers")

from ansible_collections.opsmill.infrahub.plugins.module_utils.metrics import RequestCounter
from infrahub_sdk import InfrahubClientSync
from infrahub_sdk.testing.docker import TestInfrahubDockerClient

from conftest import count_graphql, processor_for

pytestmark = pytest.mark.integration


def _page_budget(client: InfrahubClientSync, node_count: int) -> int:
    """The most requests one kind may cost: a count query plus one per page.

    Derived rather than hardcoded because these tests share a class-scoped
    container and each adds nodes, so a fixed "one page" ceiling would silently
    become wrong once the tags outgrow a page rather than catching a regression.
    """
    pages = max(1, math.ceil(node_count / client.pagination_size))
    return 1 + pages


class _CapturingDisplay:
    """The parts of Ansible's Display that ``_handle_display`` actually calls."""

    def __init__(self) -> None:
        self.verbose: list[str] = []
        self.very_verbose: list[str] = []

    def debug(self, msg: str) -> None:
        pass

    def v(self, msg: str) -> None:
        self.verbose.append(msg)

    def vvv(self, msg: str) -> None:
        self.very_verbose.append(msg)

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass


class TestFetchAndProcessIntegration(TestInfrahubDockerClient):
    @pytest.fixture(scope="class")
    def seeded_tags(self, client_sync: InfrahubClientSync) -> list[str]:
        """Create a couple of BuiltinTag nodes (part of Infrahub's default schema)."""
        names = ["blue", "green"]
        for name in names:
            client_sync.create(kind="BuiltinTag", name=name, description=f"{name} tag").save()
        return names

    def test_resolves_simple_attributes(self, client_sync: InfrahubClientSync, seeded_tags: list[str]) -> None:
        processor = processor_for(client_sync)

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
        processor = processor_for(client_sync)

        with count_graphql(client_sync) as trackers:
            result = processor.fetch_and_process(nodes={"BuiltinTag": {"include": ["name", "description"]}})

        assert result
        assert sum(trackers.values()) <= _page_budget(client_sync, len(result)), (
            f"got {sum(trackers.values())} requests for {len(result)} tags: {dict(trackers)}"
        )

    def test_empty_description_does_not_cost_a_refetch(self, client_sync: InfrahubClientSync) -> None:
        """A null attribute is an answer, not a cache miss.

        ``description`` is optional, so these tags come back with it unset. Asking
        again returns the same null, so nothing here justifies a second request.
        """
        for name in ("no-desc-1", "no-desc-2", "no-desc-3"):
            client_sync.create(kind="BuiltinTag", name=name).save()
        processor = processor_for(client_sync)

        with count_graphql(client_sync) as trackers:
            result = processor.fetch_and_process(nodes={"BuiltinTag": {"include": ["name", "description"]}})

        assert result
        blank = [attrs for attrs in result.values() if not attrs.get("description")]
        assert blank, "expected at least one tag with an empty description"
        assert sum(trackers.values()) <= _page_budget(client_sync, len(result)), (
            f"empty attributes triggered {sum(trackers.values())} requests for {len(result)} tags: {dict(trackers)}"
        )

    def test_unknown_kind_is_skipped_not_fatal(self, client_sync: InfrahubClientSync, seeded_tags: list[str]) -> None:
        """One bad kind must not take the rest of the inventory with it.

        A typo in ``nodes:``, or a kind that exists on another branch, reaches the
        schema lookup as a miss. A regression once made that abort the whole run.

        Note this processor is built through ``__new__``, so the wrapper's exception
        decorator is *not* installed -- which is the point. The skip has to come from
        the lookup itself asking not to raise, rather than from the decorator
        happening to convert the error, or it only works for callers built one way.
        """
        processor = processor_for(client_sync)

        result = processor.fetch_and_process(nodes={"NoSuchKindHere": {}, "BuiltinTag": {"include": ["name"]}})

        assert result, "the valid kind should still resolve"
        resolved_names = {attrs.get("name") for attrs in result.values()}
        for name in seeded_tags:
            assert name in resolved_names

    def test_reported_request_count_matches_the_counter_and_covers_graphql(
        self, client_sync: InfrahubClientSync
    ) -> None:
        """FR-020 / SC-009: the run states its own cost, and the number is true.

        Two things are checked, because either alone would pass while lying:

        * The number printed equals what the SDK-level recorder saw. A report that
          drifts from the counter is worse than no report.
        * It is at least the GraphQL round-trip count. It is deliberately *not*
          asserted equal: schema lookups go over REST, so they are counted by the
          recorder and invisible to ``count_graphql``. Asserting equality here would
          encode a wrong idea of what the number means and would break the first time
          a schema fetch moved.
        """
        for name in ("cost-1", "cost-2"):
            client_sync.create(kind="BuiltinTag", name=name).save()

        counter = RequestCounter()
        original_recorder = client_sync.config.custom_recorder
        client_sync.config.custom_recorder = counter
        processor = processor_for(client_sync)
        processor.client.request_counter = counter
        processor.display = _CapturingDisplay()

        try:
            counter.reset()
            with count_graphql(client_sync) as trackers:
                result = processor.fetch_and_process(nodes={"BuiltinTag": {"include": ["name"]}})
        finally:
            # The client is class-scoped and shared with the tests above.
            client_sync.config.custom_recorder = original_recorder

        assert result
        cost_lines = [line for line in processor.display.verbose if "Inventory fetch cost" in line]
        assert len(cost_lines) == 1, processor.display.verbose

        match = re.search(r"(\d+) request\(s\)", cost_lines[0])
        assert match, f"no request count in the reported line: {cost_lines[0]!r}"
        reported = int(match.group(1))
        graphql_calls = sum(trackers.values())

        assert reported == counter.responses, f"reported {reported}, recorder saw {counter.responses}"
        # -vvv carries the per-kind detail behind that total.
        breakdown = "\n".join(processor.display.very_verbose)
        assert "Inventory fetch cost, by kind:" in breakdown, processor.display.very_verbose
        assert "host kind BuiltinTag:" in breakdown, breakdown

        assert reported >= graphql_calls, (
            f"reported {reported} requests but {graphql_calls} GraphQL round-trips were made; "
            "the recorder sits below GraphQL and must see at least as many"
        )
