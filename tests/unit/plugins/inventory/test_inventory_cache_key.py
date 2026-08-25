"""Unit tests for the inventory cache key.

The key used to be derived from the API endpoint alone, so two inventory files
pointing at one Infrahub shared a single entry and switching ``branch`` served
the other branch's hosts. Everything that shapes the fetched data belongs in it.
"""

from __future__ import annotations

from ansible_collections.opsmill.infrahub.plugins.inventory.inventory import InventoryModule


def _module(endpoint="http://infrahub:8000", branch="main", nodes=None, token=None, prefetch_relationships=None):
    plugin = InventoryModule()
    plugin.api_endpoint = endpoint
    plugin.branch = branch
    plugin.nodes = nodes if nodes is not None else {"DcimDevice": {"include": ["name"]}}
    # Left unset unless a test asks for them, so the plain calls keep covering a
    # plugin that has not reached _set_authorization or the option read yet.
    if token is not None:
        plugin.token = token
    if prefetch_relationships is not None:
        plugin.prefetch_relationships = prefetch_relationships
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


def test_token_changes_the_key():
    """Infrahub applies permissions per token: two tokens must not share an entry."""
    a = _module(token="token-of-a-read-only-account")
    b = _module(token="token-of-an-admin-account")

    assert a._cache_key() != b._cache_key()


def test_the_raw_token_never_lands_in_the_key():
    """The key becomes a cache filename and shows up in verbose output; only a digest belongs in it."""
    token = "s3cret-infrahub-token"

    assert token not in _module(token=token)._cache_key()


def test_prefetch_relationships_changes_the_key():
    """It decides which relationship data reaches the host variables."""
    a = _module(prefetch_relationships=True)
    b = _module(prefetch_relationships=False)

    assert a._cache_key() != b._cache_key()


def test_a_missing_token_still_builds_a_key():
    plugin = _module()
    plugin.token = None

    assert plugin._cache_key() == _module()._cache_key()


def test_key_order_in_the_node_spec_does_not_matter():
    """The spec is data, not text: two spellings of one request share an entry."""
    a = _module(nodes={"DcimDevice": {"include": ["name"], "exclude": ["serial"]}})
    b = _module(nodes={"DcimDevice": {"exclude": ["serial"], "include": ["name"]}})

    assert a._cache_key() == b._cache_key()


def test_a_numeric_token_is_hashed_without_raising():
    """The option declares no type, and EXAMPLES writes the token as a bare number."""
    plugin = _module(token=1234567890123456478901234567)

    assert plugin._cache_key()


def test_a_numeric_token_and_its_string_spelling_share_an_entry():
    """Same credential, same cache scope -- the YAML quoting is not part of the request."""
    assert _module(token=42)._cache_key() == _module(token="42")._cache_key()
