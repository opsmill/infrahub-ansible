# opsmill.infrahub Ansible Collection Constitution

## Core Principles

### I. Ansible Collection Standards

Every Python file in this collection must comply with Ansible's module standards:

- **Copyright header**: `# Copyright (c) <year> Opsmill` + GPLv3 reference on every file
- **Future imports**: `from __future__ import absolute_import, annotations, division, print_function` required
- **Metaclass boilerplate**: `__metaclass__ = type` required (Ansible Python 2/3 compatibility header)
- **Module docstrings**: Every module must define `DOCUMENTATION`, `EXAMPLES`, and `RETURN` as module-level YAML strings
- **Doc fragments**: Shared options (api_endpoint, token, timeout, branch, validate_certs) use `plugins/doc_fragments/fragments.py` via `extends_documentation_fragment`
- **Sanity compliance**: `ansible-test sanity` must pass with zero errors; pep8 test skipped in favor of Ruff

### II. Two Plugin Patterns

All plugins follow one of two established patterns — no hybrid or custom patterns:

- **Module-utils pattern** (for stateful CRUD operations): Module stub in `plugins/modules/` delegates to an `InfrahubModule` subclass in `plugins/module_utils/`. Uses `INFRAHUB_ARG_SPEC` with `deepcopy`. Supports `state` (present/absent), `check_mode`, and `--diff`. Used by: `node`, `branch`.
- **Action plugin pattern** (for controller-side API calls): Module stub is minimal (docs/validation only). `ActionModule(ActionBase)` in `plugins/action/` does real work. Uses inline argument spec and `self._task.args`. Used by: `query_graphql`, `artifact_fetch`, `artifact_generate`.

**Decision criteria**: Use module-utils for anything requiring idempotency and state management. Use action plugin for read-only queries or operations that cannot be made idempotent.

### III. Idempotency and State Management

Modules that manage Infrahub objects must be idempotent:

- **Fetch-compare-act cycle**: Fetch existing object, compare with desired state, only call API if changes are needed
- **State methods**: `_ensure_object_exists()` for create/update, `_ensure_object_absent()` for delete
- **Changed reporting**: `changed: true` only when actual mutations occur; running twice with identical params must yield `changed: false`
- **check_mode**: `supports_check_mode=True` in AnsibleModule; skip all mutations when `module.check_mode` is True
- **Diff support**: `_build_diff(before, after)` for `--diff` output showing before/after state
- **HFID normalization**: Human-Friendly IDs normalized for consistent object identification across runs

### IV. SDK Abstraction Layer

All Infrahub API access is mediated through a single abstraction:

- **InfrahubclientWrapper**: All API calls go through this wrapper — never call `InfrahubClientSync` directly from modules or action plugins
- **Conditional imports**: `try/except ImportError` with `HAS_INFRAHUBCLIENT` flag; runtime check before any SDK use. This allows `ansible-doc` and sanity tests to parse files without the SDK installed
- **Sync-only**: Use `InfrahubClientSync`, never the async `InfrahubClient`
- **Exception handling**: `handle_infrahub_exceptions_decorator` maps SDK exceptions (`GraphQLError`, `SchemaNotFoundError`, `BranchNotFoundError`, `ServerNotReachableError`) to Ansible error messages
- **Environment variable fallbacks**: `INFRAHUB_ADDRESS` for api_endpoint, `INFRAHUB_API_TOKEN` for token
- **Token security**: `no_log=True` on all token parameters

### V. Test Coverage and Quality Gates

Three test tiers ensure collection quality:

- **Sanity tests**: `ansible-test sanity` validates module documentation format, Python import correctness, required boilerplate, and plugin interface compliance
- **Unit tests**: pytest with mocked `InfrahubClientSync` via `@patch`; no external dependencies; cover all state transitions (create, update, delete, no-change, error, check_mode)
- **Integration tests**: Ansible playbooks in `tests/integration/targets/<name>/tasks/main.yml` exercising the full module-to-API path against a running Infrahub instance
- **Docker pipeline**: All tests run in Docker via `docker-compose.yml` with multi-stage builds (base, sanity, unittests, integration)
- **CI**: Linter + sanity + unit tests run on every PR to `develop`

## Constraints and Requirements

- **Python**: >=3.10, <3.14
- **Ansible**: >=2.15.13rc1 (Python 3.9), >=2.17.7rc1 (Python 3.10+)
- **infrahub-sdk**: >=1.5, <2.0 (with `[all]` extras for sync support)
- **License**: GPLv3 — copyright header required on every Python file
- **Linting**: Ruff with `select = ["ALL"]`, line-length 120 (hard limit 150), double quotes, spaces, preview mode enabled
- **Additional linters**: yamllint, ansible-lint, markdownlint, Vale
- **Dependencies**: Managed via Poetry (`pyproject.toml`)

## Development Workflow

- **Branch model**: `develop` (active development), `stable` (releases). Feature branches off `develop`
- **Commit messages**: Conventional format — `feat:`, `fix:`, `docs:`, `chore:`, `test:`
- **PRs**: Target `develop` branch
- **Invoke commands**: `invoke lint`, `invoke format`, `invoke tests-all`, `invoke tests-sanity`, `invoke tests-unit`, `invoke tests-integration`, `invoke generate-doc`, `invoke docusaurus`, `invoke galaxy-build`
- **Docker pipeline**: `docker-compose.yml` orchestrates all test execution
- **Module creation**: Follow `dev/guides/creating-a-module.md` — stub, action/module_utils, tests, docs, changelog

## Governance

- This constitution supersedes ad-hoc decisions. All PRs must verify compliance with these principles
- Amendments require updating this document and the corresponding `dev/knowledge/` and `dev/guidelines/` files in sync
- Use `dev/guides/creating-a-module.md` as the runtime development guide for new modules
- Complexity beyond these established patterns must be justified with documented rationale

**Version**: 1.0.0 | **Ratified**: 2026-02-25 | **Last Amended**: 2026-02-25
