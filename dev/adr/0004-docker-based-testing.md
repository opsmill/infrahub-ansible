# ADR-0004: Docker-Based Test Execution

**Status**: Accepted
**Date**: 2026-02-25
**Source**: `.specify/memory/constitution.md` — backfilled from existing code

## Context

The collection's test suite spans three `ansible-test` modes — sanity, unit,
and integration — each with its own tooling expectations: a pinned Python
version, a built-and-installed copy of the collection on a custom
`ANSIBLE_COLLECTIONS_PATH`, and (for integration) a live Infrahub to talk to.
Running these directly on a contributor's machine is fragile: `ansible-test`
is sensitive to the Python version, the collection must be built and placed at
exactly `ansible_collections/opsmill/infrahub`, and host state leaks between
runs. CI and local runs would drift unless the environment were pinned in one
place.

## Decision

Run every test mode inside Docker, built from a single multi-stage `Dockerfile`
and orchestrated by `docker-compose.yml` and the Invoke tasks in `tasks/tests.py`.

- The `Dockerfile` defines a `base` stage (Python `${PYTHON_VER}`, `uv`, the
  virtualenv on `PATH`) and three derived targets: `sanity`, `unittests`, and
  `integration`. Each target builds the collection with `ansible-galaxy
  collection build`, installs it, switches to the collection path, and runs the
  matching `ansible-test` command.
- `docker-compose.yml` maps one service per target (`sanity`, `unit`,
  `integration`), sharing build args and threading through
  `ANSIBLE_SANITY_ARGS` / `ANSIBLE_UNIT_ARGS` / `ANSIBLE_INTEGRATION_ARGS` so
  extra `ansible-test` flags (e.g. `-vvv`) can be passed from the environment.
- `invoke tests-sanity` / `tests-unit` / `tests-integration` each run
  `docker compose up --build --force-recreate --exit-code-from <service>
  <service>` with `PYTHON_VER` taken from the Invoke config, so the task's exit
  code reflects the test result.

## Consequences

- Tests are reproducible: the same image runs locally and in CI, so "works on
  my machine" failures around Python version or collection layout disappear.
- Contributors do not manage a local `ansible_collections` tree or build step by
  hand — the image does it on every run.
- The Python version is a single build arg (`PYTHON_VER`), making it cheap to
  test against multiple interpreters.
- Running tests requires Docker; the procedure and troubleshooting live in
  [../guides/running-tests.md](../guides/running-tests.md) and the conventions in
  [../guidelines/testing.md](../guidelines/testing.md).

## Alternatives Considered

- **Run `ansible-test` directly on the host**: rejected — fragile against
  Python-version and collection-path drift, and pollutes host state between
  runs.
- **`tox` / `nox` virtualenv matrix without containers**: rejected — still
  depends on host-level interpreters and does not isolate the integration
  target's Infrahub dependency the way a container network does.
