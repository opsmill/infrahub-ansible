"""Unit tests for the run-cost counter.

The counter exists so a report of "the inventory is slow" can arrive as a number.
Its correctness is unglamorous but load-bearing: an off-by-one or a silently
detached counter turns the diagnostic back into an anecdote.
"""

from __future__ import annotations

import sys
import threading
from types import SimpleNamespace

from ansible_collections.opsmill.infrahub.plugins.module_utils import metrics


def test_counter_starts_at_zero():
    assert metrics.RequestCounter().responses == 0


def test_counter_increments_once_per_response():
    counter = metrics.RequestCounter()
    for _response in range(3):
        counter.record(response=None)
    assert counter.responses == 3


def test_counter_ignores_the_response_it_is_given():
    """The response is not retained -- the counter must not hold request bodies.

    Recording is called for every response the SDK receives, tokens and payloads
    included. Keeping any of it would put credentials in whatever holds the counter.
    """
    counter = metrics.RequestCounter()
    counter.record(response=SimpleNamespace(content=b"secret", status_code=200))
    assert counter.responses == 1
    # The count and the lock guarding it are the only state. Anything else appearing
    # here would be a retained response.
    assert sorted(vars(counter)) == ["_lock", "responses"]


def test_module_has_no_runtime_sdk_dependency():
    """Plugin files must import without ``infrahub-sdk`` installed.

    ``httpx`` appears only in an annotation, under ``TYPE_CHECKING``, so it must not
    be bound at module level. If someone later moves that import out of the guard,
    ``ansible-test sanity`` fails on a machine without the SDK -- this catches it first.
    """
    assert "httpx" not in vars(metrics)
    assert "infrahub_sdk" not in vars(metrics)


def test_request_count_reads_an_attached_counter():
    counter = metrics.RequestCounter()
    counter.record(response=None)
    assert metrics.request_count(SimpleNamespace(request_counter=counter)) == 1


def test_request_count_is_none_when_no_counter_is_attached():
    """A wrapper built through ``__new__`` has no counter, and that is not an error.

    The integration tests build one that way to skip re-authenticating. Reporting has
    to degrade to "unavailable" rather than raising, or a diagnostic breaks the run
    it was added to diagnose.
    """
    assert metrics.request_count(SimpleNamespace()) is None


def test_request_count_rejects_a_non_integer_counter():
    """A MagicMock auto-attribute answers to ``.responses`` with another mock.

    Without the type check that mock would be reported as a request count, so every
    mock-based test would print a nonsense number and nobody would notice.
    """
    assert metrics.request_count(SimpleNamespace(request_counter=SimpleNamespace(responses="lots"))) is None


def test_counter_totals_correctly_when_pages_are_recorded_concurrently():
    """Recording from many threads must yield the exact total.

    Parallel paging runs pages through ``InfrahubBatchSync``, a ``ThreadPoolExecutor``,
    and the collection asks for parallel paging by default -- so ``record`` really is
    called concurrently.

    This pins the guarantee, not a reproduction: on a GIL build the unlocked ``+= 1``
    could not be made to lose a count even at 32 threads and a nanosecond switch
    interval, so this passes with or without the lock today. It is the free-threaded
    builds in this project's supported range (3.13t, 3.14) where the lock is what
    keeps this green, and the interpreter this runs on is not the assertion's business.
    """
    counter = metrics.RequestCounter()
    threads = 8
    per_thread = 2000
    start = threading.Barrier(threads)

    def record_many():
        start.wait()
        for _response in range(per_thread):
            counter.record(response=None)

    original_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        workers = [threading.Thread(target=record_many) for _worker in range(threads)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
    finally:
        sys.setswitchinterval(original_interval)

    assert counter.responses == threads * per_thread
