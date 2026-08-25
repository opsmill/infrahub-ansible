# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Shared setup every integration suite needs before it can touch Infrahub.

Two things are not true just because ``docker compose up`` returned, and each
suite used to discover that for itself.

``ansible-playbook`` and ``ansible-inventory`` resolve ``opsmill.infrahub``
through ansible's collection loader, which insists the collection sit at
``<root>/ansible_collections/opsmill/infrahub``. A developer checkout already is
that shape, so walking up for an ancestor containing ``ansible_collections``
found one. A CI checkout is a plain directory -- nothing to find, the variable
never got set, and every playbook died on ``No module named
'ansible_collections.opsmill'``. When there is nothing to find, one is built out
of symlinks instead.

And the stack has to answer. ``compose.start()`` returns once the ports are open,
which is minutes before the API serves and the task worker can reach it. Every
suite here opens with a schema load or a branch create -- the two operations that
need both -- so they raced the stack and lost, and the failure surfaced as the
SDK's read timeout rather than as "not up yet".
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

    from infrahub_sdk import InfrahubClientSync
    from infrahub_sdk.schema import SchemaLoadResponse

COLLECTION_PATH = ("ansible_collections", "opsmill", "infrahub")

# Generous on purpose. A cold runner brings up a database, a message bus, the API
# and a task worker before a schema load can converge. The budget this replaces was
# never chosen -- it was the SDK's own 120s read timeout, and that is what expired.
READY_TIMEOUT = float(os.environ.get("INFRAHUB_ANSIBLE_READY_TIMEOUT", "420"))
POLL_INTERVAL = 3.0
SCHEMA_LOAD_ATTEMPTS = 3

_ROOT: Path | None = None


def _staged_collection_root() -> Path:
    """Build ``<tmp>/ansible_collections/opsmill/infrahub`` pointing at this checkout.

    Staged outside the repo deliberately: a link planted inside it would point at
    one of its own ancestors, and the collection loader walking the tree would
    descend through the checkout into itself.
    """
    repo_root = Path(__file__).resolve().parents[2]
    staging = Path(tempfile.mkdtemp(prefix="infrahub-ansible-collection-"))
    link = staging.joinpath(*COLLECTION_PATH)
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(repo_root, target_is_directory=True)
    return staging


def collection_root() -> Path:
    """The directory ansible should treat as its collections path."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "ansible_collections").is_dir():
            return parent
    return _staged_collection_root()


def install_collection_path() -> Path:
    """Make the collection importable by Python and findable by ansible.

    Idempotent, and safe to call from every suite's ``conftest``: the plugin's
    absolute imports need the root on ``sys.path``, and the ``ansible-playbook``
    and ``ansible-inventory`` subprocesses need it on ``ANSIBLE_COLLECTIONS_PATH``.
    """
    global _ROOT  # noqa: PLW0603 -- one staged tree per session, not one per caller
    if _ROOT is None:
        _ROOT = collection_root()
    root = str(_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    existing = os.environ.get("ANSIBLE_COLLECTIONS_PATH", "")
    if root not in existing.split(os.pathsep):
        os.environ["ANSIBLE_COLLECTIONS_PATH"] = os.pathsep.join(p for p in (root, existing) if p)
    return _ROOT


def wait_until_serving(client: InfrahubClientSync, timeout: float = READY_TIMEOUT) -> None:
    """Block until the stack answers a real query, and say what it last failed with.

    ``branch.all()`` is the cheapest call that proves the API and GraphQL are both
    live. Any exception means "not yet" -- a refused connection, a read timeout, a
    half-started server answering 500 -- so none of them are worth telling apart.
    """
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client.branch.all()
        except Exception as exc:  # anything at all means "not yet"
            last = exc
            time.sleep(POLL_INTERVAL)
        else:
            return
    raise TimeoutError(f"Infrahub was still not serving after {timeout:.0f}s; last error: {last!r}")


@pytest.fixture(scope="class")
def infrahub_ready(client_sync: InfrahubClientSync) -> None:
    """Gate a suite's first heavy call on the stack being up, not merely listening."""
    wait_until_serving(client_sync)


@pytest.fixture(scope="class")
def schema_loader(client_sync: InfrahubClientSync, infrahub_ready: None) -> Callable[..., SchemaLoadResponse]:
    """A ``schema.load`` that tolerates a stack still settling.

    Converging a schema needs the task worker, which comes up behind the API, so a
    load can time out while nothing is actually wrong with the schema. Retried
    against a fresh readiness check rather than failing the suite on the first
    timeout; a schema that is genuinely bad still fails, just three attempts later.
    """

    def load(schemas: list[dict], **kwargs: str) -> SchemaLoadResponse:
        for attempt in range(1, SCHEMA_LOAD_ATTEMPTS + 1):
            try:
                return client_sync.schema.load(schemas=schemas, wait_until_converged=True, **kwargs)
            except Exception:  # retry any transport-level refusal
                if attempt == SCHEMA_LOAD_ATTEMPTS:
                    raise
                wait_until_serving(client_sync)
        raise AssertionError("unreachable")  # pragma: no cover

    return load
