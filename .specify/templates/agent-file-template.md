# opsmill.infrahub Ansible Collection Development Guidelines

Auto-generated from all feature plans. Last updated: [DATE]

## Active Technologies

- **Python** >=3.10, <3.14
- **Ansible** >=2.15 (ansible-core)
- **infrahub-sdk** >=1.5, <2.0 (sync client: `InfrahubClientSync`)
- **Ruff** — linting and formatting
- **Poetry** — dependency management
- **Docker** + docker-compose — test execution pipeline
- **Docusaurus** — documentation site
- **pytest** — unit testing framework

## Project Structure

```text
plugins/
  modules/          # Ansible modules (user-facing interface stubs)
  action/           # Action plugins (controller-side execution logic)
  inventory/        # Dynamic inventory from Infrahub
  lookup/           # Lookup plugin for GraphQL queries
  module_utils/     # Shared Python utilities (SDK wrapper, base classes)
  doc_fragments/    # Reusable DOCUMENTATION fragments
roles/              # Ansible roles
tests/
  unit/             # Unit tests (pytest with mocked SDK)
  integration/      # Integration tests (Ansible playbooks against live Infrahub)
docs/               # Docusaurus documentation site
tasks/              # Invoke task definitions (lint, test, build, docs)
dev/
  knowledge/        # Architecture, plugin patterns, SDK usage docs
  guidelines/       # Python, testing, documentation, git workflow standards
  guides/           # Step-by-step how-to guides (creating modules, running tests)
```

## Commands

```bash
# Linting and formatting
invoke lint                    # Check (Ruff + yamllint)
invoke format                  # Auto-fix

# Testing
invoke tests-all               # Run all test tiers
invoke tests-sanity            # ansible-test sanity checks
invoke tests-unit              # pytest unit tests
invoke tests-integration       # Integration tests against Infrahub

# Documentation
invoke generate-doc            # Generate MDX from module docstrings
invoke docusaurus              # Build documentation site

# Build
invoke galaxy-build            # Build collection tarball
```

## Code Style

- **Ruff**: `select = ["ALL"]`, line-length 120, hard limit 150, double quotes, spaces
- **Imports**: `from __future__ import absolute_import, annotations, division, print_function` on every file
- **Type hints**: Modern style (`str | None` not `Optional[str]`)
- **Config**: `pyproject.toml` under `[tool.ruff]`
- See `dev/guidelines/python.md` for full Ruff rule configuration

## Recent Changes

[LAST 3 FEATURES AND WHAT THEY ADDED]

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
