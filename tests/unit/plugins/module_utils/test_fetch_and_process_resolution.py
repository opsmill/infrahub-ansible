"""Unit tests for ``InfrahubNodesProcessor.fetch_and_process`` resolution.

Focus: the number of times each host node is resolved (and each related kind
prefetched). These are the multipliers that drive how many GraphQL round-trips
the inventory plugin makes, so we pin them with mock-based unit tests.
"""

from __future__ import annotations

from types import SimpleNamespace

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu


class FakeNode:
    """Minimal stand-in for an ``InfrahubNodeSync`` for resolution-count tests."""

    def __init__(self, kind: str, node_id: str) -> None:
        self._schema = SimpleNamespace(kind=kind)
        self.id = node_id
        self.hfid = None

    def __str__(self) -> str:
        return self.id


def _make_processor(mocker, nodes_by_kind):
    """Build a processor whose client wrapper returns the given fake nodes."""
    wrapper = mocker.MagicMock()
    wrapper.fetch_single_schema.side_effect = lambda kind, **kw: SimpleNamespace(kind=kind)
    wrapper.fetch_nodes.side_effect = lambda kind, **kw: list(nodes_by_kind.get(kind, []))

    processor = iu.InfrahubNodesProcessor(client=wrapper)
    # Keep resolution and related-kind discovery out of the picture: this suite
    # is only about how many times the loops invoke them.
    mocker.patch.object(processor, "get_attributes_for_schema", return_value=["name"])
    return processor, wrapper


def test_each_host_node_resolved_once_across_kinds(mocker):
    """Every host node is resolved exactly once, regardless of how many kinds were requested.

    Before the Phase 1 / Phase 2 split, the resolve loop was nested inside the
    per-kind loop, so N nodes across K kinds were resolved N x K times.
    """
    nodes_by_kind = {
        "KindA": [FakeNode("KindA", "a1"), FakeNode("KindA", "a2")],
        "KindB": [FakeNode("KindB", "b1"), FakeNode("KindB", "b2")],
    }
    processor, _wrapper = _make_processor(mocker, nodes_by_kind)
    mocker.patch.object(processor, "get_related_nodes", return_value=[])
    resolve = mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}, "KindB": {}})

    # 4 unique host nodes, 2 requested kinds. The pre-S1 code resolved 4 x 2 = 8 times.
    assert resolve.call_count == 4


def test_related_kind_prefetched_once_when_shared(mocker):
    """A peer kind referenced by several host kinds is bulk-fetched only once."""
    nodes_by_kind = {
        "KindA": [FakeNode("KindA", "a1")],
        "KindB": [FakeNode("KindB", "b1")],
    }
    processor, wrapper = _make_processor(mocker, nodes_by_kind)
    # Both host kinds point at the same peer kind "SharedPeer".
    mocker.patch.object(processor, "get_related_nodes", return_value=["SharedPeer"])
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}, "KindB": {}})

    related_fetches = [call for call in wrapper.fetch_nodes.call_args_list if call.kwargs.get("kind") == "SharedPeer"]
    # Deduped: fetched once even though two host kinds reference it.
    assert len(related_fetches) == 1
