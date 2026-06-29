# Markdown Guidelines

Conventions for the Markdown in `dev/`, `docs/`, and other prose in the repo.

## File Naming

Use lowercase kebab-case for Markdown filenames: `creating-a-module.md`,
`debugging-sanity-failures.md`. ADRs are the one exception — they carry a
zero-padded numeric prefix (`0001-two-plugin-patterns.md`); see
[../adr/README.md](../adr/README.md).

## Tooling

Three linters cover Markdown and the YAML embedded around it:

- **markdownlint** — Markdown structure and formatting. Config:
  [`.markdownlint.yaml`](../../.markdownlint.yaml) at the repo root. Run it with
  your editor integration or `npx markdownlint-cli2 '**/*.md'`.
- **Vale** — prose style for the documentation site, using the custom
  `Infrahub` style under `.vale/styles/`. Config: [`.vale.ini`](../../.vale.ini).
  CI runs Vale over `docs/**/*.{md,mdx}` in `workflow-linter.yml`.
- **yamllint** — front matter and YAML files (including the YAML inside plugin
  `DOCUMENTATION` blocks once generated). Run via `invoke lint` or
  `uv run yamllint .`.

## Configured Rules

`.markdownlint.yaml` starts from the default rule set and relaxes a few:

- `MD013` (line length) — disabled, for readable prose.
- `MD024` (duplicate headings) — `siblings_only`, so tabbed sections may repeat.
- `MD025` (single H1) — `front_matter_title: ""`, to avoid clashing with MDX.
- `MD029` (ordered-list prefix) — disabled, for manual numbering.
- `MD033` (inline HTML) — disabled, for MDX/React components.
- `MD060` (table column style) — disabled, for table flexibility.

Markdown that ships to the docs site (`.mdx`) follows the same rules plus the
Vale `Infrahub` style; see [documentation.md](documentation.md) for the docs
pipeline.
