"""Unit tests for the inventory cache key.

The key used to be derived from the API endpoint alone, so two inventory files
pointing at one Infrahub shared a single entry and switching ``branch`` served
the other branch's hosts. Everything that shapes the fetched data belongs in it.
"""

from __future__ import annotations

from ansible_collections.opsmill.infrahub.plugins.inventory.inventory import InventoryModule


def _module(endpoint="http://infrahub:8000", branch="main", nodes=None):
    plugin = InventoryModule()
    plugin.api_endpoint = endpoint
    plugin.branch = branch
    plugin.nodes = nodes if nodes is not None else {"DcimDevice": {"include": ["name"]}}
    return plugin


def test_same_request_gives_the_same_key():
    assert _module()._cache_key() == _module()._cache_key()


def test_branch_changes_the_key():
    assert _module(branch="main")._cache_key() != _module(branch="feature-x")._cache_key()


def test_node_spec_changes_the_key():
    a = _module(nodes={"DcimDevice": {"include": ["name"]}})
    b = _module(nodes={"DcimDevice": {"include": ["name", "serial"]}})

    assert a._cache_key() != b._cache_key()


def test_node_kind_changes_the_key():
    a = _module(nodes={"DcimDevice": {}})
    b = _module(nodes={"IpamPrefix": {}})

    assert a._cache_key() != b._cache_key()


def test_filters_change_the_key():
    a = _module(nodes={"DcimDevice": {"filters": {"role__value": "spine"}}})
    b = _module(nodes={"DcimDevice": {"filters": {"role__value": "leaf"}}})

    assert a._cache_key() != b._cache_key()


def test_endpoint_changes_the_key():
    assert _module(endpoint="http://a:8000")._cache_key() != _module(endpoint="http://b:8000")._cache_key()


def test_key_order_in_the_node_spec_does_not_matter():
    """The spec is data, not text: two spellings of one request share an entry."""
    a = _module(nodes={"DcimDevice": {"include": ["name"], "exclude": ["serial"]}})
    b = _module(nodes={"DcimDevice": {"exclude": ["serial"], "include": ["name"]}})

    assert a._cache_key() == b._cache_key()
