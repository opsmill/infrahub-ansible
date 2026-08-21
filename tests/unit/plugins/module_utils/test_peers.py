"""Unit tests for ``PeerWarmer`` and ``RefillLedger``.

Both exist to keep a resolution pass from spending one request per peer without
spending one pass per peer *kind* either. The properties pinned here are about
volume: what gets asked for, and how many calls it takes.
"""

from __future__ import annotations

from types import SimpleNamespace

from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import PeerWarmer, RefillLedger


class FakePeer:
    def __init__(self, peer_id, typename):
        self.id = peer_id
        self.typename = typename


class FakeManager:
    """Stand-in for a ``RelationshipManagerSync``."""

    def __init__(self, peers, initialized=True):
        self.peers = peers
        self.initialized = initialized


class FakeNode:
    def __init__(self, kind, node_id, **rels):
        self._schema = SimpleNamespace(kind=kind, attribute_names=["name"])
        self.id = node_id
        for name, value in rels.items():
            setattr(self, name, value)


class RecordingFetch:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return []


def _warmer(fetch=None, store_get=None, page_size=50):
    store = SimpleNamespace(get=store_get or (lambda key, raise_when_missing=True: None))
    return PeerWarmer(fetch=fetch or RecordingFetch(), store=store, page_size=page_size)


def test_collect_only_gathers_roots_with_nested_paths():
    """A bare relationship resolves to a peer id, so its peer needs no attributes."""
    node = FakeNode("KindA", "a1", site=FakePeer("s1", "LocationSite"), platform=FakePeer("p1", "DcimPlatform"))

    referenced = _warmer().collect([node], {"KindA": ["name", "site.name", "platform"]})

    assert referenced == {"LocationSite": {"s1"}}


def test_collect_dedupes_across_nodes():
    shared = FakePeer("s1", "LocationSite")
    nodes = [FakeNode("KindA", "a1", site=shared), FakeNode("KindA", "a2", site=shared)]

    referenced = _warmer().collect(nodes, {"KindA": ["site.name"]})

    assert referenced == {"LocationSite": {"s1"}}


def test_collect_skips_peers_already_complete_in_the_store():
    """A peer whose attributes already arrived inline is not fetched again."""
    stored = SimpleNamespace(
        _schema=SimpleNamespace(attribute_names=["name"]),
        name=SimpleNamespace(value="London"),
    )
    node = FakeNode("KindA", "a1", site=FakePeer("s1", "LocationSite"))

    referenced = _warmer(store_get=lambda key, raise_when_missing=True: stored).collect(
        [node], {"KindA": ["site.name"]}
    )

    assert referenced == {}


def test_collect_keeps_peers_the_generic_projection_left_empty():
    """The case this module exists for: the concrete kind has an attribute the query never asked for."""
    stored = SimpleNamespace(
        _schema=SimpleNamespace(attribute_names=["name", "shortname"]),
        name=SimpleNamespace(value=None),
        shortname=SimpleNamespace(value="lon"),
    )
    node = FakeNode("KindA", "a1", site=FakePeer("s1", "LocationSite"))

    referenced = _warmer(store_get=lambda key, raise_when_missing=True: stored).collect(
        [node], {"KindA": ["site.name"]}
    )

    assert referenced == {"LocationSite": {"s1"}}


def test_collect_leaves_an_uninitialised_many_relationship_alone():
    """Forcing it would be the per-node round-trip this module avoids."""
    node = FakeNode("KindA", "a1", tags=FakeManager(peers=[], initialized=False))

    assert _warmer().collect([node], {"KindA": ["tags.name"]}) == {}


def test_warm_issues_one_call_per_page():
    fetch = RecordingFetch()
    warmer = _warmer(fetch=fetch, page_size=2)

    calls = warmer.warm({"LocationSite": {"s1", "s2", "s3"}})

    assert calls == 2
    assert [c["filters"] for c in fetch.calls] == [{"ids": ["s1", "s2"]}, {"ids": ["s3"]}]
    # Parallel mode spends a round-trip counting first, which is a loss for one page.
    assert all(c["parallel"] is False for c in fetch.calls)


def test_warm_survives_one_bad_kind():
    seen = []

    def fetch(**kwargs):
        if kwargs["kind"] == "Broken":
            raise RuntimeError("boom")
        seen.append(kwargs["kind"])
        return []

    warmer = PeerWarmer(fetch=fetch, store=SimpleNamespace(get=lambda **kw: None), on_error=lambda k, e: None)
    warmer.warm({"Broken": {"x"}, "Fine": {"y"}})

    assert seen == ["Fine"]


def test_ledger_ignores_a_null_that_was_actually_queried():
    """An attribute that was asked for and came back empty is a genuine null."""
    projection = SimpleNamespace(projected=lambda root: True)
    ledger = RefillLedger(projections={"KindA": projection})

    ledger.record(FakeNode("KindA", "a1"), "description")

    assert ledger.pending == {}
    assert not ledger


def test_ledger_records_an_attribute_that_was_never_queried():
    projection = SimpleNamespace(projected=lambda root: False)
    ledger = RefillLedger(projections={"KindA": projection})

    ledger.record(FakeNode("KindA", "a1"), "name")

    assert ledger.pending == {"KindA": {"a1"}}
    assert ledger


def test_ledger_records_kinds_it_has_no_projection_for():
    """Peers have no projection of their own; erring towards one extra batched call is safe."""
    ledger = RefillLedger(projections={})

    ledger.record(FakeNode("LocationSite", "s1"), "name")

    assert ledger.pending == {"LocationSite": {"s1"}}


def test_disabled_ledger_records_nothing():
    ledger = RefillLedger.disabled()

    ledger.record(FakeNode("KindA", "a1"), "name")

    assert ledger.pending == {}


def test_collect_warms_a_peer_a_depth_two_path_reads_through():
    """``site.region.name``: the peer's own relationships only arrive when it is warmed.

    The inline payload the host query carries stops one level down, so calling the
    peer satisfied here leaves resolution fetching one region per site -- the
    per-peer round-trip this module exists to avoid.
    """
    stored = SimpleNamespace(
        _schema=SimpleNamespace(attribute_names=["name"], relationship_names=["region"]),
        name=SimpleNamespace(value="London"),
        region=SimpleNamespace(id="r1", typename="LocationRegion"),
    )
    node = FakeNode("KindA", "a1", site=FakePeer("s1", "LocationSite"))

    referenced = _warmer(store_get=lambda key, raise_when_missing=True: stored).collect(
        [node], {"KindA": ["site.region.name"]}
    )

    assert referenced == {"LocationSite": {"s1"}}


def test_warm_passes_the_order_it_was_given():
    """Ordering is server-side work nobody here needs, exactly as for the host query."""
    fetch = RecordingFetch()
    warmer = PeerWarmer(fetch=fetch, store=SimpleNamespace(get=lambda **kw: None), order="ORDER")

    warmer.warm({"LocationSite": {"s1"}})

    assert fetch.calls[0]["order"] == "ORDER"


def test_warm_records_the_ids_it_loaded():
    warmer = _warmer()

    warmer.warm({"LocationSite": {"s1", "s2"}})

    assert warmer.loaded == {"s1", "s2"}


def test_ledger_ignores_a_peer_the_warmer_already_loaded_in_full():
    """A value still empty after a complete fetch is a genuine null.

    Peers carry no projection, so without this every falsy peer attribute would queue
    a refill -- a redundant refetch plus a second full resolution pass, every run.
    """
    warmer = _warmer()
    warmer.warm({"LocationSite": {"s1"}})
    ledger = RefillLedger(projections={}, already_loaded=warmer.loaded)

    ledger.record(FakeNode("LocationSite", "s1"), "description")

    assert ledger.pending == {}
    assert not ledger
