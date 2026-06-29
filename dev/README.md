# Developer Documentation

Internal documentation for `opsmill.infrahub` collection contributors. For
user-facing docs, see the [Docusaurus site](https://docs.infrahub.app/ansible/)
generated from `docs/`.

## Quick Navigation

| I want to...                       | Go to                  |
|------------------------------------|------------------------|
| Understand how the collection works | `knowledge/`          |
| Follow coding and writing standards | `guidelines/`         |
| Do a specific task step by step     | `guides/`             |
| Learn why we made a decision        | `adr/`                |
| Read the project constitution       | `constitution.md`     |
| Use agent commands                  | `../.agents/commands/` |

## Directory Guide

- **constitution.md**: Pointer to the binding project principles in
  `.specify/memory/constitution.md`. The authoritative reference.
- **knowledge/**: Descriptive reference. How the system works.
- **guidelines/**: Prescriptive rules. How code and docs should be written.
- **guides/**: Step-by-step procedures for specific tasks.
- **adr/**: Architecture Decision Records. Why we chose what we chose.

## Current Knowledge

- [architecture.md](knowledge/architecture.md) — Collection layout, plugin types, data flow, key abstractions
- [plugin-patterns.md](knowledge/plugin-patterns.md) — Ansible conventions: boilerplate, docstrings, arg specs, conditional imports, state management
- [infrahub-sdk-usage.md](knowledge/infrahub-sdk-usage.md) — InfrahubclientWrapper, InfrahubModule, processor classes, sync-only pattern
- [inventory-and-lookup.md](knowledge/inventory-and-lookup.md) — Dynamic inventory and GraphQL lookup plugins, end to end

## Current Guidelines

- [python.md](guidelines/python.md) — Ruff config, line length 120, type hints, dependencies
- [testing.md](guidelines/testing.md) — Docker-based test execution, mocking, sanity/unit/integration
- [documentation.md](guidelines/documentation.md) — Doc generation pipeline, Jinja2 templates, Docusaurus, Vale
- [module-docstrings.md](guidelines/module-docstrings.md) — DOCUMENTATION/EXAMPLES/RETURN rules and doc fragments
- [markdown.md](guidelines/markdown.md) — Markdown conventions, file naming, markdownlint/Vale/yamllint
- [git-workflow.md](guidelines/git-workflow.md) — Branch model (develop/stable), PR conventions, CI, versioning

## Current Guides

- [creating-a-module.md](guides/creating-a-module.md) — Add a new module + action/module_utils + tests + docs
- [running-tests.md](guides/running-tests.md) — Invoke tasks, Docker Compose, pytest, troubleshooting
- [adding-a-doc-fragment.md](guides/adding-a-doc-fragment.md) — When and how to add a shared doc fragment
- [debugging-sanity-failures.md](guides/debugging-sanity-failures.md) — Reproduce and fix `ansible-test sanity` failures

## Current ADRs

- [0001-two-plugin-patterns.md](adr/0001-two-plugin-patterns.md) — Module-utils vs action plugin patterns
- [0002-sdk-abstraction-wrapper.md](adr/0002-sdk-abstraction-wrapper.md) — Wrap the SDK behind `InfrahubclientWrapper`
- [0003-sync-only-sdk.md](adr/0003-sync-only-sdk.md) — Synchronous-only SDK usage

## Agent Commands

Agent commands live at the repository root under
[`../.agents/commands/`](../.agents/commands/):

- [add-module](../.agents/commands/add-module.md) — Scaffold a new Ansible module
- [fix-bug](../.agents/commands/fix-bug.md) — Guided bug investigation and fix workflow
- `speckit.*` — Spec-kit workflow commands (specify, plan, tasks, implement, …)
