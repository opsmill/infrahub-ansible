"""Pytest configuration and shared helpers for the processor integration tests.

The collection-path and readiness handling lives in ``_harness`` so all three
integration suites share one copy of it; see that module for why either is needed.
The two suites in this directory share the processor factory and the round-trip
counter from here so they cannot drift apart.
"""

from __future__ import annotations

import contextlib
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from infrahub_sdk import InfrahubClientSync

# This directory is not a package, so pytest inserts *it* rather than its parent --
# `_harness` has to be found explicitly.
_INTEGRATION_ROOT = str(Path(__file__).resolve().parent.parent)
if _INTEGRATION_ROOT not in sys.path:
    sys.path.insert(0, _INTEGRATION_ROOT)

from _harness import infrahub_ready, install_collection_path, schema_loader

__all__ = ["count_graphql", "infrahub_ready", "processor_for", "schema_loader"]

install_collection_path()


def processor_for(client_sync: InfrahubClientSync):
    """Wrap a live client in the collection's processor without re-authenticating.

    Built through ``__new__`` on purpose: that skips ``__init__``, so no second
    client is created and the wrapper's exception decorator is *not* installed.
    ``test_unknown_kind_is_skipped_not_fatal`` depends on that -- the skip has to come
    from the schema lookup itself, not from the decorator happening to swallow.
    """
    from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu

    wrapper = iu.InfrahubclientWrapper.__new__(iu.InfrahubclientWrapper)
    wrapper.client = client_sync
    return iu.InfrahubNodesProcessor(client=wrapper)


@contextlib.contextmanager
def count_graphql(client: InfrahubClientSync) -> Iterator[Counter[str]]:
    """Count GraphQL round-trips by query tracker while inside the block.

    Shared by both processor suites so the two cannot drift: the measurement suite
    pins the per-shape budgets, the lighter suite guards the floor.

    Neither runs on a pull request -- ``integration-testcontainers`` is gated on
    ``schedule``/``workflow_dispatch`` in ``workflow-ansible-linter-and-tests.yml`` --
    so a regression these catch surfaces on the nightly build, not in PR checks.
    """
    trackers: Counter[str] = Counter()
    original = client.execute_graphql

    def wrapper(*args, **kwargs):
        trackers[kwargs.get("tracker") or "untracked"] += 1
        return original(*args, **kwargs)

    client.execute_graphql = wrapper
    try:
        yield trackers
    finally:
        client.execute_graphql = original
