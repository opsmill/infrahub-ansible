# Markdown Guidelines

Conventions for the Markdown in `dev/`, `docs/`, and other prose in the repo.

## File Naming

Use lowercase kebab-case for Markdown filenames: `creating-a-module.md`,
`debugging-sanity-failures.md`. ADRs are the one exception — they carry a
zero-padded numeric prefix (`0001-two-plugin-patterns.md`); see
[../adr/README.md](../adr/README.md).

## Tooling

Three linters cover Markdown and the YAML embedded around it:

- **rumdl** — Markdown structure and formatting. Config: `[tool.rumdl]` in
  [`pyproject.toml`](../../pyproject.toml) at the repo root. Run it with
  `uv run rumdl check .` or `invoke lint`.
- **Vale** — prose style for the documentation site, using the custom
  `Infrahub` style under `.vale/styles/`. Config: [`.vale.ini`](../../.vale.ini).
  CI runs Vale over `docs/**/*.{md,mdx}` in `workflow-linter.yml`.
- **yamllint** — front matter and YAML files (including the YAML inside plugin
  `DOCUMENTATION` blocks once generated). Run via `invoke lint` or
  `uv run yamllint .`.

## Configured Rules

`[tool.rumdl]` in `pyproject.toml` starts from the default rule set and
disables a few:

- `MD013` (line length) — disabled, for readable prose.
- `MD033` (inline HTML) — disabled, for MDX/React components.
- `MD041` (first-line heading) — disabled, for files with front matter or
  non-heading starts.

Vendored and generated trees are excluded: `docs/` (Vale-owned MDX), `.agents/`
(vendored agent skills/commands), `.specify/` (vendored spec-kit tooling), and
`.github/agents/` (vendored spec-kit agent definitions).

Markdown that ships to the docs site (`.mdx`) follows the same rules plus the
Vale `Infrahub` style; see [documentation.md](documentation.md) for the docs
pipeline.
