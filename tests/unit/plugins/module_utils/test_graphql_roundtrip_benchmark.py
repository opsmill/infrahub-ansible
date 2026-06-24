"""GraphQL round-trip benchmark harness (mock HTTP).

Drives the real ``InfrahubNodesProcessor.fetch_and_process`` against an
``InfrahubClientSync`` pointed at a mocked HTTP backend, and counts the GraphQL
POSTs that hit the wire. This is the deterministic "fetch as little as possible"
yardstick: assert the number of round-trips a given inventory shape produces.

This pass pins the baseline for the simplest scenario (one kind, simple
attributes, no relationships). Relationship / nested / inherited-attribute
scenarios (to qualify strategies S2-S4) build on this same harness.
"""

from __future__ import annotations

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu
from infrahub_sdk import Config, InfrahubClientSync
from infrahub_sdk.schema import NodeSchema
from infrahub_sdk.schema.main import BranchSchema

TAG_SCHEMA = {
    "name": "Tag",
    "namespace": "Builtin",
    "default_filter": "name__value",
    "attributes": [
        {"name": "name", "kind": "String", "unique": True},
        {"name": "description", "kind": "String", "optional": True},
    ],
    "relationships": [],
}


def _graphql_posts(httpx_mock) -> list:
    return [r for r in httpx_mock.get_requests() if r.method == "POST" and "/graphql" in str(r.url)]


@pytest.fixture
def processor():
    """A processor wired to a mock-HTTP client with the BuiltinTag schema pre-cached."""
    client = InfrahubClientSync(config=Config(address="http://mock", insert_tracker=True))
    tag_api = NodeSchema(**TAG_SCHEMA).convert_api()
    client.schema.cache["main"] = BranchSchema(hash="benchmark", nodes={tag_api.kind: tag_api})

    wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
    wrapper.client = client
    return iu.InfrahubNodesProcessor(client=wrapper)


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_single_kind_simple_attrs_roundtrips(processor, httpx_mock):
    """One kind, two populated simple attributes, no relationships → baseline round-trips."""
    httpx_mock.add_response(
        method="POST",
        json={
            "data": {
                "BuiltinTag": {
                    "count": 1,
                    "edges": [
                        {
                            "node": {
                                "id": "tag-1",
                                "__typename": "BuiltinTag",
                                "display_label": "blue",
                                "name": {"value": "blue", "is_default": False},
                                "description": {"value": "a colour", "is_default": False},
                            }
                        }
                    ],
                }
            }
        },
        is_reusable=True,
    )

    result = processor.fetch_and_process(nodes={"BuiltinTag": {}})

    # Correctness: the one tag resolved with its populated attributes.
    assert result is not None
    [attrs] = list(result.values())
    assert attrs["name"] == "blue"
    assert attrs["description"] == "a colour"
    assert attrs["id"] == "tag-1"

    # Baseline round-trip count for this shape. No schema fetch (pre-cached) and no
    # per-attribute refetch (both attributes are populated), so the only POSTs are
    # the bulk node query (count + page under parallel fetch).
    posts = _graphql_posts(httpx_mock)
    assert len(posts) == 2
