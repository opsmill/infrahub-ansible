"""Unit tests for ``NodeProjection``.

The headline behaviour: an explicit ``include`` must reach the wire. The SDK
narrows a query by ``exclude`` only -- ``include`` merely opts cardinality-many
relationships in, and a dotted path matches nothing -- so without this
translation ``include: [name]`` and no include at all produce the same query.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils.projection import NodeProjection

SCHEMA = SimpleNamespace(
    kind="InfraDevice",
    attribute_names=["name", "description", "serial", "config"],
    relationship_names=["site", "tags", "platform"],
)

DEFAULT_ATTRS = ["name", "description", "serial", "config", "site", "platform"]


def _build(include=None, exclude=None):
    return NodeProjection.build(schema=SCHEMA, include=include, exclude=exclude, resolvable_attrs=DEFAULT_ATTRS)


def test_include_becomes_an_exclude_complement():
    """Everything the schema offers and the user did not ask for is excluded."""
    projection = _build(include=["name", "site.name"])

    # The four hierarchy pseudo-fields ride along: see
    # test_hierarchy_fields_are_excluded_when_not_requested.
    assert projection.exclude == [
        "ancestors",
        "children",
        "config",
        "descendants",
        "description",
        "parent",
        "platform",
        "serial",
        "tags",
    ]
    assert projection.include == ["name", "site"]
    # Resolution still works off the dotted paths the user wrote.
    assert projection.attrs == ["name", "site.name"]


def test_many_relationship_is_opted_in():
    """A cardinality-many relationship the user asked for is named in include, not excluded."""
    projection = _build(include=["name", "tags.name"])

    assert "tags" in projection.include
    assert "tags" not in (projection.exclude or [])


def test_no_include_keeps_the_wide_query():
    """A bare `nodes: {Kind: {}}` must not start narrowing: that would change what it returns."""
    projection = _build()

    assert projection.exclude is None
    assert projection.include is None
    assert projection.narrowed is False
    assert projection.attrs == DEFAULT_ATTRS


def test_user_exclude_is_preserved_alongside_the_complement():
    projection = _build(include=["name"], exclude=["something_else"])

    assert "something_else" in projection.exclude


def test_unknown_roots_are_not_excluded():
    """A root the schema does not define is left alone rather than pushed into exclude.

    It is either a special node property or a typo, and excluding an unknown name
    would be a query error rather than a narrowing.
    """
    projection = _build(include=["name", "display_label", "typo_here"])

    assert "display_label" not in (projection.exclude or [])
    assert "typo_here" not in (projection.exclude or [])
    assert "display_label" not in projection.include


@pytest.mark.parametrize(
    ("root", "expected"),
    [
        ("name", True),  # asked for
        ("description", False),  # excluded, so an empty value means "never queried"
        ("display_label", True),  # always in the SDK's query
        ("id", True),
    ],
)
def test_projected_reports_what_reached_the_server(root, expected):
    """`projected` is what separates a genuine null from a field nobody requested."""
    assert _build(include=["name", "site.name"]).projected(root) is expected


def test_projected_is_true_for_everything_when_not_narrowed():
    projection = _build()

    assert projection.projected("description") is True
    assert projection.projected("serial") is True


def test_projected_respects_a_user_exclude_when_not_narrowed():
    projection = _build(exclude=["serial"])

    assert projection.projected("serial") is False
    assert projection.projected("name") is True


def test_hierarchy_fields_are_excluded_when_not_requested():
    """A narrowed query must not still drag both hierarchies down on every page.

    ``parent``/``children``/``ancestors``/``descendants`` are pseudo-schemas the SDK
    adds to every query when ``prefetch_relationships`` is on. They never appear in
    ``relationship_names``, so the exclude complement misses them unless they are
    named -- which is how a hierarchical kind (Location, IPAM prefix) kept paying for
    two full hierarchies per page despite an explicit ``include``.
    """
    projection = _build(include=["name"])

    for field in ("parent", "children", "ancestors", "descendants"):
        assert field in projection.exclude


def test_a_requested_hierarchy_field_is_not_excluded():
    """Asking for one must still fetch it."""
    projection = _build(include=["name", "parent.name"])

    assert "parent" not in projection.exclude
    assert "children" in projection.exclude
