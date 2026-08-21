"""Unit tests for ``InfrahubNodesProcessor.fetch_and_process`` resolution.

Focus: the number of times each host node is resolved, and how peers are loaded.
These are the multipliers that drive how many GraphQL round-trips the inventory
plugin makes, so we pin them with mock-based unit tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import NamedTuple

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu


class FakePeer(NamedTuple):
    """Stand-in for a ``RelatedNodeSync`` pointing at a peer of a concrete kind."""

    id: str
    typename: str


class FakeNode:
    """Minimal stand-in for an ``InfrahubNodeSync`` for resolution-count tests."""

    def __init__(self, kind: str, node_id: str, peer: FakePeer | None = None) -> None:
        self._schema = SimpleNamespace(kind=kind, attribute_names=["name"], relationship_names=["site"])
        self.id = node_id
        self.hfid = None
        if peer is not None:
            self.site = peer

    def __str__(self) -> str:
        return self.id


def _make_processor(mocker, nodes_by_kind, attrs=None):
    """Build a processor whose client wrapper returns the given fake nodes."""
    wrapper = mocker.MagicMock()
    wrapper.fetch_single_schema.side_effect = lambda kind, **kw: SimpleNamespace(
        kind=kind, attribute_names=["name"], relationship_names=["site"]
    )
    wrapper.fetch_nodes.side_effect = lambda kind, **kw: list(nodes_by_kind.get(kind, []))
    # Nothing is in the store, so every referenced peer counts as needing a load.
    wrapper.client.store.get.return_value = None
    wrapper.client.pagination_size = 50

    processor = iu.InfrahubNodesProcessor(client=wrapper)
    mocker.patch.object(processor, "get_attributes_for_schema", return_value=attrs or ["name"])
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
    resolve = mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}, "KindB": {}})

    # 4 unique host nodes, 2 requested kinds. The pre-S1 code resolved 4 x 2 = 8 times.
    assert resolve.call_count == 4


def test_peers_are_loaded_by_id_not_by_kind(mocker):
    """Peers are fetched by the ids the host nodes reference, never a whole kind.

    The previous strategy fetched every peer *kind* in full, so the cost tracked the
    size of the database rather than the size of the inventory.
    """
    shared = FakePeer("site-1", "LocationSite")
    nodes_by_kind = {
        "KindA": [FakeNode("KindA", "a1", peer=shared)],
        "KindB": [FakeNode("KindB", "b1", peer=shared)],
    }
    processor, wrapper = _make_processor(mocker, nodes_by_kind, attrs=["name", "site.name"])
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}, "KindB": {}})

    peer_calls = [c for c in wrapper.fetch_nodes.call_args_list if c.kwargs.get("kind") == "LocationSite"]
    # One call, carrying the referenced ids as a filter...
    assert len(peer_calls) == 1
    assert peer_calls[0].kwargs["filters"] == {"ids": ["site-1"]}
    # ...deduped across the two host kinds that reference the same peer.
    assert peer_calls[0].kwargs["parallel"] is False

    # No unfiltered fetch of the peer kind: that is the unbounded pass this replaced.
    unbounded = [
        c
        for c in wrapper.fetch_nodes.call_args_list
        if c.kwargs.get("kind") == "LocationSite" and not c.kwargs.get("filters")
    ]
    assert unbounded == []


def test_bare_relationship_needs_no_peer_load(mocker):
    """A relationship requested without a dotted path resolves to an id, so no peer is loaded."""
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1", peer=FakePeer("site-1", "LocationSite"))]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind, attrs=["name", "site"])
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}})

    assert [c for c in wrapper.fetch_nodes.call_args_list if c.kwargs.get("kind") == "LocationSite"] == []
