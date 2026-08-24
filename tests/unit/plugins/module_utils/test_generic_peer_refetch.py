"""Unit tests for the concrete-kind refetch of store-cached peers (issue #384).

A peer reached through a relationship declared against a generic is cached in
the SDK store typed by its concrete kind (from ``__typename``) but only carries
the generic's fields. A requested nested relationship then exists on the schema
yet holds no id, and the traversal silently resolved empty. The resolver must
detect that and refetch the peer by its concrete kind instead.
"""

from __future__ import annotations

from types import SimpleNamespace

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu


def _make_processor(mocker, cached_peer):
    client = mocker.MagicMock()
    client.store.get.return_value = cached_peer
    wrapper = mocker.MagicMock()
    wrapper.client = client
    return iu.InfrahubNodesProcessor(client=wrapper)


def _cached_peer(mocker, peer_id="site-1", nested_rel_id=None):
    """A store-cached peer whose ``parent`` relationship is a RelatedNodeSync with the given id."""
    nested_rel = mocker.MagicMock(spec=iu.RelatedNodeSync)
    nested_rel.id = nested_rel_id
    return SimpleNamespace(id=peer_id, parent=nested_rel)


def _one_rel(mocker, peer_id="site-1", fresh_peer=None):
    """A host node's one-cardinality relationship pointing at the cached peer."""
    node_attr = mocker.MagicMock(spec=iu.RelatedNodeSync)
    node_attr.id = peer_id
    node_attr.schema = SimpleNamespace(peer="LocationGeneric")
    node_attr.peer = fresh_peer
    return node_attr


def test_store_hit_with_uninitialized_nested_relationship_refetches_peer(mocker):
    """A cached peer missing data for a requested nested relationship is refetched."""
    cached = _cached_peer(mocker, nested_rel_id=None)
    fresh = SimpleNamespace(id="site-1")
    processor = _make_processor(mocker, cached)
    node_attr = _one_rel(mocker, fresh_peer=fresh)
    resolve = mocker.patch.object(processor, "resolve_node_mapping", return_value={"parent": {"name": "region-1"}})

    result = processor._resolve_one_relationship(node_attr, ["parent.name"], has_nested=True, schemas={})

    node_attr.fetch.assert_called_once()
    # Nested resolution ran against the refetched peer, not the incomplete cached copy.
    assert resolve.call_args.kwargs["node"] is fresh
    assert result == {"parent": {"name": "region-1"}}


def test_store_hit_with_complete_nested_relationship_uses_cache(mocker):
    """A cached peer that already has the nested relationship id is used as-is."""
    cached = _cached_peer(mocker, nested_rel_id="region-uuid")
    processor = _make_processor(mocker, cached)
    node_attr = _one_rel(mocker)
    resolve = mocker.patch.object(processor, "resolve_node_mapping", return_value={"parent": {"name": "region-1"}})

    processor._resolve_one_relationship(node_attr, ["parent.name"], has_nested=True, schemas={})

    node_attr.fetch.assert_not_called()
    assert resolve.call_args.kwargs["node"] is cached


def test_genuinely_empty_relationship_refetches_only_once(mocker):
    """A peer whose relationship is empty even after refetch is not refetched per host."""
    cached = _cached_peer(mocker, nested_rel_id=None)
    processor = _make_processor(mocker, cached)
    # The refetch returns the same shape (the relationship is genuinely empty).
    node_attr = _one_rel(mocker, fresh_peer=cached)
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"parent": {}})

    processor._resolve_one_relationship(node_attr, ["parent.name"], has_nested=True, schemas={})
    processor._resolve_one_relationship(node_attr, ["parent.name"], has_nested=True, schemas={})

    node_attr.fetch.assert_called_once()
