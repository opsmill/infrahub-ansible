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


def _display_lines(display, level="v"):
    """The messages emitted at one Display level."""
    return [c.args[0] if c.args else c.kwargs.get("msg", "") for c in getattr(display, level).call_args_list]


def test_run_cost_is_reported_at_raised_verbosity(mocker):
    """The run states what it cost, through ``Display.v`` and not through plain output.

    ``Display.v`` is what Ansible gates behind ``-v``. Emitting the same line through
    ``display.display`` or ``error`` would put diagnostics into every playbook's
    normal output, which is why the level matters more than the wording here.
    """
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1"), FakeNode("KindA", "a2")]}
    processor, _wrapper = _make_processor(mocker, nodes_by_kind)
    processor.display = mocker.MagicMock()
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}})

    cost_lines = [line for line in _display_lines(processor.display) if "Inventory fetch cost" in line]
    assert len(cost_lines) == 1, _display_lines(processor.display)
    # Never at default verbosity.
    assert not [c for c in processor.display.display.call_args_list if "Inventory fetch cost" in str(c)]
    assert not [c for c in processor.display.error.call_args_list if "Inventory fetch cost" in str(c)]


def test_run_cost_reports_this_run_not_the_client_lifetime(mocker):
    """The figure is a delta, and it comes from the SDK-level counter.

    Two failure modes are covered here. Counting the wrapper's own calls would miss
    pagination, which happens inside the SDK -- exactly the part that grows with the
    estate. And reporting the counter's absolute value would charge this run for
    every request the client made before it, because the counter belongs to the
    client and outlives a single ``fetch_and_process``.
    """
    from ansible_collections.opsmill.infrahub.plugins.module_utils.metrics import RequestCounter

    counter = RequestCounter()
    for _ in range(5):  # an earlier run on the same client
        counter.record(response=None)

    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1")]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind)
    wrapper.request_counter = counter
    processor.display = mocker.MagicMock()
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    # Each fetch this run makes costs two round-trips (a count query and a page).
    inner = wrapper.fetch_nodes.side_effect

    def counting_fetch(kind, **kwargs):
        counter.record(response=None)
        counter.record(response=None)
        return inner(kind, **kwargs)

    wrapper.fetch_nodes.side_effect = counting_fetch

    processor.fetch_and_process(nodes={"KindA": {}})

    cost_line = next(line for line in _display_lines(processor.display) if "Inventory fetch cost" in line)
    assert "2 request(s)" in cost_line, cost_line
    # The 5 requests from before this run are not charged to it.
    assert "7 request(s)" not in cost_line
    assert counter.responses == 7


def test_run_cost_degrades_when_no_counter_is_attached(mocker):
    """A wrapper without a counter still reports the peer figures, and does not raise."""
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1")]}
    processor, _wrapper = _make_processor(mocker, nodes_by_kind)
    processor.display = mocker.MagicMock()
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}})

    cost_line = next(line for line in _display_lines(processor.display) if "Inventory fetch cost" in line)
    assert "unavailable" in cost_line
    assert "node(s) loaded" in cost_line


def test_run_cost_counts_the_peer_batches_it_issued(mocker):
    """The batch count comes back from ``_warm_peers`` rather than being discarded."""
    shared = FakePeer("site-1", "LocationSite")
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1", peer=shared)]}
    processor, _wrapper = _make_processor(mocker, nodes_by_kind, attrs=["name", "site.name"])
    processor.display = mocker.MagicMock()
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}})

    cost_line = next(line for line in _display_lines(processor.display) if "Inventory fetch cost" in line)
    assert "in 1 batch(es)" in cost_line


def test_run_cost_report_is_silent_without_a_display(mocker):
    """No Display attached -- reporting must be a no-op, not an AttributeError."""
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1")]}
    processor, _wrapper = _make_processor(mocker, nodes_by_kind)
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    assert processor.display is None
    assert processor.fetch_and_process(nodes={"KindA": {}}) is not None


def test_run_cost_breakdown_is_emitted_at_vvv_not_at_v(mocker):
    """The totals ride -v; the per-kind detail rides -vvv.

    Anyone running an inventory at -v wants one line, not a page. The breakdown is
    only useful once the total already looks wrong, so it sits a level deeper.
    """
    shared = FakePeer("site-1", "LocationSite")
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1", peer=shared)]}
    processor, _wrapper = _make_processor(mocker, nodes_by_kind, attrs=["name", "site.name"])
    processor.display = mocker.MagicMock()
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    processor.fetch_and_process(nodes={"KindA": {}})

    at_v = _display_lines(processor.display, "v")
    at_vvv = _display_lines(processor.display, "vvv")
    assert [line for line in at_v if "Inventory fetch cost:" in line]
    assert not [line for line in at_v if "by kind" in line]
    assert [line for line in at_vvv if "Inventory fetch cost, by kind:" in line]
    assert [line for line in at_vvv if "host kind KindA: 1 node(s)" in line]
    assert [line for line in at_vvv if "peer kind LocationSite:" in line]


def test_run_cost_breakdown_distinguishes_narrowed_from_wide_from_generic():
    """Three cases that must not be described the same way.

    A kind with no ``include`` is wide by request. A kind answered via a requested
    generic has no projection of its own, and calling that "not narrowed" would be a
    lie. Only the third is actually narrowed.
    """
    from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import PeerWarmer
    from ansible_collections.opsmill.infrahub.plugins.module_utils.projection import NodeProjection

    fetched = iu.HostFetch()
    fetched.nodes = [FakeNode("Wide", "w1"), FakeNode("Concrete", "c1"), FakeNode("Narrow", "n1")]
    fetched.projections = {
        "Wide": NodeProjection(attrs=["name"], roots={"name"}, include=None, exclude=None, narrowed=False),
        "Narrow": NodeProjection(
            attrs=["name"], roots={"name"}, include=["name"], exclude=["a", "b", "c"], narrowed=True
        ),
    }
    warmer = PeerWarmer(fetch=lambda **kw: [], store=None)
    warmer.stats = {"LocationSite": {"requested": 130, "batches": 3, "loaded": 130, "failed": 0}}

    lines = iu.InfrahubNodesProcessor._run_cost_breakdown(fetched=fetched, warmer=warmer)

    joined = "\n".join(lines)
    assert "host kind Wide: 1 node(s), no include given, full attribute set requested" in joined
    assert "host kind Concrete: 1 node(s), answered via a requested generic" in joined
    assert "host kind Narrow: 1 node(s), requested [name], 3 field(s) excluded" in joined
    assert "peer kind LocationSite: 130 id(s) referenced, 3 batch(es), 130 loaded" in joined


def test_run_cost_breakdown_reports_failed_peer_batches():
    """A peer kind that failed must say so, or its zero shows up as a mystery."""
    from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import PeerWarmer

    warmer = PeerWarmer(fetch=lambda **kw: [], store=None)
    warmer.stats = {"LocationSite": {"requested": 60, "batches": 0, "loaded": 0, "failed": 2}}

    lines = iu.InfrahubNodesProcessor._run_cost_breakdown(fetched=iu.HostFetch(), warmer=warmer)

    assert any("2 batch(es) failed" in line for line in lines)


def test_run_cost_breakdown_is_empty_when_there_is_nothing_to_say():
    """No header without content -- an empty run should not emit a bare heading."""
    from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import PeerWarmer

    warmer = PeerWarmer(fetch=lambda **kw: [], store=None)
    assert iu.InfrahubNodesProcessor._run_cost_breakdown(fetched=iu.HostFetch(), warmer=warmer) == []


def test_run_cost_breakdown_calls_a_refilled_host_kind_by_its_name():
    """A host kind reaching the warmer got there through refill, not a relationship.

    Both passes share one warmer, so refill files host kinds into the same stats map.
    Calling those a peer kind points the reader at the wrong cause.
    """
    from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import PeerWarmer

    fetched = iu.HostFetch()
    fetched.nodes = [FakeNode("KindA", "a1")]
    warmer = PeerWarmer(fetch=lambda **kw: [], store=None)
    warmer.stats = {
        "KindA": {"requested": 1, "batches": 1, "loaded": 1, "failed": 0},
        "LocationSite": {"requested": 1, "batches": 1, "loaded": 1, "failed": 0},
    }

    joined = "\n".join(iu.InfrahubNodesProcessor._run_cost_breakdown(fetched=fetched, warmer=warmer))

    assert "refilled host kind KindA:" in joined
    assert "peer kind LocationSite:" in joined
    assert "peer kind KindA:" not in joined


def test_run_cost_names_failed_batches_in_the_totals(mocker):
    """A batch that failed still cost a round-trip, so the cost line says so."""
    shared = FakePeer("site-1", "LocationSite")
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1", peer=shared)]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind, attrs=["name", "site.name"])
    processor.display = mocker.MagicMock()
    mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "x"})

    hosts = wrapper.fetch_nodes.side_effect

    def failing_peer_fetch(kind, **kwargs):
        if kind == "LocationSite":
            raise RuntimeError("boom")
        return hosts(kind, **kwargs)

    wrapper.fetch_nodes.side_effect = failing_peer_fetch

    processor.fetch_and_process(nodes={"KindA": {}})

    cost_line = next(line for line in _display_lines(processor.display) if "Inventory fetch cost" in line)
    assert "1 batch(es) failed" in cost_line, cost_line
    # The batch that failed loaded nothing, so it is not folded into the loaded count.
    assert "0 node(s) loaded in 0 batch(es)" in cost_line, cost_line


def test_run_cost_is_reported_when_the_query_matched_no_hosts(mocker):
    """An empty-but-successful fetch still cost requests, and still reports them."""
    processor, _wrapper = _make_processor(mocker, {})
    processor.display = mocker.MagicMock()

    assert processor.fetch_and_process(nodes={"KindA": {}}) is None

    cost_lines = [line for line in _display_lines(processor.display) if "Inventory fetch cost" in line]
    assert len(cost_lines) == 1, _display_lines(processor.display)
    assert "0 node(s) loaded in 0 batch(es)" in cost_lines[0]


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


def test_each_fetch_resolves_its_nodes_with_its_own_attribute_list(mocker):
    """A generic and one of its concrete kinds are two specs, not one.

    Both fetches answer with the same concrete ``__typename``, so a single by-kind
    attribute map lets whichever spec registered last speak for both: the other's
    fields get read off nodes whose query never projected them, and its variables are
    lost. Each node is resolved with the spec that fetched it instead, and a host both
    specs answered with carries the union rather than one silently replacing the other.
    """
    nodes_by_kind = {
        "TestingLocation": [FakeNode("TestingSite", "s1")],
        # A second fetch of the same underlying node, as the server would answer it.
        "TestingSite": [FakeNode("TestingSite", "s1")],
    }
    processor, _wrapper = _make_processor(mocker, nodes_by_kind)

    def resolve(node, attrs, schemas, include_id, refill):
        return {attr: f"{node.id}-{attr}" for attr in attrs} | {"id": node.id}

    resolved = mocker.patch.object(processor, "resolve_node_mapping", side_effect=resolve)

    result = processor.fetch_and_process(
        nodes={"TestingLocation": {"include": ["name"]}, "TestingSite": {"include": ["shortname"]}}
    )

    assert [c.kwargs["attrs"] for c in resolved.call_args_list] == [["name"], ["shortname"]]
    assert result == {"s1": {"id": "s1", "name": "s1-name", "shortname": "s1-shortname"}}


def test_a_refill_is_judged_by_the_query_that_fetched_the_node(mocker):
    """An empty field the fetching query never projected is still worth a reload.

    The node reports its concrete kind, so a ledger keyed on that alone consults the
    *concrete* spec's projection -- which did project the field -- and calls the empty a
    genuine null. The refill is suppressed and the value stays empty with nothing queued
    to fix it, which is silently wrong data rather than a slow run.
    """
    from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import RefillLedger

    processor, _wrapper = _make_processor(mocker, {})
    node = FakeNode("TestingSite", "s1")
    generic = SimpleNamespace(projected=lambda root: False)
    concrete = SimpleNamespace(projected=lambda root: True)

    fetched = iu.HostFetch()
    fetched.nodes = [node]
    fetched.projections = {"TestingLocation": generic, "TestingSite": concrete}
    fetched.contexts = [iu.HostContext(kind="TestingLocation", nodes=[node], attrs=["name"], projection=generic)]

    def resolve(node, attrs, schemas, include_id, refill):
        refill.record(node, "name")
        return {"id": node.id}

    mocker.patch.object(processor, "resolve_node_mapping", side_effect=resolve)
    refill = RefillLedger(projections=fetched.projections)

    processor._resolve_hosts(fetched=fetched, include_id=True, refill=refill)

    assert refill.pending == {"TestingSite": {"s1"}}


def test_a_hand_built_fetch_falls_back_to_the_by_kind_attributes(mocker):
    """No per-fetch context: resolve off the by-kind map, exactly as before."""
    from ansible_collections.opsmill.infrahub.plugins.module_utils.peers import RefillLedger

    processor, _wrapper = _make_processor(mocker, {})

    fetched = iu.HostFetch()
    fetched.nodes = [FakeNode("KindA", "a1")]
    fetched.attrs_by_kind = {"KindA": ["name", "site.name"]}

    resolve = mocker.patch.object(processor, "resolve_node_mapping", return_value={"id": "a1"})
    result = processor._resolve_hosts(fetched=fetched, include_id=True, refill=RefillLedger.disabled())

    assert result == {"a1": {"id": "a1"}}
    assert resolve.call_args.kwargs["attrs"] == ["name", "site.name"]


def test_merging_two_specs_keeps_both_nested_paths():
    """Two specs naming different nested paths under one root must not erase each other."""
    existing = {"id": "s1", "site": {"id": "x1", "name": "paris"}, "name": None}

    iu.InfrahubNodesProcessor._merge_host_result(
        existing, {"id": "s1", "site": {"id": "x1", "shortname": "par"}, "name": "site-1"}
    )

    assert existing == {"id": "s1", "site": {"id": "x1", "name": "paris", "shortname": "par"}, "name": "site-1"}


def test_merging_keeps_a_falsy_answer_over_an_unresolved_placeholder():
    """``False`` and ``0`` are answers; ``None`` and ``{}`` are what an unasked field looks like."""
    existing = {"enabled": False, "count": 0, "site": {}}

    iu.InfrahubNodesProcessor._merge_host_result(existing, {"enabled": None, "count": None, "site": {"name": "paris"}})

    assert existing == {"enabled": False, "count": 0, "site": {"name": "paris"}}


def test_a_refill_batch_that_comes_back_short_is_reported(mocker):
    """A refill that returns fewer nodes than it asked for must not be silent.

    The second pass runs on a disabled ledger, so a node the refill never reloaded
    resolves exactly as the first pass resolved it and its unqueried attributes stay
    empty. Aborting the run instead would hand Ansible zero hosts over one peer that
    vanished mid-run, so the values are kept -- but the warning is what says they are
    short, and without it the gap is invisible.
    """
    nodes_by_kind = {"KindA": [FakeNode("KindA", "a1")]}
    processor, wrapper = _make_processor(mocker, nodes_by_kind)
    processor.display = mocker.MagicMock()

    hosts = wrapper.fetch_nodes.side_effect

    def fetch(kind, **kwargs):
        if (kwargs.get("filters") or {}).get("ids"):
            # The refill pass: the node is gone by the time it is asked for by id.
            return []
        return hosts(kind, **kwargs)

    wrapper.fetch_nodes.side_effect = fetch

    def resolve(node, attrs, schemas, include_id, refill):
        if refill is not None:
            # `name` is not in the include, so the ledger judges it never queried.
            refill.record(node, "name")
        return {"id": node.id, "name": None}

    mocker.patch.object(processor, "resolve_node_mapping", side_effect=resolve)

    result = processor.fetch_and_process(nodes={"KindA": {"include": ["site.name"]}})

    warnings = [line for line in _display_lines(processor.display, "warning") if "Refill came back short" in line]
    assert len(warnings) == 1, _display_lines(processor.display, "warning")
    assert "KindA (a1)" in warnings[0]
    assert "1 node(s) never returned" in warnings[0]
    # The run still completes, with the values the first pass had.
    assert result == {"a1": {"id": "a1", "name": None}}


def test_a_refill_that_comes_back_whole_says_nothing():
    """No warning when every queued id was loaded: the diagnostic is for the gap only."""
    processor = iu.InfrahubNodesProcessor.__new__(iu.InfrahubNodesProcessor)
    processor.display = None

    emitted = []
    processor._handle_display = lambda message, level=None, exception=None: emitted.append((level, message))

    processor._warn_on_short_refill(queued={"KindA": {"a1", "a2"}}, loaded={"a1", "a2", "s1"})

    assert emitted == []


def test_a_short_refill_warning_caps_the_ids_it_names():
    """Hundreds of missing UUIDs would bury the count that the warning exists to give."""
    processor = iu.InfrahubNodesProcessor.__new__(iu.InfrahubNodesProcessor)
    processor.display = None

    emitted = []
    processor._handle_display = lambda message, level=None, exception=None: emitted.append((level, message))

    processor._warn_on_short_refill(queued={"KindA": {f"id-{n:02d}" for n in range(12)}}, loaded=set())

    (level, message) = emitted[0]
    assert level == "WARNING"
    assert "12 node(s) never returned" in message
    assert "id-00" in message
    assert "id-05" not in message
    assert "and 7 more" in message


def test_merging_prefers_the_nested_answer_over_a_bare_id():
    """`site` resolves to the peer id, `site.name` to its attributes; the richer one wins."""
    existing = {"id": "d1", "site": "x1"}

    iu.InfrahubNodesProcessor._merge_host_result(existing, {"id": "d1", "site": {"id": "x1", "name": "paris"}})

    assert existing == {"id": "d1", "site": {"id": "x1", "name": "paris"}}


def test_merging_does_not_let_a_bare_id_overwrite_the_nested_answer():
    """The other order must give the same result, or output depends on node-spec order."""
    existing = {"id": "d1", "site": {"id": "x1", "name": "paris"}}

    iu.InfrahubNodesProcessor._merge_host_result(existing, {"id": "d1", "site": "x1"})

    assert existing == {"id": "d1", "site": {"id": "x1", "name": "paris"}}


def test_merging_prefers_nested_peers_over_a_list_of_ids():
    """Same rule for cardinality-many: a list of dicts beats a list of ids."""
    existing = {"id": "d1", "tags": ["t1", "t2"]}

    iu.InfrahubNodesProcessor._merge_host_result(
        existing, {"id": "d1", "tags": [{"id": "t1", "name": "edge"}, {"id": "t2", "name": "core"}]}
    )

    assert existing == {"id": "d1", "tags": [{"id": "t1", "name": "edge"}, {"id": "t2", "name": "core"}]}
