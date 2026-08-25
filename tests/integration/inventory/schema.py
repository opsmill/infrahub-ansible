# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Purpose-built minimal schema + seed data for the inventory integration tests.

Models a small "hosts in sites in regions" topology that exercises the inventory
plugin's features: simple attributes, one-cardinality relationships (``site``,
``primary_address``), a depth-2 path (``site.region.name``) and a many-cardinality
relationship (``tags`` -> BuiltinTag).

``Host.site`` deliberately declares its peer as the ``TestingLocation`` *generic*,
which exposes only ``shortname``, while ``name`` and ``region`` live on the
concrete ``TestingSite``. That mirrors how real schemas are shaped (a device's
``location`` declaring a location generic) and it is the case that breaks: the SDK
builds a relationship's inline payload from the *declared* peer schema, so a peer
reached this way arrives without the concrete kind's attributes. Every
``site.name`` assertion in this suite therefore also proves the plugin recovers
them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from infrahub_sdk.schema.main import AttributeKind, GenericSchema, NodeSchema, RelationshipKind, SchemaRoot
from infrahub_sdk.schema.main import AttributeSchema as Attr
from infrahub_sdk.schema.main import RelationshipSchema as Rel

if TYPE_CHECKING:
    from collections.abc import Callable

    from infrahub_sdk import InfrahubClientSync

NAMESPACE = "Testing"
HOST = f"{NAMESPACE}Host"
LOCATION = f"{NAMESPACE}Location"
SITE = f"{NAMESPACE}Site"
REGION = f"{NAMESPACE}Region"
ADDRESS = f"{NAMESPACE}IPAddress"
BUILTIN_TAG = "BuiltinTag"


def build_schema() -> SchemaRoot:
    region = NodeSchema(
        name="Region",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
    )
    location = GenericSchema(
        name="Location",
        namespace=NAMESPACE,
        # Deliberately narrower than TestingSite: no `name`, no `region`. A peer
        # reached through this generic arrives carrying only `shortname`.
        attributes=[Attr(name="shortname", kind=AttributeKind.TEXT, optional=True)],
    )
    site = NodeSchema(
        name="Site",
        namespace=NAMESPACE,
        inherit_from=[LOCATION],
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
        relationships=[
            Rel(name="region", peer=REGION, kind=RelationshipKind.ATTRIBUTE, cardinality="one", optional=False),
        ],
    )
    address = NodeSchema(
        name="IPAddress",
        namespace=NAMESPACE,
        default_filter="address__value",
        human_friendly_id=["address__value"],
        display_labels=["address__value"],
        attributes=[Attr(name="address", kind=AttributeKind.TEXT, unique=True)],
    )
    host = NodeSchema(
        name="Host",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[
            Attr(name="name", kind=AttributeKind.TEXT, unique=True),
            Attr(name="role", kind=AttributeKind.TEXT),
            Attr(name="platform", kind=AttributeKind.TEXT, optional=True),
        ],
        relationships=[
            # Declared against the generic, not TestingSite: the SDK projects a
            # relationship's inline payload off the *declared* peer, so `name` and
            # `region` do not come back with the host query and have to be recovered.
            Rel(name="site", peer=LOCATION, kind=RelationshipKind.ATTRIBUTE, cardinality="one", optional=False),
            Rel(
                name="primary_address",
                peer=ADDRESS,
                kind=RelationshipKind.ATTRIBUTE,
                cardinality="one",
                optional=True,
            ),
            Rel(name="tags", peer=BUILTIN_TAG, kind=RelationshipKind.ATTRIBUTE, cardinality="many", optional=True),
        ],
    )
    return SchemaRoot(version="1.0", generics=[location], nodes=[region, site, address, host])


# (host, role, platform, site, region, address, [tags])
HOSTS = [
    ("host-a", "edge", "ios", "paris", "emea", "10.0.0.1", ["red"]),
    ("host-b", "core", "eos", "paris", "emea", "10.0.0.2", ["blue"]),
    ("host-c", "edge", "ios", "denver", "amer", "10.0.0.3", ["red", "blue"]),
    ("host-d", "core", "nxos", "denver", "amer", "10.0.0.4", []),
]


def seed_dataset(client: InfrahubClientSync, loader: Callable[..., Any] | None = None) -> dict:
    """Load the schema and create the host topology. Idempotent enough for one container.

    ``loader`` is the retrying ``schema.load`` from the integration harness; the
    direct call is the fallback for anyone driving this outside pytest.
    """
    load = loader or (lambda schemas: client.schema.load(schemas=schemas, wait_until_converged=True))
    resp = load([build_schema().to_schema_dict()])
    if resp.errors:
        raise RuntimeError(f"schema load failed: {resp.errors}")

    regions: dict[str, object] = {}
    sites: dict[str, object] = {}
    tags: dict[str, object] = {}

    for _name, _role, _platform, site_name, region_name, _address, host_tags in HOSTS:
        if region_name not in regions:
            node = client.create(kind=REGION, name=region_name)
            node.save()
            regions[region_name] = node
        if site_name not in sites:
            node = client.create(kind=SITE, name=site_name, region=regions[region_name])
            node.save()
            sites[site_name] = node
        for tag_name in host_tags:
            if tag_name not in tags:
                node = client.create(kind=BUILTIN_TAG, name=tag_name)
                node.save()
                tags[tag_name] = node

    for name, role, platform, site_name, _region_name, address, host_tags in HOSTS:
        addr = client.create(kind=ADDRESS, address=address)
        addr.save()
        host = client.create(
            kind=HOST,
            name=name,
            role=role,
            platform=platform,
            site=sites[site_name],
            primary_address=addr,
            tags=[tags[t] for t in host_tags],
        )
        host.save()

    return {"hosts": [h[0] for h in HOSTS], "sites": sorted(sites), "regions": sorted(regions)}
