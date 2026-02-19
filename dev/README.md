# dev/

Developer knowledge base and AI agent resources for the `opsmill.infrahub` Ansible collection.

## Structure

### knowledge/

Deep reference material extracted from the codebase.

- [architecture.md](knowledge/architecture.md) — Collection structure, plugin types, data flow, key abstractions
- [plugin-patterns.md](knowledge/plugin-patterns.md) — Ansible-specific conventions: boilerplate, docstrings, arg specs, conditional imports, state management
- [infrahub-sdk-usage.md](knowledge/infrahub-sdk-usage.md) — InfrahubclientWrapper, InfrahubModule, processor classes, sync-only pattern

### guidelines/

Standards and conventions for contributing.

- [python.md](guidelines/python.md) — Ruff config, line length 120, rule selection, format settings
- [testing.md](guidelines/testing.md) — Docker-based test execution, unit tests with mocks, sanity tests
- [documentation.md](guidelines/documentation.md) — Doc generation pipeline, Jinja2 templates, Docusaurus, Vale
- [git-workflow.md](guidelines/git-workflow.md) — Branch model (develop/stable), PR conventions, CI, versioning

### guides/

Step-by-step how-tos for common tasks.

- [creating-a-module.md](guides/creating-a-module.md) — Add a new module + action plugin + tests + docs
- [running-tests.md](guides/running-tests.md) — Invoke tasks, Docker Compose, pytest, troubleshooting

### commands/

Claude Code slash commands (available via `/add-module`, `/fix-bug`).

- [add-module.md](commands/add-module.md) — Scaffold a new Ansible module
- [fix-bug.md](commands/fix-bug.md) — Guided bug investigation and fix workflow
