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
    """Records the fetch calls and returns a node per requested id.

    Returning the nodes matters: ``warm`` records what actually came back, not what
    it asked for, so a fake that returns [] models a fetch that found nothing.
    """

    def __init__(self, found=None):
        self.calls = []
        # None = every requested id is found. A set = only these are.
        self.found = found

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        ids = kwargs.get("filters", {}).get("ids", [])
        return [SimpleNamespace(id=i) for i in ids if self.found is None or i in self.found]


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
    """A kind that raises must not stop the others, and must not vanish either.

    `on_error` is the only place a failed kind surfaces by name, and the tally is the
    only place the run-cost breakdown can see it, so both are asserted alongside the
    good kind still being fetched.
    """
    seen = []
    errors = []
    boom = RuntimeError("boom")

    def fetch(**kwargs):
        if kwargs["kind"] == "Broken":
            raise boom
        seen.append(kwargs["kind"])
        return []

    warmer = PeerWarmer(
        fetch=fetch,
        store=SimpleNamespace(get=lambda **kw: None),
        on_error=lambda kind, exc: errors.append((kind, exc)),
    )
    warmer.warm({"Broken": {"x"}, "Fine": {"y"}})

    assert seen == ["Fine"]
    assert errors == [("Broken", boom)]
    assert warmer.stats["Broken"]["failed"] == 1
    assert warmer.stats["Broken"]["batches"] == 0
    assert warmer.stats["Fine"]["failed"] == 0


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


def test_warm_does_not_record_ids_the_fetch_did_not_return():
    """A requested id that does not come back was not loaded.

    Peers can vanish between the host query and the warm -- deleted, or hidden by
    permissions. Marking them loaded would tell RefillLedger their empty attributes
    are genuine nulls and suppress the retry that would notice.
    """
    fetch = RecordingFetch(found={"s1"})
    warmer = _warmer(fetch=fetch)

    warmer.warm({"LocationSite": {"s1", "s2"}})

    assert warmer.loaded == {"s1"}


def test_warm_records_nothing_when_the_fetch_is_swallowed():
    """The wrapper's exception decorator returns None instead of raising.

    Nothing is loaded, and the failure still has to reach ``on_error``: that callback
    is what raises the caller's per-kind WARNING, so without it the kind silently
    contributes no peers.
    """
    errors = []
    warmer = PeerWarmer(
        fetch=lambda **kwargs: None,
        store=SimpleNamespace(get=lambda key, raise_when_missing=True: None),
        on_error=lambda kind, exc: errors.append((kind, exc)),
    )

    warmer.warm({"LocationSite": {"s1"}})

    assert warmer.loaded == set()
    assert [kind for kind, _exc in errors] == ["LocationSite"]
    assert "fetch failed" in str(errors[0][1])
    # Counted once, by the branch that saw the None -- not again by the `except`.
    assert warmer.stats["LocationSite"]["failed"] == 1


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


def test_warm_counts_a_swallowed_batch_as_failed_not_as_a_batch():
    """A ``None`` return is a failure the wrapper already swallowed.

    ``handle_infrahub_exceptions_decorator`` logs and returns ``None`` rather than
    raising whenever a Display is attached, which is always in the inventory, so the
    ``except`` never fires. Counting it as a batch that worked hides the failure.
    """
    warmer = _warmer(fetch=lambda **kwargs: None)

    calls = warmer.warm({"LocationSite": {"s1"}})

    assert calls == 0
    assert warmer.stats["LocationSite"]["batches"] == 0
    assert warmer.stats["LocationSite"]["failed"] == 1


def test_warm_counts_each_loaded_id_once_across_passes():
    """``warm`` runs twice a run, and the by-kind tally must still reconcile.

    The summary reports ``len(warmer.loaded)``, a deduplicated set, so counting every
    returned node would overshoot it for any id that comes back in both passes.
    """
    warmer = _warmer()

    warmer.warm({"LocationSite": {"s1", "s2"}})
    warmer.warm({"LocationSite": {"s1"}})

    assert warmer.loaded == {"s1", "s2"}
    assert warmer.stats["LocationSite"]["loaded"] == 2
    # Both passes were issued, so both are still charged as batches.
    assert warmer.stats["LocationSite"]["batches"] == 2


def test_scoped_view_shares_the_parent_pending_set():
    """One batched reload, however many resolution passes feed it.

    A view exists because two specs can answer with the same concrete kind and a
    kind-keyed projection map cannot tell them apart. Copying ``pending`` instead of
    sharing it would leave each pass queueing into a ledger nobody ever reloads.
    """
    parent = RefillLedger(projections={"KindA": SimpleNamespace(projected=lambda root: True)})
    view = parent.scoped({"KindA": SimpleNamespace(projected=lambda root: False)})

    view.record(FakeNode("KindA", "a1"), "name")

    assert view.pending is parent.pending
    assert parent.pending == {"KindA": {"a1"}}
    # The parent is what the caller tests before issuing the reload.
    assert parent


def test_scoped_view_judges_against_its_own_projections():
    """The parent's verdict for that kind must not leak into the view.

    This is the suppression the view exists to stop: the node came from a query that
    never projected the field, so the empty is not a genuine null -- even though the
    other spec for that same concrete kind did project it.
    """
    parent = RefillLedger(projections={"KindA": SimpleNamespace(projected=lambda root: False)})
    view = parent.scoped({"KindA": SimpleNamespace(projected=lambda root: True)})

    view.record(FakeNode("KindA", "a1"), "name")

    assert view.pending == {}


def test_scoped_view_inherits_enabled_and_already_loaded():
    """A view of a disabled ledger records nothing, and a peer loaded in full stays exempt."""
    disabled = RefillLedger.disabled().scoped({})
    disabled.record(FakeNode("KindA", "a1"), "name")
    assert disabled.pending == {}

    loaded = RefillLedger(projections={}, already_loaded={"s1"}).scoped({})
    loaded.record(FakeNode("LocationSite", "s1"), "name")
    assert loaded.pending == {}
    # An id nothing fetched in full still queues.
    loaded.record(FakeNode("LocationSite", "s2"), "name")
    assert loaded.pending == {"LocationSite": {"s2"}}


def test_collect_skips_a_peer_whose_attribute_is_genuinely_empty():
    """An empty string is an answer, so asking again just buys the same empty string.

    ``_resolve_schema_attribute`` treats ``""`` as falsy-but-present and only queues a
    refill on ``None``; warming on ``""`` here made every such peer a fresh fetch on
    every single run, for a value that cannot change.
    """
    stored = SimpleNamespace(
        _schema=SimpleNamespace(attribute_names=["name"]),
        name=SimpleNamespace(value=""),
    )
    node = FakeNode("KindA", "a1", site=FakePeer("s1", "LocationSite"))

    referenced = _warmer(store_get=lambda key, raise_when_missing=True: stored).collect(
        [node], {"KindA": ["site.name"]}
    )

    assert referenced == {}


def test_collect_still_warms_a_peer_whose_attribute_is_none():
    """The companion case: ``None`` is the never-queried signal, and worth a request."""
    stored = SimpleNamespace(
        _schema=SimpleNamespace(attribute_names=["name"]),
        name=SimpleNamespace(value=None),
    )
    node = FakeNode("KindA", "a1", site=FakePeer("s1", "LocationSite"))

    referenced = _warmer(store_get=lambda key, raise_when_missing=True: stored).collect(
        [node], {"KindA": ["site.name"]}
    )

    assert referenced == {"LocationSite": {"s1"}}
