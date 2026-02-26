# [PROJECT_NAME] Constitution
<!-- Example: opsmill.infrahub Ansible Collection Constitution -->

## Core Principles

### [PRINCIPLE_1_NAME]
<!-- Example: I. Ansible Collection Standards -->
[PRINCIPLE_1_DESCRIPTION]
<!-- Example: Every file requires copyright header, __future__ imports, __metaclass__ = type boilerplate; Modules must define DOCUMENTATION, EXAMPLES, RETURN docstrings; Doc fragments for shared options; ansible-test sanity must pass -->

### [PRINCIPLE_2_NAME]
<!-- Example: II. Two Plugin Patterns -->
[PRINCIPLE_2_DESCRIPTION]
<!-- Example: Module-utils pattern for stateful CRUD (node, branch); Action plugin pattern for controller-side API calls (query_graphql, artifacts); Decision criteria documented -->

### [PRINCIPLE_3_NAME]
<!-- Example: III. Idempotency and State Management -->
[PRINCIPLE_3_DESCRIPTION]
<!-- Example: Fetch-compare-act cycle; _ensure_object_exists/_ensure_object_absent; check_mode support; --diff output; HFID normalization; changed: true only on actual mutations -->

### [PRINCIPLE_4_NAME]
<!-- Example: IV. SDK Abstraction Layer -->
[PRINCIPLE_4_DESCRIPTION]
<!-- Example: All API calls through InfrahubclientWrapper; Conditional HAS_INFRAHUBCLIENT imports; Sync-only client; handle_infrahub_exceptions_decorator; Environment variable fallbacks -->

### [PRINCIPLE_5_NAME]
<!-- Example: V. Test Coverage and Quality Gates -->
[PRINCIPLE_5_DESCRIPTION]
<!-- Example: Three test tiers: sanity (ansible-test), unit (pytest with mocked SDK), integration (playbooks against live Infrahub); Docker pipeline; CI on every PR -->

## [SECTION_2_NAME]
<!-- Example: Constraints and Requirements -->

[SECTION_2_CONTENT]
<!-- Example: Python >=3.10 <3.14; Ansible >=2.15; infrahub-sdk >=1.5 <2.0; GPLv3 license; Ruff with select=ALL; Poetry for dependencies -->

## [SECTION_3_NAME]
<!-- Example: Development Workflow -->

[SECTION_3_CONTENT]
<!-- Example: Branch model (develop/stable); Conventional commits (feat:, fix:, docs:); invoke commands for lint, test, build, docs; Docker-based test pipeline; Module creation per dev/guides/ -->

## Governance
<!-- Example: Constitution supersedes ad-hoc decisions; All PRs must verify compliance; Amendments require doc updates; Use creating-a-module.md as runtime guide -->

[GOVERNANCE_RULES]
<!-- Example: Constitution-first development; PR compliance checks; Module creation guide as runtime reference; Complexity must be justified -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
<!-- Example: Version: 1.0.0 | Ratified: 2026-02-25 | Last Amended: 2026-02-25 -->
