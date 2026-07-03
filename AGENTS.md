# AGENTS.md — opsmill.infrahub Ansible Collection

Ansible collection — modules, plugins, and inventory sources for [Infrahub](https://github.com/opsmill/infrahub), an infrastructure data platform.

This file is the portable router: repo-wide facts every agent needs up front. Deeper how-tos, architecture notes, and decision records live under [dev/](dev/) — see Navigation below.

- **Namespace / Collection:** `opsmill.infrahub` · **License:** GPLv3
- **Repo:** <https://github.com/opsmill/infrahub-ansible> · **Docs:** <https://docs.infrahub.app/ansible/>
- **Constitution (binding principles):** [.specify/memory/constitution.md](.specify/memory/constitution.md)
- **Dev docs index:** [dev/README.md](dev/README.md) · **Decision records:** [dev/adr/](dev/adr/)

## Tech Stack

| Component | Version/Tool |
|-----------|-------------|
| Python | >=3.11, <3.15 |
| ansible-core | >=2.18 |
| infrahub-sdk | >=1.19.0, <2.0 |
| Linter/Formatter | Ruff (pinned in pyproject.toml) |
| Tests | pytest, ansible-test sanity (Docker-based) |
| Docs | Docusaurus + Jinja2 generation |
| Deps | uv |
| Tasks | Invoke |

## Commands

```bash
invoke lint            # Check (ruff + yamllint)
invoke format          # Auto-fix (ruff)
invoke tests-sanity    # Ansible compliance (boilerplate, docs, imports)
invoke tests-unit      # Unit tests
invoke tests-integration
invoke tests-all
invoke generate-doc    # Regenerate plugin reference MDX from docstrings
invoke docusaurus      # Build Docusaurus site
invoke galaxy-build    # Build collection tarball
```

All tests run in Docker. Run checks as you go, not just at the end:

| When you change… | Run |
|------------------|-----|
| any plugin file (`plugins/**/*.py`) | `invoke format` → `invoke lint` → `invoke tests-sanity` |
| module logic or `module_utils` | also `invoke tests-unit` |
| module docstrings (DOCUMENTATION / EXAMPLES / RETURN) | `invoke generate-doc` |

Full verification before a PR: `invoke format && invoke lint && invoke tests-sanity && invoke tests-unit && invoke generate-doc`.

New-module walkthrough: [dev/guides/creating-a-module.md](dev/guides/creating-a-module.md). Test execution detail: [dev/guides/running-tests.md](dev/guides/running-tests.md).

## Architecture & Standards Pointers

- [dev/knowledge/architecture.md](dev/knowledge/architecture.md) — Collection structure, plugin types, data flow
- [dev/knowledge/plugin-patterns.md](dev/knowledge/plugin-patterns.md) — Ansible boilerplate, docstrings, arg specs, conditional imports
- [dev/knowledge/infrahub-sdk-usage.md](dev/knowledge/infrahub-sdk-usage.md) — SDK wrapper, InfrahubModule, processor classes
- [dev/guidelines/python.md](dev/guidelines/python.md) — Ruff config, line length 120, quote style, import sorting
- [dev/guidelines/testing.md](dev/guidelines/testing.md) — Docker test execution, mocking patterns, pytest config
- [dev/guidelines/documentation.md](dev/guidelines/documentation.md) — Doc generation pipeline, docstring format
- [dev/guidelines/git-workflow.md](dev/guidelines/git-workflow.md) — Branch model (develop/stable), PR conventions

### Key Source Locations

| Path | Contents |
|------|----------|
| `plugins/modules/` | Module stubs (DOCUMENTATION + AnsibleModule) |
| `plugins/action/` | Action plugins (controller-side logic) |
| `plugins/module_utils/infrahub_utils.py` | Core: InfrahubclientWrapper, InfrahubModule, processors (~1500 lines) |
| `plugins/module_utils/node.py` | NodeModule (node CRUD) |
| `plugins/module_utils/branch.py` | BranchModule (branch CRUD) |
| `plugins/module_utils/exception.py` | SDK exception → Ansible error mapping |
| `plugins/inventory/inventory.py` | Dynamic inventory plugin |
| `plugins/lookup/lookup.py` | GraphQL lookup plugin |
| `plugins/doc_fragments/fragments.py` | Reusable DOCUMENTATION fragments |

## Generated Files — Never Edit Directly

`invoke generate-doc` generates `docs/docs/references/plugins/*.mdx` and `docs/docs/readme.mdx`. Edit the source docstrings in `plugins/modules/*.py` or the Jinja2 templates in `docs/_templates/` instead.

## Boundaries

### Always Do

- Use the conditional import pattern for `infrahub-sdk` (`HAS_INFRAHUBCLIENT`)
- Include `__metaclass__ = type` and `from __future__ import` boilerplate in plugin files
- Use `no_log=True` for token/secret parameters
- Follow the existing module patterns (see `dev/knowledge/plugin-patterns.md`)
- Use `deepcopy(INFRAHUB_ARG_SPEC)` when extending the standard argument spec

### Ask First

- Adding new dependencies to `pyproject.toml`
- Changing the ruff configuration or ignoring new rules
- Modifying `plugins/module_utils/infrahub_utils.py` (core shared code, ~1500 lines)
- Changing the `INFRAHUB_ARG_SPEC` (affects all modules using it)
- Modifying CI workflows in `.github/workflows/`

### Never Do

- Edit generated files in `docs/docs/references/plugins/`
- Remove the `__metaclass__ = type` or `__future__` imports (breaks `ansible-test sanity`)
- Use async SDK methods (this collection is synchronous only)
- Hardcode credentials — always use environment variable fallbacks
- Skip the conditional `HAS_INFRAHUBCLIENT` check in any plugin
