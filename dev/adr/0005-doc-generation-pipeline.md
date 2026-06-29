# ADR-0005: Generated Plugin Reference Documentation

**Status**: Accepted
**Date**: 2026-02-25
**Source**: `.specify/memory/constitution.md` — backfilled from existing code

## Context

Each plugin already carries its full interface in standard Ansible docstrings —
`DOCUMENTATION`, `EXAMPLES`, and `RETURN` — which `ansible-test sanity`
validates. The user-facing reference site (the Docusaurus build under `docs/`,
published to <https://docs.infrahub.app/ansible/>) needs the same information as
MDX pages. Maintaining a second, hand-written copy of every parameter and return
value would guarantee drift: the docstrings are the source `ansible-test`
enforces, so any prose duplicate of them would silently fall out of date.

## Decision

Generate the plugin reference MDX from the docstrings; never hand-edit the
output. The `invoke generate-doc` task (`tasks/docs.py`) is the single pipeline.

- `generate_docs` discovers plugin files under `plugins/{modules,inventory,
  lookup}/`, parses `DOCUMENTATION` / `EXAMPLES` / `RETURN` out of each, and
  renders them through the Jinja2 templates in `docs/_templates/`
  (`plugin.mdx.j2` and the readme template).
- Output is written to `docs/docs/references/plugins/<plugin>_<type>.mdx` and the
  landing page `docs/docs/readme.mdx`, stamped with the collection version from
  `galaxy.yml` and the `requires_ansible` value.
- A `mdx_safe` Jinja2 filter escapes JSX-reserved braces in prose (so a
  docstring `{var}` is not parsed as a JSX expression) while leaving Markdown
  code spans untouched.
- `invoke docusaurus` then builds the static site (`npm run build`) from the
  generated MDX.

## Consequences

- The docstrings are the single source of truth; the reference site cannot drift
  from the validated interface.
- Files under `docs/docs/references/plugins/` and `docs/docs/readme.mdx` are
  generated artifacts and must never be edited directly — fix the docstring in
  `plugins/modules/*.py` or the template in `docs/_templates/` and regenerate.
- Changing a docstring obliges the author to run `invoke generate-doc`; CI also
  regenerates and commits the docs on release
  (`workflow-changelog-and-docs.yml`).
- The rules and pipeline detail live in
  [../guidelines/documentation.md](../guidelines/documentation.md) and
  [../guidelines/module-docstrings.md](../guidelines/module-docstrings.md).

## Alternatives Considered

- **Hand-written reference pages**: rejected — duplicates the docstrings and
  drifts from the interface `ansible-test sanity` validates.
- **`antsibull-docs` to build a standalone Ansible doc site**: rejected — the
  project standardised on a single Docusaurus site, so a bespoke Jinja2 → MDX
  step keeps all docs (reference and narrative) in one toolchain.
