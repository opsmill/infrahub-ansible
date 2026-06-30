# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Minimal self-contained schema for the module integration tests.

A single ``TestingThing`` kind (unique ``name`` + optional ``description``) is
enough to exercise the node module's create / update / idempotent / delete and
check-mode behaviour without pulling in relationships.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from infrahub_sdk.schema.main import AttributeKind, NodeSchema, SchemaRoot
from infrahub_sdk.schema.main import AttributeSchema as Attr

if TYPE_CHECKING:
    from infrahub_sdk import InfrahubClientSync

NAMESPACE = "Testing"
THING = f"{NAMESPACE}Thing"


def build_schema() -> SchemaRoot:
    thing = NodeSchema(
        name="Thing",
        namespace=NAMESPACE,
        default_filter="name__value",
        human_friendly_id=["name__value"],
        display_labels=["name__value"],
        attributes=[
            Attr(name="name", kind=AttributeKind.TEXT, unique=True),
            Attr(name="description", kind=AttributeKind.TEXT, optional=True),
        ],
    )
    return SchemaRoot(version="1.0", nodes=[thing])


def load_schema(client: InfrahubClientSync, branch: str | None = None) -> None:
    """Load the TestingThing schema (on ``branch`` if given, else default)."""
    kwargs = {"branch": branch} if branch else {}
    resp = client.schema.load(schemas=[build_schema().to_schema_dict()], wait_until_converged=True, **kwargs)
    if resp.errors:
        raise RuntimeError(f"schema load failed: {resp.errors}")
