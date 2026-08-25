# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Filling the store with the peers a resolution pass is about to ask for.

Nested paths like ``location.name`` resolve against peer nodes held in the SDK
store. Peers arrive there two ways, and neither is reliable on its own:

* Inline, from the host query's ``prefetch_relationships``. Complete only when
  the relationship's declared peer is the concrete kind -- the SDK builds the
  peer's projection from the *declared* peer schema, so a relationship pointing
  at a generic (``LocationHosting`` exposes ``shortname``) yields peers missing
  the attributes the concrete kind (``LocationSite`` has ``name``) actually has.
* One request per peer, on demand, during resolution.

``PeerWarmer`` closes the gap in between: it reads the ids the host nodes
already reference, keeps the ones whose attributes are genuinely missing, and
fetches those by id -- one request per page of peers, on the concrete kind.
Cost tracks the number of peers referenced, not the size of the peer kind.
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_PAGE_SIZE = 50


class RefillLedger:
    """Records nodes whose attributes the query never carried, for one batched reload.

    An empty attribute means one of two things. The server answered null -- in which
    case asking again returns the same null -- or the field was never in the
    projection, which is what happens to peers built from a generic peer schema. Only
    the second is worth a second request, and the projection is what tells them apart.
    """

    def __init__(
        self,
        projections: dict[str, Any] | None = None,
        enabled: bool = True,
        already_loaded: set[str] | None = None,
    ) -> None:
        """
        Parameters:
            projections: node kind to its ``NodeProjection``. A kind with no entry is
                treated as under-projected, which is the safe direction: worst case is
                one extra batched request, never a missing value.
            enabled: when False nothing is recorded, for a pass that must not queue
                any more work.
            already_loaded: ids ``PeerWarmer`` has already fetched in full this run.
                Those were queried on their concrete kind with nothing excluded, so an
                attribute that is still empty is a genuine null and refetching it would
                return the same null -- at the cost of a second full resolution pass.
                Peers have no projection of their own, so without this every falsy peer
                attribute would queue a refill on every single run.
        """
        self.projections = projections or {}
        self.enabled = enabled
        self.already_loaded = already_loaded if already_loaded is not None else set()
        self.pending: dict[str, set[str]] = {}

    @classmethod
    def disabled(cls) -> RefillLedger:
        """A ledger that records nothing."""
        return cls(enabled=False)

    def scoped(self, projections: dict[str, Any]) -> RefillLedger:
        """A view judging nodes against one fetch's projections, sharing this ledger's pending set.

        Two node specs can answer with the same concrete kind -- a generic and one of
        its concrete kinds -- and then a single kind-keyed map cannot say which query a
        given node came from. A resolution pass takes a view scoped to the projections
        of the fetch it is walking, so an attribute *that* query never asked for is
        still recorded even where the other spec projected it, and an attribute it did
        ask for is not re-queued just because the other spec left it out. ``pending`` is
        the same object rather than a copy: every view feeds the one batched reload.
        """
        view = RefillLedger(projections=projections, enabled=self.enabled, already_loaded=self.already_loaded)
        view.pending = self.pending
        return view

    def record(self, node: Any, root_attr: str) -> None:
        """Note that ``root_attr`` came back empty on ``node``, if that is worth a reload."""
        if not self.enabled or not node.id:
            return

        if node.id in self.already_loaded:
            # Fetched in full already: the null is the answer.
            return

        projection = self.projections.get(node._schema.kind)
        if projection is not None and projection.projected(root_attr):
            # It was asked for and came back empty: the null is the answer.
            return

        self.pending.setdefault(node._schema.kind, set()).add(node.id)

    def __bool__(self) -> bool:
        return bool(self.pending)


class PeerWarmer:
    """Loads referenced peers into the store before nested resolution reads them."""

    def __init__(
        self,
        fetch: Callable[..., Any],
        store: Any,
        page_size: int = DEFAULT_PAGE_SIZE,
        on_error: Callable[[str, Exception], None] | None = None,
        order: Any = None,
    ) -> None:
        """
        Parameters:
            fetch: callable with the signature of ``InfrahubclientWrapper.fetch_nodes``.
            store: the SDK node store, used to skip peers already held in full.
            page_size: how many ids to request per round-trip.
            on_error: called with (kind, exception) when a kind fails to load. A fetch
                the wrapper's exception decorator swallowed -- ``None`` back, nothing
                raised -- is a failure to load like any other, and is reported here too
                with a stand-in error, since the real one never reached this module.
            order: the SDK ``Order`` to query peers with. Ordering is server-side work
                nobody here needs, so the caller passes ``Order(disable=True)`` for the
                same reason the host query does. Kept untyped so this module stays
                importable without the SDK.
        """
        self.fetch = fetch
        self.store = store
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self.on_error = on_error
        self.order = order
        # Ids fetched in full this run, so a ``RefillLedger`` can tell a genuine null
        # from an attribute the query never carried.
        self.loaded: set[str] = set()
        # Per-kind tallies for the raised-verbosity cost breakdown. Accumulated across
        # both warming passes (the initial one and the refill), because a peer kind can
        # legitimately appear in each.
        self.stats: dict[str, dict[str, int]] = {}

    @staticmethod
    def _nested_roots(attrs: list[str]) -> dict[str, tuple[str, ...]]:
        """Map each root that carries a dotted path to the first segment of each path.

        Roots without a dotted path resolve to a bare peer id, which needs no peer
        attributes and therefore no warming. The wanted names come back as a sorted
        tuple so they can key the verdict cache in ``collect``.
        """
        nested: dict[str, set[str]] = {}
        for attr in attrs:
            if "." not in attr:
                continue
            root, rest = attr.split(".", 1)
            nested.setdefault(root, set()).add(rest.split(".", 1)[0])
        return {root: tuple(sorted(wanted)) for root, wanted in nested.items()}

    def _is_satisfied(self, node_id: str, wanted: tuple[str, ...]) -> bool:
        """Whether the stored peer already carries everything about to be read off it.

        "Carries" means the value is not ``None``. A falsy-but-present value counts as
        carried, for the reason spelled out at the check below.
        """
        peer = self.store.get(key=node_id, raise_when_missing=False)
        if peer is None:
            return False

        schema = getattr(peer, "_schema", None)
        attribute_names = getattr(schema, "attribute_names", None)
        if attribute_names is None:
            return False
        relationship_names = getattr(schema, "relationship_names", None) or ()

        for name in wanted:
            if name in relationship_names:
                # A depth-2 path (``site.region.name``): the peer's own relationships
                # only come back populated when the peer itself is queried with
                # ``prefetch_relationships=True``, which is what ``warm`` does. The
                # inline payload the host query carries never goes that deep, so
                # calling this satisfied leaves resolution to fetch one region per
                # site -- the per-peer round-trip this module exists to avoid.
                return False
            if name not in attribute_names:
                # A special node property (display_label, hfid); resolution handles
                # those without needing an attribute value here.
                continue
            attr = getattr(peer, name, None)
            if attr is None or getattr(attr, "value", None) is None:
                # Only `None` means "never queried". `""` (like `False` and `0`) is a
                # falsy answer the server actually gave, and asking again returns the
                # same one -- so warming on it would refetch such a peer every single
                # run for a value that cannot change. `_resolve_schema_attribute` in
                # infrahub_utils draws the line in the same place, and the two have to
                # agree: it only queues a refill when the value is `None`.
                return False
        return True

    def collect(self, nodes: list[Any], attrs_by_kind: dict[str, list[str]]) -> dict[str, set[str]]:
        """Referenced peer ids that still need loading, grouped by their concrete kind.

        Parameters:
            nodes: the host nodes about to be resolved.
            attrs_by_kind: the resolution attribute list for each host kind.

        Returns:
            dict[str, set[str]]: concrete peer kind to the ids to fetch.
        """
        # The dotted paths depend on the kind, not the node, so parse them once per
        # kind instead of once per node.
        nested_by_kind = {kind: self._nested_roots(attrs) for kind, attrs in attrs_by_kind.items()}

        referenced: dict[str, set[str]] = {}
        # One peer is typically referenced by many hosts (600 devices sharing 130
        # sites), so remember each verdict rather than reading the store once per
        # reference. Keyed by the wanted names too, since two host kinds can ask for
        # different attributes through the same relationship name.
        verdicts: dict[tuple[str, tuple[str, ...]], bool] = {}

        for node in nodes:
            nested = nested_by_kind.get(node._schema.kind)
            if not nested:
                continue

            for root, wanted in nested.items():
                node_attr = getattr(node, root, None)
                if node_attr is None:
                    continue

                for peer in self._peers_of(node_attr):
                    peer_id = getattr(peer, "id", None)
                    kind = getattr(peer, "typename", None)
                    if not peer_id or not kind:
                        continue

                    key = (peer_id, wanted)
                    if key not in verdicts:
                        verdicts[key] = not self._is_satisfied(peer_id, wanted)
                    if verdicts[key]:
                        referenced.setdefault(kind, set()).add(peer_id)

        return referenced

    @staticmethod
    def _peers_of(node_attr: Any) -> list[Any]:
        """The related nodes behind a relationship, without triggering a fetch.

        An uninitialised cardinality-many relationship is left alone: its members
        are not known yet, and forcing them here would be the per-node round-trip
        this module exists to avoid.
        """
        if hasattr(node_attr, "peers"):
            if not getattr(node_attr, "initialized", False):
                return []
            return list(node_attr.peers)
        if getattr(node_attr, "id", None):
            return [node_attr]
        return []

    def warm(self, referenced: dict[str, set[str]]) -> int:
        """Load the referenced peers into the store.

        Parameters:
            referenced: concrete peer kind to the ids to fetch.

        Returns:
            int: how many fetch calls came back. A failed one lands in
                ``stats[kind]["failed"]`` instead.
        """
        calls = 0
        for kind, ids in referenced.items():
            ordered = sorted(ids)
            stat = self.stats.setdefault(kind, {"requested": 0, "batches": 0, "loaded": 0, "failed": 0})
            stat["requested"] += len(ordered)
            for start in range(0, len(ordered), self.page_size):
                chunk = ordered[start : start + self.page_size]
                try:
                    # One page per call, so `parallel` (which spends a round-trip on a
                    # count first) would only add latency here.
                    loaded = self.fetch(
                        kind=kind,
                        filters={"ids": chunk},
                        prefetch_relationships=True,
                        parallel=False,
                        order=self.order,
                    )
                    if loaded is None:
                        # None means the wrapper's exception decorator swallowed the
                        # failure. Counting it as a batch that worked would hide it.
                        stat["failed"] += 1
                        if self.on_error:
                            # The caller's per-kind warning is the only place this
                            # surfaces by name, and `on_error` promises to fire on a
                            # failure to load. There is no exception to hand over --
                            # the decorator already logged and discarded it -- so say
                            # exactly that rather than invent a traceback.
                            self.on_error(kind, RuntimeError("fetch failed, see the warning above"))
                        continue
                    calls += 1
                    stat["batches"] += 1
                    # Record the ids that came back, not the ids asked for: a peer can
                    # vanish between the host query and this one, and marking it loaded
                    # would tell RefillLedger its empty attributes are genuine nulls.
                    #
                    # Once per id, not once per return -- `warm` runs twice a run, and
                    # double-counting would push the by-kind tally past the deduplicated
                    # total the summary reports.
                    for node in loaded:
                        node_id = getattr(node, "id", None)
                        if node_id and node_id not in self.loaded:
                            self.loaded.add(node_id)
                            stat["loaded"] += 1
                except Exception as exc:
                    stat["failed"] += 1
                    if self.on_error:
                        self.on_error(kind, exc)
        return calls
