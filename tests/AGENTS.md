# AGENTS.md — tests/

Testing context for the `opsmill.infrahub` Ansible collection.

## Test Types

| Type | Directory | Runner | Purpose |
|------|-----------|--------|---------|
| Sanity | (Ansible built-in) | `ansible-test sanity` | Module standards compliance |
| Unit | `tests/unit/` | pytest | Individual function/class testing |
| Integration | `tests/integration/` | ansible-test / playbooks | End-to-end with Infrahub |

## Execution

All tests run inside Docker containers via `docker-compose.yml`:

```bash
# Via invoke (recommended)
invoke tests-sanity
invoke tests-unit
invoke tests-integration

# Via docker compose directly
docker compose up --build --force-recreate --quiet-pull --exit-code-from sanity sanity
docker compose up --build --force-recreate --quiet-pull --exit-code-from unit unit
docker compose up --build --force-recreate --quiet-pull --exit-code-from integration integration
```

## Sanity Tests

Run by `ansible-test sanity` inside the `sanity` Docker target. Checks:
- Module documentation format
- Python import correctness
- Required boilerplate (`__metaclass__ = type`, `__future__` imports)
- Plugin interface compliance

The `pep8` sanity test is skipped (Ruff handles this).

## Unit Tests

### Structure

```
tests/unit/
  plugins/
    module_utils/
      test_*.py
    modules/
      test_*.py
```

### Pytest Configuration

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["."]
```

### Mocking Conventions

- Mock `InfrahubClientSync` and SDK responses
- Mock `AnsibleModule` with controlled `params`, `exit_json`, `fail_json`
- Use `unittest.mock.patch` for SDK imports
- Use `pytest-mock` fixtures when preferred

### Running Locally (Fast Iteration)

```bash
uv run pytest tests/unit/ -v
uv run pytest tests/unit/plugins/modules/test_node.py -v
uv run pytest tests/unit/ -n auto  # parallel with pytest-xdist
```

## Integration Tests

Integration tests live in `tests/integration/targets/` and require a running Infrahub instance. The `integration` Docker service connects via `integration_network`.

## Dev Dependencies

```toml
pytest = "^9.0.2"
pytest-mock = "*"
pytest-xdist = "*"
pytest-pythonpath = "*"
mock = "^5.2.0"
```

## When to Run Tests

| Trigger | Command |
|---------|---------|
| Modified any file in `plugins/` | `invoke tests-sanity` |
| Modified module logic or `module_utils/` | `invoke tests-unit` |
| Modified interaction with Infrahub API | `invoke tests-integration` |
| Before opening a PR | `invoke tests-all` |

Always run sanity tests after plugin changes — they catch missing boilerplate, broken imports, and documentation format issues that lint won't find.

## Detailed Reference

- [../dev/guidelines/testing.md](../dev/guidelines/testing.md) — full testing guidelines
- [../dev/guides/running-tests.md](../dev/guides/running-tests.md) — step-by-step guide
