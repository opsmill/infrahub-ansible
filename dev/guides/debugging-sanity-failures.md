# Debugging ansible-test sanity Failures

`ansible-test sanity` is the gate that enforces Ansible's plugin conventions. It
runs in Docker, so it reproduces the CI environment exactly. This guide covers
how to run it, the failures you will hit most, and how to read its output. For
the test mechanics and the full test matrix, see
[running-tests.md](running-tests.md) and
[../guidelines/testing.md](../guidelines/testing.md).

## Reproduce Locally

```bash
invoke tests-sanity
```

This builds the collection and runs `ansible-test sanity --skip-test pep8
--python <ver> plugins/` inside the `sanity` Docker service (`pep8` is skipped
because Ruff owns style). The container exits non-zero on the first failing
test, and the failing test names and file/line references print to stdout.

## The Common Failures

### Missing boilerplate

Sanity requires every plugin file to start with the Python 2/3 compatibility
headers, even though the collection targets Python 3.10+:

```python
from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type
```

A missing `__metaclass__ = type` or `__future__` line is the most frequent
failure. Add them at the very top, after the copyright header.

### Unguarded SDK import

The SDK must be imported conditionally so `ansible-doc` and sanity can parse a
file without `infrahub-sdk` installed. Import inside `try/except ImportError`,
set `HAS_INFRAHUBCLIENT`, and check it at runtime before any SDK use — the
pattern lives in `plugins/module_utils/infrahub_utils.py` and is detailed in
[../knowledge/plugin-patterns.md](../knowledge/plugin-patterns.md). A bare
top-level `from infrahub_sdk import ...` will surface as an import error in the
isolated sanity environment.

### Docstring / arg-spec mismatch

The `validate-modules` sanity test compares each option in `DOCUMENTATION`
against the module's `argument_spec`. Mismatches — an option documented but not
in the spec (or vice versa), a wrong `type`, or a `required`/`default`
disagreement — fail here. Keep the two in sync; when options come from a doc
fragment, the fragment's YAML must match the spec too. See
[../guidelines/module-docstrings.md](../guidelines/module-docstrings.md).

## Reading the Output

Each failure prints as `<test-name>: <path>:<line>: <message>`. Work from the
top — a parse or boilerplate error early in a file can cascade into later
complaints. After a fix, rerun `invoke tests-sanity`; the rebuild is cached, so
iteration is fast.

If sanity reports an `infrahub_sdk` import error specifically, that is expected
in the isolated environment and means the conditional-import guard is missing or
incomplete, not that a dependency is absent — see the troubleshooting notes in
[running-tests.md](running-tests.md).
