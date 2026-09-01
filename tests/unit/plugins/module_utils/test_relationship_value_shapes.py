# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""The shape ``resolve_node_mapping`` gives a root that resolved to nothing.

A host variable that changes type when the data behind it is empty breaks every
inventory expression written against the populated case: ``'edge' in tags`` reads
fine on a device with tags and raises "argument of type 'NoneType' is not
iterable" on the one without, which under ``strict: false`` drops that host from
the group with no explanation.

These build real ``InfrahubNodeSync`` objects from a real schema, because the
shape under test is the SDK's -- a stand-in that returns lists where the SDK
returns a ``RelationshipManagerSync`` would pin nothing.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu
from infrahub_sdk.node import InfrahubNodeSync
from infrahub_sdk.schema import NodeSchemaAPI

DEVICE_SCHEMA = NodeSchemaAPI(
    id="schema-1",
    name="Device",
    namespace="Dcim",
    branch="aware",
    attributes=[{"id": "a1", "name": "name", "kind": "Text", "optional": False}],
    relationships=[
        {
            "id": "r1",
            "name": "tags",
            "peer": "BuiltinTag",
            "cardinality": "many",
            "kind": "Attribute",
            "optional": True,
        },
        {
            "id": "r2",
            "name": "software_version",
            "peer": "DcimSoftwareVersion",
            "cardinality": "one",
            "kind": "Attribute",
            "optional": True,
        },
    ],
)


def _processor() -> iu.InfrahubNodesProcessor:
    wrapper = MagicMock()
    # Nothing in the store, so a peer would have to be fetched -- which none of
    # these cases should reach, since there are no peers to resolve.
    wrapper.client.store.get.return_value = None
    return iu.InfrahubNodesProcessor(client=wrapper)


def _device(data: dict) -> InfrahubNodeSync:
    client = MagicMock()
    client.default_branch = "main"
    client.store.get.return_value = None
    return InfrahubNodeSync(client=client, schema=DEVICE_SCHEMA, data=data)


EMPTY = {"id": "dev-1", "name": {"value": "cr01"}, "tags": [], "software_version": None}
POPULATED = {
    "id": "dev-2",
    "name": {"value": "cr02"},
    "tags": [{"id": "tag-1", "__typename": "BuiltinTag"}, {"id": "tag-2", "__typename": "BuiltinTag"}],
    "software_version": None,
}


@pytest.mark.parametrize("attrs", [["tags"], ["tags.name"]])
def test_empty_many_relationship_resolves_to_a_list(attrs):
    """An empty cardinality-many relationship is ``[]``, bare or with a nested path.

    It used to be ``None`` when asked for bare and ``{}`` when asked for with a
    nested path -- neither of which a caller doing ``in``, ``length`` or a loop can
    read the way it reads the populated answer.
    """
    result = _processor().resolve_node_mapping(node=_device(EMPTY), attrs=attrs, schemas={})

    assert result["tags"] == []


def test_populated_many_relationship_still_resolves_to_its_peer_ids():
    """The empty case is the only thing that changed: a bare root is still peer ids."""
    result = _processor().resolve_node_mapping(node=_device(POPULATED), attrs=["tags"], schemas={})

    assert result["tags"] == ["tag-1", "tag-2"]


def test_empty_and_populated_many_relationships_agree_on_type():
    """The point of the fix: one expression can read both hosts."""
    empty = _processor().resolve_node_mapping(node=_device(EMPTY), attrs=["tags"], schemas={})
    populated = _processor().resolve_node_mapping(node=_device(POPULATED), attrs=["tags"], schemas={})

    assert type(empty["tags"]) is type(populated["tags"])


def test_unset_cardinality_one_relationship_stays_scalar():
    """A cardinality-one root resolves to a peer id, so its empty is ``None``, not ``[]``."""
    result = _processor().resolve_node_mapping(node=_device(EMPTY), attrs=["software_version"], schemas={})

    assert result["software_version"] is None


def test_unset_cardinality_one_relationship_with_a_nested_path_stays_an_empty_mapping():
    """``{}`` is falsy, so ``software_version | default(...)`` and ``if software_version``
    keep working; seeding the requested keys instead would make "no peer" truthy."""
    result = _processor().resolve_node_mapping(node=_device(EMPTY), attrs=["software_version.version"], schemas={})

    assert result["software_version"] == {}


def test_empty_value_falls_back_when_the_schema_cannot_be_asked():
    """A schema stand-in without ``get_relationship_or_none`` gets the scalar seed.

    Several tests here and in the fetch-resolution suite build schemas as plain
    namespaces; reading cardinality off one must degrade, not raise.
    """
    schema = SimpleNamespace(kind="KindA", attribute_names=[], relationship_names=["tags"])

    assert iu.InfrahubNodesProcessor._empty_value(schema, "tags", None, has_nested=False) is None
    assert iu.InfrahubNodesProcessor._empty_value(schema, "tags", None, has_nested=True) == {}
