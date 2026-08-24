# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Regression test for issue #384: nested traversal through a generic peer.

When a relationship's declared peer is a generic, the SDK caches the peer typed
by its concrete kind (``__typename``) but shaped by the generic's fields, so a
concrete-only relationship (``parent``) used to resolve empty from the store.

Schema shape (mirrors the issue):
  - TestingLocationGeneric (generic) — has neither ``name`` nor ``parent``
  - TestingSite (inherits the generic) — has ``name`` and ``parent`` -> TestingRegion
  - TestingDevice.site — declared peer is the *generic*

Expectation under test: ``site.parent.name`` resolves, identically with
``prefetch_relationships`` True and False.

Run:
  INFRAHUB_TESTING_IMAGE_VER=1.10.5 uv run --no-group dev --group integration \
      pytest tests/integration/processor/test_generic_peer_traversal.py -m integration
"""

from __future__ import annotations

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

pytestmark = pytest.mark.integration

ADMIN_TOKEN = PROJECT_ENV_VARIABLES["INFRAHUB_TESTING_INITIAL_ADMIN_TOKEN"]

NAMESPACE = "Testing"
LOCATION_GENERIC = f"{NAMESPACE}LocationGeneric"
SITE = f"{NAMESPACE}Site"
REGION = f"{NAMESPACE}Region"
DEVICE = f"{NAMESPACE}Device"


def build_schema() -> SchemaRoot:
    location_generic = GenericSchema(
        name="LocationGeneric",
        namespace=NAMESPACE,
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
    device = NodeSchema(
        name="Device",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[Attr(name="name", kind=AttributeKind.TEXT, unique=True)],
        relationships=[
            Rel(name="site", peer=LOCATION_GENERIC, kind=RelationshipKind.ATTRIBUTE, cardinality="one", optional=False),
        ],
    )
    return SchemaRoot(version="1.0", generics=[location_generic], nodes=[region, site, device])


class TestIssue384GenericPeerTraversal(TestInfrahubDockerClient):
    @pytest.fixture(scope="class")
    def dataset(self, client_sync: InfrahubClientSync) -> None:
        resp = client_sync.schema.load(schemas=[build_schema().to_schema_dict()], wait_until_converged=True)
        if resp.errors:
            raise RuntimeError(f"schema load failed: {resp.errors}")

        region = client_sync.create(kind=REGION, name="region-1")
        region.save()
        site = client_sync.create(kind=SITE, name="site-a", parent=region)
        site.save()
        device = client_sync.create(kind=DEVICE, name="device-01", site=site)
        device.save()

    def _fresh_processor(self, infrahub_port: int) -> iu.InfrahubNodesProcessor:
        """A processor with its own client/store, like each real ansible-inventory run."""
        wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
        wrapper.client = InfrahubClientSync(
            address=f"http://localhost:{infrahub_port}",
            config=Config(api_token=ADMIN_TOKEN, timeout=60),
        )
        return iu.InfrahubNodesProcessor(client=wrapper)

    @pytest.mark.parametrize("prefetch", [False, True], ids=["prefetch-off", "prefetch-on"])
    def test_nested_traversal_through_generic_peer(self, infrahub_port: int, dataset: None, prefetch: bool) -> None:
        processor = self._fresh_processor(infrahub_port)

        result = processor.fetch_and_process(
            nodes={DEVICE: {"include": ["name", "site.name", "site.parent.name"]}},
            prefetch_relationships=prefetch,
        )

        assert result is not None
        assert len(result) == 1
        attrs = next(iter(result.values()))

        assert attrs["name"] == "device-01"
        assert attrs["site"]["name"] == "site-a"
        assert attrs["site"]["parent"].get("name") == "region-1"
