# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Nested traversal through a relationship whose *declared* peer is a generic (issue #384).

The SDK builds a relationship's inline payload from the declared peer schema, so a
peer reached through a generic arrives carrying the generic's fields while typed by
its concrete kind (``__typename``). A nested path whose next hop exists only on the
concrete kind then has nothing to follow, and the traversal resolves empty --
silently, until ``strict: true`` plus ``keyed_groups``/``compose`` built on that path
abort the whole inventory run.

What has to hold, in both ``prefetch_relationships`` modes and at both cardinalities:

  - ``TestingDevice.site`` -> ``TestingLocationGeneric`` (one), where ``parent`` ->
    ``TestingRegion`` exists only on the concrete ``TestingSite``: ``site.parent.name``
  - ``TestingDevice.interfaces`` -> ``TestingIfaceGeneric`` (many), where ``vlan`` ->
    ``TestingVlan`` exists only on the concrete ``TestingIfaceEth``:
    ``interfaces.vlan.name``

Both shapes fail on the pre-``PeerWarmer`` resolver and pass once referenced peers are
loaded by id on their concrete kind before resolution reads them. One schema and one
dataset cover both, so this costs a single container.

Run:
  INFRAHUB_TESTING_IMAGE_VER=1.10.5 uv run --no-default-groups --group integration \
      pytest tests/integration/processor/test_generic_peer_traversal.py -m integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

pytest.importorskip("infrahub_testcontainers")

from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu
from infrahub_sdk import Config, InfrahubClientSync
from infrahub_sdk.schema.main import (
    AttributeKind,
    GenericSchema,
    NodeSchema,
    RelationshipKind,
    SchemaRoot,
)
from infrahub_sdk.schema.main import AttributeSchema as Attr
from infrahub_sdk.schema.main import RelationshipSchema as Rel
from infrahub_sdk.testing.docker import TestInfrahubDockerClient
from infrahub_testcontainers.container import PROJECT_ENV_VARIABLES

if TYPE_CHECKING:
    from collections.abc import Callable

    from infrahub_sdk.schema import SchemaLoadResponse

pytestmark = pytest.mark.integration

ADMIN_TOKEN = PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]

NAMESPACE = "Testing"
LOCATION_GENERIC = f"{NAMESPACE}LocationGeneric"
SITE = f"{NAMESPACE}Site"
REGION = f"{NAMESPACE}Region"
IFACE_GENERIC = f"{NAMESPACE}IfaceGeneric"
IFACE_ETH = f"{NAMESPACE}IfaceEth"
VLAN = f"{NAMESPACE}Vlan"
DEVICE = f"{NAMESPACE}Device"


def build_schema() -> SchemaRoot:
    """Two generics, each hiding a concrete-only relationship one hop further out."""
    location_generic = GenericSchema(
        name="LocationGeneric",
        namespace=NAMESPACE,
        # Deliberately narrower than TestingSite: no `name`, no `parent`.
        display_labels=["description__value"],
        attributes=[Attr(name="description", kind=AttributeKind.TEXT, optional=True)],
    )
    iface_generic = GenericSchema(
        name="IfaceGeneric",
        namespace=NAMESPACE,
        # Likewise narrower than TestingIfaceEth: no `name`, no `vlan`.
        display_labels=["description__value"],
        attributes=[Attr(name="description", kind=AttributeKind.TEXT, optional=True)],
    )
    region = NodeSchema(
        name="Region",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
    )
    vlan = NodeSchema(
        name="Vlan",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
    )
    site = NodeSchema(
        name="Site",
        namespace=NAMESPACE,
        inherit_from=[LOCATION_GENERIC],
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
        relationships=[
            Rel(name="parent", peer=REGION, kind=RelationshipKind.ATTRIBUTE, cardinality="one", optional=False),
        ],
    )
    iface_eth = NodeSchema(
        name="IfaceEth",
        namespace=NAMESPACE,
        inherit_from=[IFACE_GENERIC],
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
        relationships=[
            Rel(name="vlan", peer=VLAN, kind=RelationshipKind.ATTRIBUTE, cardinality="one", optional=False),
        ],
    )
    device = NodeSchema(
        name="Device",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
        relationships=[
            # Both declared against a generic, not the concrete kind: this is the shape
            # real schemas use (a device's location, an address's interface).
            Rel(
                name="site",
                peer=LOCATION_GENERIC,
                kind=RelationshipKind.ATTRIBUTE,
                cardinality="one",
                optional=False,
            ),
            Rel(name="interfaces", peer=IFACE_GENERIC, kind=RelationshipKind.ATTRIBUTE, cardinality="many"),
        ],
    )
    return SchemaRoot(
        version="1.0",
        generics=[location_generic, iface_generic],
        nodes=[region, vlan, site, iface_eth, device],
    )


class TestGenericPeerTraversal(TestInfrahubDockerClient):
    @pytest.fixture(scope="class")
    def dataset(self, client_sync: InfrahubClientSync, schema_loader: Callable[..., SchemaLoadResponse]) -> None:
        resp = schema_loader([build_schema().to_schema_dict()])
        if resp.errors:
            raise RuntimeError(f"schema load failed: {resp.errors}")

        region = client_sync.create(kind=REGION, name="region-1")
        region.save()
        site = client_sync.create(kind=SITE, name="site-a", parent=region)
        site.save()

        vlan = client_sync.create(kind=VLAN, name="vlan-10")
        vlan.save()
        ifaces = []
        for index in range(2):
            iface = client_sync.create(kind=IFACE_ETH, name=f"eth{index}", vlan=vlan)
            iface.save()
            ifaces.append(iface)

        device = client_sync.create(kind=DEVICE, name="device-01", site=site, interfaces=ifaces)
        device.save()

    def _fresh_processor(self, infrahub_port: int) -> iu.InfrahubNodesProcessor:
        """A processor with its own client, and so its own store.

        Not ``conftest.processor_for``: that shares the class-scoped ``client_sync``,
        whose store outlives a single test. The first parametrization would then leave
        fully-loaded peers behind for the second, which would pass on the leftovers
        rather than on its own fetch. A real ``ansible-inventory`` run starts cold, and
        so does each case here.

        Built through ``__new__`` for the same reason ``processor_for`` is: it skips
        ``__init__``, so no second client is created.
        """
        wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
        wrapper.client = InfrahubClientSync(
            address=f"http://localhost:{infrahub_port}",
            config=Config(api_token=ADMIN_TOKEN, timeout=60),
        )
        return iu.InfrahubNodesProcessor(client=wrapper)

    @pytest.mark.parametrize("prefetch", [False, True], ids=["prefetch-off", "prefetch-on"])
    def test_one_cardinality_nested_traversal(self, infrahub_port: int, dataset: None, prefetch: bool) -> None:
        """``site.parent.name``: the second hop exists only on the concrete peer kind."""
        processor = self._fresh_processor(infrahub_port)

        result = processor.fetch_and_process(
            nodes={DEVICE: {"include": ["name", "site.name", "site.parent.name"]}},
            prefetch_relationships=prefetch,
        )

        assert result is not None
        assert len(result) == 1
        attrs = next(iter(result.values()))

        assert attrs["name"] == "device-01"
        # `name` lives on the concrete kind, so it is already absent from the payload
        # the declared generic peer produced.
        assert attrs["site"]["name"] == "site-a"
        # ...and `parent` is the hop that has nothing to follow when the peer arrives
        # generic-shaped: this is what resolved to `{}` before.
        assert attrs["site"]["parent"].get("name") == "region-1"

    @pytest.mark.parametrize("prefetch", [False, True], ids=["prefetch-off", "prefetch-on"])
    def test_many_cardinality_nested_traversal(self, infrahub_port: int, dataset: None, prefetch: bool) -> None:
        """The same shape one cardinality out: ``interfaces.vlan.name``."""
        processor = self._fresh_processor(infrahub_port)

        result = processor.fetch_and_process(
            nodes={DEVICE: {"include": ["name", "interfaces.name", "interfaces.vlan.name"]}},
            prefetch_relationships=prefetch,
        )

        assert result is not None
        assert len(result) == 1
        attrs = next(iter(result.values()))

        assert attrs["name"] == "device-01"
        interfaces = attrs["interfaces"]
        assert len(interfaces) == 2
        assert {iface.get("name") for iface in interfaces} == {"eth0", "eth1"}
        assert all(iface.get("vlan", {}).get("name") == "vlan-10" for iface in interfaces), interfaces
