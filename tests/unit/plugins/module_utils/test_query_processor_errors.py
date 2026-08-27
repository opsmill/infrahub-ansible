# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""What ``InfrahubQueryProcessor.fetch_and_process`` says when a query does not work.

This is the lookup plugin's only error surface: ``lookup.py`` catches whatever comes
out of here and re-raises it as ``AnsibleError(str(exc))``, so a message that names
only the query is the whole of what a playbook author sees.

Two distinct failures reach this code, and they need different messages:

* ``execute_graphql`` raised -- the cause is the exception.
* ``execute_graphql`` returned ``None`` -- the wrapper's exception decorator logs and
  swallows whenever a ``Display`` is attached, which every plugin does, so a failed
  call arrives here as an empty return with the detail already in a warning.
"""

from __future__ import annotations

import pytest
from ansible_collections.opsmill.infrahub.plugins.module_utils import infrahub_utils as iu

QUERY = {"ZoneBNG": {"edges": {"node": {"name": {"value": None}}}}}


def _processor(mocker, *, side_effect=None, return_value=None):
    """A query processor whose ``execute_graphql`` behaves as the test asks."""
    wrapper = mocker.MagicMock()
    wrapper._render_query.return_value = "query { ZoneBNG { edges { node { name { value } } } } }"
    wrapper.execute_graphql.side_effect = side_effect
    if side_effect is None:
        wrapper.execute_graphql.return_value = return_value
    return iu.InfrahubQueryProcessor(client=wrapper)


def test_raised_failure_keeps_its_cause_and_message(mocker):
    """A GraphQL/transport failure survives to the caller instead of being replaced.

    The old code caught bare ``Exception`` and re-raised a message built only from the
    query, so the status code, the GraphQL error list or the timeout that actually
    explained the failure never reached the playbook.
    """
    original = RuntimeError("Server returned HTTP 502")
    processor = _processor(mocker, side_effect=original)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    # The cause is chained, so `-vvv` and any traceback still reach the real error.
    assert excinfo.value.__cause__ is original
    # And it is legible without a traceback, which is all AnsibleError(str(exc)) shows.
    assert "Server returned HTTP 502" in str(excinfo.value)
    assert "RuntimeError" in str(excinfo.value)


def test_empty_response_says_the_call_failed_not_that_the_query_is_bad(mocker):
    """``None`` back means the decorator swallowed a failure, and the message says so.

    ``handle_infrahub_exceptions`` turns a ``GraphQLError`` into ``display.warning``
    and returns ``None`` whenever a ``Display`` is attached. Reporting that as a bad
    query sent people looking at their query text for a server-side problem.
    """
    processor = _processor(mocker, return_value=None)

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    message = str(excinfo.value)
    assert "no response" in message.lower()
    # Points at where the detail actually is, rather than echoing the query back.
    assert "warning" in message.lower()


def test_typo_free_message(mocker):
    """The word is "GraphQL". Pinned because the old message shipped `grapqhl`."""
    processor = _processor(mocker, side_effect=RuntimeError("boom"))

    with pytest.raises(Exception) as excinfo:
        processor.fetch_and_process(query=QUERY)

    assert "grapqhl" not in str(excinfo.value)


def test_successful_query_is_returned_unchanged(mocker):
    """The happy path is untouched: a query response comes back as-is."""
    payload = {"ZoneBNG": {"edges": [{"node": {"name": {"value": "bng-01"}}}]}}
    processor = _processor(mocker, return_value=payload)

    assert processor.fetch_and_process(query=QUERY) == payload
