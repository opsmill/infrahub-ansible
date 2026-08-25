"""Unit tests for the run-cost counter.

The counter exists so a report of "the inventory is slow" can arrive as a number.
Its correctness is unglamorous but load-bearing: an off-by-one or a silently
detached counter turns the diagnostic back into an anecdote.
"""

from __future__ import annotations

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
    # The count is the only state. Anything else here would be a retained response.
    assert list(vars(counter)) == ["responses"]


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
