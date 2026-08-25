# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Translation from a user's node spec to the arguments the SDK actually honours.

The inventory plugin lets a user write ``include: [name, location.name]``. That
list is not what the SDK narrows a query with: ``generate_query_data_node``
filters attributes by ``exclude`` only, and treats ``include`` purely as an
opt-in for cardinality-many relationships that would otherwise be skipped. A
dotted path matches neither. Left untranslated, ``include`` therefore shapes the
host variables and nothing else -- the query on the wire is the same one an
empty spec produces.

``NodeProjection`` owns that translation in one place: which roots the user
asked for, which of them the SDK needs named in ``include``, and the
``exclude`` complement that actually narrows the query.
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type

from typing import Any

# Always present in the SDK's generated query regardless of include/exclude, so
# they can never be excluded and never need requesting.
ALWAYS_QUERIED = frozenset({"id", "hfid", "display_label"})

# Hierarchical kinds (Location, Organization, IPAM prefixes -- the ones an inventory
# actually queries) carry four synthetic fields the SDK adds to every query whenever
# `prefetch_relationships` is on. They are pseudo-schemas, so they are absent from
# `relationship_names` and the exclude complement below never reaches them: a narrowed
# query would still drag both full hierarchies down on every page. Naming them costs
# nothing on a kind that has none -- the SDK only ever tests membership in `exclude`.
HIERARCHICAL_FIELDS = frozenset({"parent", "children", "ancestors", "descendants"})


class NodeProjection:
    """What to fetch for one node kind, and what to resolve out of it.

    An explicit ``exclude`` wins over ``include``, and this class is what makes that
    true: the SDK does not arbitrate between them, it *rejects* the pair.
    ``generate_query_data`` raises ``ValueError("[...] are part of both include and
    exclude")`` before any per-field logic runs, and ``fetch_nodes`` swallows that
    into a failed kind -- so one overlapping name used to cost the whole inventory.
    A root named in both is therefore kept out of ``include`` here, and is neither
    fetched nor resolved.

    Attributes:
        attrs: dotted attribute paths to resolve into host variables, minus any
            path whose root the user excluded.
        roots: top-level names those paths start from.
        include: names to pass to the SDK's ``include`` (opt-in relationships).
        exclude: names to pass to the SDK's ``exclude`` (the real projection).
            A name here beats the same name in ``include``.
        narrowed: whether the user supplied an explicit ``include``.
    """

    def __init__(
        self,
        attrs: list[str],
        roots: set[str],
        include: list[str] | None,
        exclude: list[str] | None,
        narrowed: bool,
    ) -> None:
        self.attrs = attrs
        self.roots = roots
        self.include = include
        self.exclude = exclude
        self.narrowed = narrowed

    def projected(self, root_attr: str) -> bool:
        """Whether ``root_attr`` was requested from the server for this kind.

        A field that was never projected comes back empty because nobody asked
        for it, which is a different thing from the server answering null. Only
        the first case is worth a second look.

        An explicit ``exclude`` wins over ``include`` here too: a root the user
        named in both never reached the wire, so its empty value is not a null.
        ``ALWAYS_QUERIED`` still wins over everything -- the SDK puts those in
        the query whatever the caller asks for.
        """
        if root_attr in ALWAYS_QUERIED:
            return True
        if self.exclude and root_attr in self.exclude:
            return False
        if not self.narrowed:
            return True
        return root_attr in self.roots

    @classmethod
    def build(
        cls,
        schema: Any,
        include: list[str] | None,
        exclude: list[str] | None,
        resolvable_attrs: list[str],
    ) -> NodeProjection:
        """Build the projection for one kind.

        Parameters:
            schema: the node's schema (needs ``attribute_names`` and ``relationship_names``).
            include: the user's include list, dotted paths allowed.
            exclude: the user's exclude list; a name here wins over the same name
                in ``include``.
            resolvable_attrs: the attribute list to resolve when the user gave no
                ``include`` -- i.e. the collection's default view of the kind.

        Returns:
            NodeProjection: the fetch arguments and the resolution list.
        """
        if not include:
            # No explicit request: keep the historical wide query. Narrowing here
            # would change what a bare `nodes: {Kind: {}}` returns.
            return cls(
                attrs=resolvable_attrs,
                roots={attr.split(".", 1)[0] for attr in resolvable_attrs},
                include=None,
                exclude=exclude,
                narrowed=False,
            )

        roots = {attr.split(".", 1)[0] for attr in include}

        known = set(schema.attribute_names) | set(schema.relationship_names)
        # Anything the schema offers and the user did not ask for is dead weight
        # on every page of every host. Unknown roots are left alone: they are
        # either special node properties or a typo, and neither belongs in exclude.
        complement = sorted((known | HIERARCHICAL_FIELDS) - roots)

        excluded_roots = set(exclude or [])
        merged_exclude = sorted(set(complement) | excluded_roots)

        # A root the user named in both lists is dropped, not arbitrated: the SDK
        # refuses the pair outright (`ValueError: [...] are part of both include and
        # exclude`), `fetch_nodes` swallows that, and the kind is recorded as failed --
        # which for a single-kind inventory means zero hosts where the old wide query
        # returned every host with an empty value. Resolving it would be wrong anyway:
        # it would hand out an empty host variable and let the refill pass, which
        # re-fetches by id with no exclude, drag back the field the user asked to drop.
        # The whole dotted path goes with its root: `location.name` leaves when
        # `location` is excluded.
        attrs = [attr for attr in include if attr.split(".", 1)[0] not in excluded_roots]

        return cls(
            attrs=attrs,
            roots=roots,
            # `include` only ever *adds* to the query, so every requested root is safe
            # to name -- relationships the SDK would skip get opted in, plain attributes
            # are a no-op -- except one the user also excluded, which has to stay out to
            # keep the two lists disjoint.
            include=sorted((roots & known) - excluded_roots),
            exclude=merged_exclude or None,
            narrowed=True,
        )
