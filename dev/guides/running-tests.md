# Running Tests

## Quick Reference

```bash
# All tests (sanity + unit + integration)
invoke tests-all

# Individual test types
invoke tests-sanity
invoke tests-unit
invoke tests-integration
```

## Prerequisites

- Docker and Docker Compose installed
- Poetry environment set up (`poetry install`)
- Invoke available (`pip install invoke` or via Poetry)

## How It Works

All tests run inside Docker containers. The `invoke` tasks wrap `docker compose` commands:

```
invoke tests-sanity
  → docker compose up --build --force-recreate --quiet-pull --exit-code-from sanity sanity
    → Dockerfile (base stage → sanity stage)
      → ansible-galaxy collection build + install
      → ansible-test sanity --skip-test pep8 --python 3.12 plugins/
```

### Docker Compose Services

| Service | Dockerfile Target | What it runs |
|---------|-------------------|-------------|
| `sanity` | `sanity` | `ansible-test sanity` against installed collection |
| `unit` | `unittests` | Unit test suite |
| `integration` | `integration` | Integration tests (with network access) |

## Sanity Tests

Sanity tests validate that modules conform to Ansible standards:

```bash
invoke tests-sanity
```

What `ansible-test sanity` checks:
- Module documentation format and completeness
- Python import correctness
- Required boilerplate (`__metaclass__ = type`)
- Plugin interface compliance
- Compile checks across Python versions

The `pep8` sanity test is skipped — Ruff handles style checking.

### Fixing Sanity Failures

Common issues:
- Missing `__metaclass__ = type` → add to top of file
- Missing `from __future__ import` → add the standard import line
- Documentation format errors → check YAML syntax in `DOCUMENTATION` string
- Import errors → ensure conditional imports for `infrahub-sdk`

## Unit Tests

```bash
invoke tests-unit
```

Unit tests live in `tests/unit/` and use `pytest` with mocking.

### Running Specific Tests Locally

For faster iteration, you can run pytest directly (requires the Poetry environment):

```bash
# All unit tests
poetry run pytest tests/unit/

# Specific test file
poetry run pytest tests/unit/plugins/modules/test_node.py

# Specific test with verbose output
poetry run pytest tests/unit/plugins/modules/test_node.py::test_create -v

# With parallel execution
poetry run pytest tests/unit/ -n auto
```

### Pytest Configuration

From `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
```

## Integration Tests

```bash
invoke tests-integration
```

Integration tests require a running Infrahub instance. The `integration` Docker service uses the `integration_network` to reach Infrahub.

Integration tests use Ansible playbooks in `tests/integration/targets/`.

## Linting (Not Tests, But Related)

```bash
# Run all linters (ruff + yamllint)
invoke lint

# Auto-fix formatting
invoke format
```

## Changing Python Version

The default Python version is `3.12` (configured in `tasks/__init__.py`). To test with a different version:

```bash
PYTHON_VER=3.11 docker compose up --build --exit-code-from sanity sanity
```

## Troubleshooting

### Docker Build Failures

If the Docker build fails on dependency installation:
1. Check that `poetry.lock` is up to date: `poetry lock`
2. Check for network issues (Poetry needs to download packages)

### Sanity Test Import Errors

If sanity tests fail with import errors for `infrahub_sdk`:
- This is expected in the sanity test environment
- Ensure you use the conditional import pattern (`HAS_INFRAHUBCLIENT`)
- The `infrahub-sdk` dependency is installed in the Docker image but `ansible-test` may use isolated environments

### Test Output

Docker logs and test output go to stdout. If using `--exit-code-from`, the exit code reflects the test result (0 = pass, non-zero = fail).
