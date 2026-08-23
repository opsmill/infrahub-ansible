"""Unit tests for ``InfrahubNodesProcessor.fetch_and_process`` resolution.

Focus: the number of times each host node is resolved, and how peers are loaded.
These are the multipliers that drive how many GraphQL round-trips the inventory
plugin makes, so we pin them with mock-based unit tests.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import NamedTuple

import pytest
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
    # `self.client` IS this wrapper, so the processor's `self.client.client.store`
    # resolves to `wrapper.client.store` -- the mock stubbed here.
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


def test_all_kinds_failing_raises_instead_of_returning_empty(mocker):
    """An empty result caused by a failure must not look like an empty inventory.

    Returning ``None`` here is indistinguishable from "the query matched nothing",
    so a transient API error would hand Ansible zero hosts and the play would
    quietly no-op -- which reads as success.
    """
    processor, wrapper = _make_processor(mocker, {})
    wrapper.fetch_nodes.side_effect = RuntimeError("infrahub unreachable")

    with pytest.raises(RuntimeError, match="No nodes could be fetched"):
        processor.fetch_and_process(nodes={"KindA": {}})


def test_failure_detail_names_every_broken_kind(mocker):
    processor, wrapper = _make_processor(mocker, {})
    wrapper.fetch_nodes.side_effect = RuntimeError("boom")

    with pytest.raises(RuntimeError) as excinfo:
        processor.fetch_and_process(nodes={"KindA": {}, "KindB": {}})

    assert "KindA: boom" in str(excinfo.value)
    assert "KindB: boom" in str(excinfo.value)


def test_genuinely_empty_result_still_returns_none(mocker):
    """No failures, no nodes: the kinds answered and the answer was empty."""
    processor, _wrapper = _make_processor(mocker, {})

    assert processor.fetch_and_process(nodes={"KindA": {}}) is None


def test_a_partial_failure_still_returns_what_worked(mocker):
    """One broken kind must not discard the kinds that answered."""
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1")]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind)

    def fetch(kind, **kwargs):
        if kind == "KindB":
            raise RuntimeError("boom")
        return list(nodes_by_kind.get(kind, []))

    wrapper.fetch_nodes.side_effect = fetch
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "a1"})

    result = processor.fetch_and_process(nodes={"KindA": {}, "KindB": {}})

    assert result == {"a1": {"id": "a1"}}


def test_bare_relationship_needs_no_peer_load(mocker):
    """A relationship requested without a dotted path resolves to an id, so no peer is loaded."""
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1", peer=FakePeer("site-1", "LocationSite"))]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind, attrs=["name", "site"])
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}})

    assert [c for c in wrapper.fetch_nodes.call_args_list if c.kwargs.get("kind") == "LocationSite"] == []


def test_a_kind_with_no_schema_does_not_take_the_others_with_it(mocker):
    """An unknown kind must not abort the kinds that do resolve.

    A missing schema reaches the projection step as ``schema=None``; reading
    ``attribute_names`` off it used to abort the whole inventory over one typo.
    """
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1")]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind)
    wrapper.fetch_single_schema.side_effect = lambda kind, **kw: (
        None if kind == "NoSuchKind" else SimpleNamespace(kind=kind, attribute_names=["name"], relationship_names=[])
    )
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "a1"})

    result = processor.fetch_and_process(nodes={"NoSuchKind": {}, "KindA": {}})

    assert result == {"a1": {"id": "a1"}}


def test_a_kind_with_no_schema_alone_raises(mocker):
    """With nothing else to fall back on, a bad kind is an error, not an empty inventory.

    Silently returning nothing here is how a typo in ``nodes:`` becomes a play that
    runs against zero hosts and reports success.
    """
    wrapper = mocker.MagicMock()
    wrapper.fetch_single_schema.side_effect = lambda kind, **kw: None
    wrapper.fetch_nodes.side_effect = lambda kind, **kw: None
    wrapper.client.store.get.return_value = None
    wrapper.client.pagination_size = 50

    processor = iu.InfrahubNodesProcessor(client=wrapper)

    with pytest.raises(RuntimeError, match="no schema found"):
        processor.fetch_and_process(nodes={"NoSuchKind": {}})


def test_a_swallowed_fetch_is_a_failure_not_an_empty_result(mocker):
    """The wrapper returns ``None`` instead of raising, and that still has to fail loudly.

    ``InfrahubclientWrapper`` decorates its own methods with
    ``handle_infrahub_exceptions_decorator``, which -- whenever a Display is attached,
    as it always is in the inventory -- logs the error and returns ``None`` rather than
    raising. So the ``except`` around ``fetch_nodes`` never fires in the path that
    matters, and treating ``None`` as "this kind matched nothing" hands Ansible zero
    hosts and reports success.
    """
    processor, wrapper = _make_processor(mocker, {})
    wrapper.fetch_nodes.side_effect = lambda kind, **kw: None

    with pytest.raises(RuntimeError, match="No nodes could be fetched"):
        processor.fetch_and_process(nodes={"KindA": {}})


def test_a_generic_kind_resolves_the_concrete_kinds_it_answers_with(mocker):
    """Requesting a generic must not die on the concrete kinds that come back.

    A query for a generic answers with nodes carrying their *concrete* ``__typename``,
    and resolution looks the attribute list up by the node's own kind. Keying that list
    by the requested kind alone made a perfectly valid ``nodes: {SomeGeneric: {}}``
    abort the whole inventory with a KeyError.
    """
    nodes_by_kind = {"TestingLocation": [FakeNode("TestingSite", "s1"), FakeNode("TestingRegion", "r1")]}
    processor, _wrapper = _make_processor(mocker, nodes_by_kind)
    mocker.patch.object(processor, "resolve_node_mapping", side_effect=lambda node, **kw: {"id": node.id})

    result = processor.fetch_and_process(nodes={"TestingLocation": {}})

    assert result == {"s1": {"id": "s1"}, "r1": {"id": "r1"}}
