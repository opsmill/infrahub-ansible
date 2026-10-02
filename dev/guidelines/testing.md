# Testing Guidelines

## Test Types

This collection supports three types of tests, each running in Docker via `docker-compose.yml`:

| Type | Target | What it tests |
|------|--------|---------------|
| Sanity | `sanity` | Ansible module standards, Python compatibility, import checks |
| Unit | `unit` | Individual functions/classes with mocked dependencies |
| Integration | `integration` | End-to-end against a running Infrahub instance |

## Running Tests

### Via invoke (Recommended)

```bash
# Run all tests
invoke tests-all

# Run individual test types
invoke tests-sanity
invoke tests-unit
invoke tests-integration
```

### Via Docker Compose Directly

```bash
# Sanity tests
docker compose up --build --force-recreate --quiet-pull --exit-code-from sanity sanity

# Unit tests
docker compose up --build --force-recreate --quiet-pull --exit-code-from unit unit

# Integration tests
docker compose up --build --force-recreate --quiet-pull --exit-code-from integration integration
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `PYTHON_VER` | Python version for Docker build | `3.12` |
| `ANSIBLE_SANITY_ARGS` | Extra args for `ansible-test sanity` | empty |
| `ANSIBLE_UNIT_ARGS` | Extra args for unit tests | empty |
| `ANSIBLE_INTEGRATION_ARGS` | Extra args for integration tests | empty |

## Docker Build Stages

The `Dockerfile` uses multi-stage builds:

1. **`base`** — Installs Python, uv, and all dependencies
2. **`sanity`** — Builds the collection, installs it, runs `ansible-test sanity`
3. **`unittests`** — Runs unit tests
4. **`integration`** — Runs integration tests (with network access for Infrahub)

## Sanity Tests

Sanity tests use `ansible-test sanity` which checks:

- Module documentation format
- Python import correctness
- Required boilerplate (`__metaclass__ = type`, `__future__` imports)
- Plugin interface compliance

The `pep8` test is skipped (Ruff handles this).

```dockerfile
RUN ansible-test sanity $ANSIBLE_SANITY_ARGS \
    --requirements \
    --skip-test pep8 \
    --python ${PYTHON_VERSION} \
    plugins/
```

## Writing Unit Tests

### Directory Structure

```text
tests/
  unit/
    plugins/
      module_utils/
        test_infrahub_utils.py
      modules/
        test_node.py
```

### Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

### Mocking the SDK

Since tests run without an Infrahub instance, mock the SDK client:

```python
from unittest.mock import MagicMock, patch


@patch("ansible_collections.opsmill.infrahub.plugins.module_utils.infrahub_utils.InfrahubClientSync")
def test_wrapper_creation(mock_client_class):
    mock_client_class.return_value = MagicMock()
    wrapper = InfrahubclientWrapper(
        api_endpoint="https://infrahub.example.com",
        token="test-token",
        branch="main",
        timeout=10,
        validate_certs=True,
        display=MagicMock(),
    )
    assert wrapper.client is not None
```

### Testing Modules

Use `ansible.module_utils.basic.AnsibleModule` with mocked `exit_json` and `fail_json`:

```python
from unittest.mock import patch, MagicMock


def test_node_module_create():
    mock_module = MagicMock()
    mock_module.params = {
        "api_endpoint": "https://infrahub.example.com",
        "token": "test",
        "state": "present",
        "kind": "BuiltinTag",
        "data": {"name": "test-tag"},
        "branch": "main",
    }
    # ... setup mocks and assert behavior
```

### Dev Dependencies for Testing

```toml
pytest = "^9.0.2"
pytest-mock = "*"
pytest-xdist = "*"        # Parallel test execution
pytest-pythonpath = "*"    # pythonpath support
mock = "^5.2.0"
```

## Integration Tests

Integration tests require a running Infrahub instance. They use the `integration_network` Docker network to communicate.

### Directory Structure

```text
tests/
  integration/
    targets/
      <test_name>/
        tasks/
          main.yml
```

Integration tests are Ansible playbooks that exercise the full module → API path.

There is a second kind. `tests/integration/processor/` and `tests/integration/inventory/` use pytest
against a real Infrahub started by the SDK's testcontainers helper. They need their own dependency group
and a handful of flags — see
[../guides/running-tests.md](../guides/running-tests.md) for the exact invocation and why each flag is
required.

## Practices Worth Following

These come from defects that reached a branch and were caught late, not from theory.

### Verify a new test by collection, not by the pass count

A test method attached to the wrong class still leaves a green suite — the count simply goes down by
one, which nobody notices. After adding or moving a test, confirm the runner can see it:

```bash
uv run pytest tests/unit --collect-only -q | grep <your_test_name>
```

"N passed" answers whether the tests that ran succeeded. It does not answer whether your test ran.

### Mutation-check a test that claims to protect a behaviour

Before writing "this test guards X" in a docstring, disable X and confirm the test fails. A test can
pass for reasons unrelated to the thing it names — in this collection an integration test asserting that
peer warming resolved a generic-peer attribute passed with warming disabled, because a separate refill
path recovered the value. The docstring was the defect, not the code.

### Re-verify remembered facts against the code

Notes carried between sessions go stale. A refetch path recorded as "dead code, does not fire" turned
out to fire once per node — 653 times on a 652-device estate — and was the only thing resolving
attributes declared through a generic peer. Removing it on the strength of the note would have silently
emptied those attributes. Confirm behaviour by instrumenting or testing it before acting on a memory.

### Derive round-trip budgets, do not hardcode them

Integration tests that assert a request count share a container and accumulate data, so a fixed ceiling
quietly stops meaning anything. Compute the budget from `pagination_size` and the actual result size,
and record which SDK and image version a measured budget came from.

## CI Pipeline

Tests run on every PR to `develop`:

1. **Linter job** — Ruff check + format, **mypy**, yamllint, rumdl, Vale
2. **Ansible linter and tests job** — ansible-lint, sanity tests, unit tests

`invoke lint` covers ruff, mypy, yamllint, and rumdl, so it matches what the linter job checks
(bar Vale).

The CI workflow is in `.github/workflows/trigger-pr-develop.yml`.
