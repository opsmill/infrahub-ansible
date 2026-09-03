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
- uv environment set up (`uv sync`)
- Invoke available (`pip install invoke` or via uv)

## How It Works

All tests run inside Docker containers. The `invoke` tasks wrap `docker compose` commands:

```text
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

For faster iteration, you can run pytest directly (requires the uv environment):

```bash
# All unit tests
uv run pytest tests/unit/

# Specific test file
uv run pytest tests/unit/plugins/modules/test_node.py

# Specific test with verbose output
uv run pytest tests/unit/plugins/modules/test_node.py::test_create -v

# With parallel execution
uv run pytest tests/unit/ -n auto
```

### Pytest Configuration

From `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

## Integration Tests

```bash
invoke tests-integration
```

Integration tests require a running Infrahub instance. The `integration` Docker service uses the `integration_network` to reach Infrahub.

Integration tests use Ansible playbooks in `tests/integration/targets/`.

### Testcontainers Suites

`tests/integration/processor/` and `tests/integration/inventory/` do not use the Docker Compose
`integration` service. They spin up a real Infrahub with the SDK's `TestInfrahubDocker` helper, so they
run through pytest directly and need their own dependency group:

```bash
uv sync --no-default-groups --group integration
export INFRAHUB_TESTING_IMAGE_VER=1.9.9

uv run --no-default-groups --group integration pytest tests/integration/processor \
  -m "integration and not measurement" -p no:pytest-infrahub-performance-test -q
```

Four details behind that command, three of which will otherwise cost you a failed run:

- **`--no-default-groups` is mandatory.** `dev` and `integration` are declared as conflicting groups in
  `pyproject.toml` (the `integration` group pulls `prefect-client`, which pins `cachetools<7`, while
  `dev` needs `tox` at `cachetools>=7`). Without it, uv refuses outright:
  `Groups 'dev' (enabled by default) and 'integration' are incompatible`.
- **`-p no:pytest-infrahub-performance-test` is already applied.** `addopts` in `pyproject.toml` passes it
  to every pytest run, so the copy above is redundant and omitting it costs nothing. It is there at all
  because that plugin's startup hook calls `psutil.cpu_freq()`, which raises on macOS and aborts collection.
- **`INFRAHUB_TESTING_IMAGE_VER`** selects the Infrahub image. It has no default.
- **Two markers, two audiences.** `integration` rides the PR gate. `measurement` additionally marks the
  heavy round-trip benchmarks in `test_fetch_roundtrip_measurement.py`, which load a schema and wait for
  convergence — too slow for a standard runner, so they run on scheduled builds only.

Fixtures are **class-scoped**, so every additional test class starts another Infrahub container. Adding
a test to an existing class rather than a new one is worth roughly a minute of PR wall-clock.

### Run pytest and sanity in separate passes

Running pytest creates `.pytest_collections/`, which contains a symlink to the absolute path of your
checkout. That directory is in `.gitignore`, and is now also in `.dockerignore` — it was not, and the
consequence was `invoke tests-sanity` failing inside the Docker build with:

```text
[ERROR]: Failed to find the target path '/Users/.../infrahub' for the symlink
         '/usr/src/app/.pytest_collections/ansible_collections/opsmill/infrahub'
failed to solve: process "/bin/sh -c ansible-galaxy collection build --output-path ./dist/ ."
         did not complete successfully: exit code: 1
```

The error names `ansible-galaxy`, not pytest, so it reads like a packaging problem. If you see it after
a dependency bump or on an older checkout, `rm -rf .pytest_collections` and re-run.

### Comparing two branches

Use `git worktree`, not `git stash`. `uv run` rewrites `uv.lock` as a side effect, so the tree is dirty
again the moment you run anything — which blocks `git stash pop` and can make `git checkout` fail
silently enough that you carry on measuring the branch you thought you had left.

```bash
git worktree add ../infrahub-baseline develop
```

## Linting (Not Tests, But Related)

```bash
# Run all linters (ruff check + ruff format + mypy + yamllint + rumdl)
invoke lint

# Type checking on its own
uv run mypy .

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

1. Check that `uv.lock` is up to date: `uv lock`
2. Check for network issues (uv needs to download packages)

### Sanity Test Import Errors

If sanity tests fail with import errors for `infrahub_sdk`:

- This is expected in the sanity test environment
- Ensure you use the conditional import pattern (`HAS_INFRAHUBCLIENT`)
- The `infrahub-sdk` dependency is installed in the Docker image but `ansible-test` may use isolated environments

### Test Output

Docker logs and test output go to stdout. If using `--exit-code-from`, the exit code reflects the test result (0 = pass, non-zero = fail).
