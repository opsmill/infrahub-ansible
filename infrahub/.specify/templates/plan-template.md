# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

**Language/Version**: Python >=3.10, <3.14
**Primary Dependencies**: Ansible >=2.15, infrahub-sdk >=1.5 <2.0, Ruff
**Storage**: N/A (Infrahub is the data store, accessed via infrahub-sdk)
**Testing**: pytest (unit, mocked SDK), ansible-test (sanity), Ansible playbooks (integration), all via Docker
**Target Platform**: Ansible controller (Linux/macOS)
**Project Type**: Ansible collection plugin
**Constraints**: Must pass ansible-test sanity, sync-only SDK usage, GPLv3 license, Ruff compliance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] **Gate 1 — Ansible Collection Standards (Principle I)**: Does the feature include required boilerplate, docstrings, and doc fragments?
- [ ] **Gate 2 — Plugin Pattern (Principle II)**: Does the feature follow one of the two established plugin patterns (module_utils or action plugin)?
- [ ] **Gate 3 — Idempotency (Principle III)**: Is idempotency addressed? (state management, check_mode, diff support)
- [ ] **Gate 4 — SDK Abstraction (Principle IV)**: Do all API calls go through InfrahubclientWrapper with conditional imports and exception handling?
- [ ] **Gate 5 — Test Coverage (Principle V)**: Are all three test tiers planned (sanity, unit, integration)?

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (Ansible collection layout)

```text
plugins/
  modules/<name>.py          # Module stub (DOCUMENTATION/EXAMPLES/RETURN + argument spec)
  action/<name>.py           # Action plugin (if action plugin pattern)
  module_utils/<name>.py     # Module utils class (if module_utils pattern)
  doc_fragments/fragments.py # Update if new shared options needed

tests/
  unit/plugins/
    modules/test_<name>.py       # Unit tests for module
    module_utils/test_<name>.py  # Unit tests for module utils
  integration/targets/<name>/
    tasks/main.yml               # Integration test playbook

docs/
  docs/references/plugins/       # Generated MDX (invoke generate-doc)
```

The layout is fixed by Ansible collection conventions — no structural choices needed.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., Custom pattern] | [current need] | [why standard pattern insufficient] |
