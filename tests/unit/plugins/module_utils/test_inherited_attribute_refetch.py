"""Unit tests for the inherited-attribute refetch in ``resolve_node_mapping``.

When a schema attribute comes back empty (e.g. inherited from a generic and not
populated in the store), the resolver refetches the full node. This must happen
at most once per node, not once per empty attribute.
"""

from __future__ import annotations

from types import SimpleNamespace

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu


class FakeAttr:
    def __init__(self, value):
        self.value = value


class FakeNode:
    """Node whose requested attributes are all empty, forcing the refetch path."""

    def __init__(self, client, kind="KindA", node_id="n1", empty_attrs=("a", "b")):
        self._client = client
        self.id = node_id
        self._schema = SimpleNamespace(
            kind=kind,
            attribute_names=list(empty_attrs),
            relationship_names=[],
        )
        # Every requested attribute is empty on the original node.
        for name in empty_attrs:
            setattr(self, name, FakeAttr(value=None))


def test_inherited_attrs_refetch_node_once(mocker):
    """Several empty attributes on one node trigger a single full-node refetch."""
    client = mocker.MagicMock()
    # The refetched node exposes populated attribute values.
    client.get.return_value = SimpleNamespace(a=FakeAttr("va"), b=FakeAttr("vb"))

    wrapper = mocker.MagicMock()
    wrapper.client = client
    processor = iu.InfrahubNodesProcessor(client=wrapper)

    node = FakeNode(client=client, empty_attrs=("a", "b"))
    result = processor.resolve_node_mapping(node=node, attrs=["a", "b"], schemas={}, include_id=False)

    # Both attributes resolved from the single refetched node...
    assert result == {"a": "va", "b": "vb"}
    # ...via exactly one refetch, not one per empty attribute (was 2).
    assert client.get.call_count == 1


def test_refetched_node_without_the_attribute_resolves_to_none(mocker):
    """A refetched node that lacks the attribute gives None, not an AttributeError."""
    client = mocker.MagicMock()
    # The refetched node carries "a" but not "b" (e.g. a peer on a generic schema).
    client.get.return_value = SimpleNamespace(a=FakeAttr("va"))

    wrapper = mocker.MagicMock()
    wrapper.client = client
    processor = iu.InfrahubNodesProcessor(client=wrapper)

    node = FakeNode(client=client, empty_attrs=("a", "b"))
    result = processor.resolve_node_mapping(node=node, attrs=["a", "b"], schemas={}, include_id=False)

    assert result == {"a": "va", "b": None}
