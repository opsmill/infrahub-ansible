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

# `docker compose up --wait` fails on a project holding a zero-replica service
# (docker/compose#13899), and infrahub-testcontainers ships
# INFRAHUB_TESTING_TASKMGR_BACKGROUND_SVC_REPLICAS="0". It reads os.environ ahead of its
# own defaults when it writes the project's .env (container.py), so setting this at
# import time -- before any compose project is initialised -- is what takes effect.
#
# This is the failure CI kept hitting and a developer machine did not: `up --wait`
# aborting with "dependency failed to start: container <project>-message-queue-1 is
# unhealthy". Whether it bites depends on the docker-compose version, which is why it
# showed up on the runner and not locally. `setdefault`, so an explicit override wins.
# Borrowed from infrahub-solution-ai-dc and infrahub-demo-dc, which hit the same thing.
os.environ.setdefault("INFRAHUB_TESTING_TASKMGR_BACKGROUND_SVC_REPLICAS", "1")

# The packaged defaults model a production-shaped cluster: two API replicas of four
# gunicorn workers each, two task workers, plus Neo4j, RabbitMQ, Redis, Prefect and its
# Postgres behind a load balancer. That is eight web workers before anything else, and a
# GitHub runner has four cores -- so the schema load, which is the heaviest thing these
# suites ask for, never completed. Raising its timeout to 600s did not help; the work was
# not slow, it was starved.
#
# These tests need a working Infrahub, not a cluster. One replica each, and the Prefect UI
# nobody is looking at turned off. `setdefault` throughout, so a bigger machine can put the
# cluster shape back with env vars.
#
# WEB_CONCURRENCY has to be set before `infrahub_testcontainers.container` is imported: the
# gunicorn entrypoint interpolates it at module import and freezes it. Being read from this
# module, which every integration conftest imports first, is what makes that hold.
os.environ.setdefault("INFRAHUB_TESTING_API_SERVER_COUNT", "1")
os.environ.setdefault("INFRAHUB_TESTING_TASK_WORKER_COUNT", "1")
os.environ.setdefault("INFRAHUB_TESTING_WEB_CONCURRENCY", "2")
os.environ.setdefault("INFRAHUB_TESTING_PREFECT_UI_ENABLED", "false")

# Generous on purpose. A cold runner brings up a database, a message bus, the API
# and a task worker before a schema load can converge. The budget this replaces was
# never chosen -- it was the SDK's own 120s read timeout, and that is what expired.
READY_TIMEOUT = float(os.environ.get("INFRAHUB_ANSIBLE_READY_TIMEOUT", "420"))
POLL_INTERVAL = 3.0
SCHEMA_LOAD_ATTEMPTS = 3

# `schema.load` posts with `timeout=max(120, client.default_timeout)` and Config.timeout
# defaults to 60, so the POST is capped at 120s however long the server actually needs.
# A two-core runner takes longer than that to apply a schema, which is what turned into
# "Unable to read from '.../api/schema/load?branch=main'. (timeout: 120 sec)".
#
# `default_timeout` is snapshotted at construction (client.py:139), so raising it means
# setting the attribute -- mutating `config.timeout` afterwards has no effect.
# `schema_converge_timeout` is the separate 60s budget for the convergence *poll* that
# follows, and that one is read live off the config.
SCHEMA_LOAD_TIMEOUT = int(os.environ.get("INFRAHUB_ANSIBLE_SCHEMA_LOAD_TIMEOUT", "600"))
SCHEMA_CONVERGE_TIMEOUT = int(os.environ.get("INFRAHUB_ANSIBLE_SCHEMA_CONVERGE_TIMEOUT", "300"))

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

    The budgets are raised on the client first. Retrying a call that cannot take
    longer than 120s only spends 120s three times over -- which is exactly what a
    slow runner did before the timeouts moved.
    """
    client_sync.default_timeout = max(client_sync.default_timeout, SCHEMA_LOAD_TIMEOUT)
    client_sync.config.schema_converge_timeout = max(
        client_sync.config.schema_converge_timeout, SCHEMA_CONVERGE_TIMEOUT
    )

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
