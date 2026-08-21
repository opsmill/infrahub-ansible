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

    def __init__(self, projections: dict[str, Any] | None = None, enabled: bool = True) -> None:
        """
        Parameters:
            projections: node kind to its ``NodeProjection``. A kind with no entry is
                treated as under-projected, which is the safe direction: worst case is
                one extra batched request, never a missing value.
            enabled: when False nothing is recorded, for a pass that must not queue
                any more work.
        """
        self.projections = projections or {}
        self.enabled = enabled
        self.pending: dict[str, set[str]] = {}

    @classmethod
    def disabled(cls) -> RefillLedger:
        """A ledger that records nothing."""
        return cls(enabled=False)

    def record(self, node: Any, root_attr: str) -> None:
        """Note that ``root_attr`` came back empty on ``node``, if that is worth a reload."""
        if not self.enabled or not node.id:
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
    ) -> None:
        """
        Parameters:
            fetch: callable with the signature of ``InfrahubclientWrapper.fetch_nodes``.
            store: the SDK node store, used to skip peers already held in full.
            page_size: how many ids to request per round-trip.
            on_error: called with (kind, exception) when a kind fails to load.
        """
        self.fetch = fetch
        self.store = store
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self.on_error = on_error

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
        """Whether the stored peer already carries every attribute about to be read."""
        peer = self.store.get(key=node_id, raise_when_missing=False)
        if peer is None:
            return False

        schema = getattr(peer, "_schema", None)
        attribute_names = getattr(schema, "attribute_names", None)
        if attribute_names is None:
            return False

        for name in wanted:
            if name not in attribute_names:
                # A relationship or a special property; resolution handles those
                # without needing an attribute value here.
                continue
            attr = getattr(peer, name, None)
            if attr is None or getattr(attr, "value", None) in (None, ""):
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
            int: how many fetch calls were issued.
        """
        calls = 0
        for kind, ids in referenced.items():
            ordered = sorted(ids)
            for start in range(0, len(ordered), self.page_size):
                chunk = ordered[start : start + self.page_size]
                try:
                    # One page per call, so `parallel` (which spends a round-trip on a
                    # count first) would only add latency here.
                    self.fetch(
                        kind=kind,
                        filters={"ids": chunk},
                        prefetch_relationships=True,
                        parallel=False,
                    )
                    calls += 1
                except Exception as exc:
                    if self.on_error:
                        self.on_error(kind, exc)
        return calls
