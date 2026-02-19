# AGENTS.md — docs/

Documentation context for the `opsmill.infrahub` Ansible collection.

## Overview

This is a [Docusaurus](https://docusaurus.io/) site that hosts the collection's documentation. Plugin reference pages are **generated** from Python docstrings — do not edit them directly.

## Generation Pipeline

```
plugins/modules/*.py (DOCUMENTATION/EXAMPLES/RETURN docstrings)
  → tasks/docs.py (extract + parse YAML)
    → docs/_templates/*.mdx.j2 (Jinja2 rendering)
      → docs/docs/references/plugins/*.mdx (generated output)
        → Docusaurus build → static site
```

### Commands

```bash
# Regenerate plugin reference docs from docstrings
invoke generate-doc

# Build the Docusaurus site
invoke docusaurus

# Or directly:
cd docs && npm run build
```

## Directory Structure

```
docs/
  docs/                          # Content pages
    references/
      plugins/                   # GENERATED — never edit these
        artifact_fetch_module.mdx
        artifact_generate_module.mdx
        branch_module.mdx
        node_module.mdx
        query_graphql_module.mdx
        inventory_inventory.mdx
        lookup_lookup.mdx
    readme.mdx                   # GENERATED — landing page
  _templates/                    # Jinja2 templates (edit these)
    plugin.mdx.j2               # Template for individual plugin pages
    readme.mdx.j2               # Template for landing page
  src/                           # Docusaurus React source
  static/                        # Static assets (images, etc.)
  docusaurus.config.ts           # Site configuration
  sidebars.ts                    # Navigation sidebar
  package.json                   # Node.js dependencies
```

## Generated Files — Never Edit

These files are overwritten by `invoke generate-doc`:

- `docs/docs/references/plugins/*.mdx`
- `docs/docs/readme.mdx`

To change plugin reference content, edit the `DOCUMENTATION`, `EXAMPLES`, or `RETURN` docstrings in the corresponding `plugins/modules/*.py` file, then regenerate.

To change the page layout or template, edit `docs/_templates/*.mdx.j2`.

## Prose Linting

### Vale

Configuration: `.vale.ini` (repo root)

```bash
vale docs/
```

CI runs Vale automatically on doc changes.

### Markdownlint

Configuration: `.markdownlint.yml` (repo root)

## Building Locally

```bash
cd docs
npm install
npm run build
npm run start  # local dev server
```

## When to Regenerate

Run `invoke generate-doc` after any of these changes:

- Editing `DOCUMENTATION`, `EXAMPLES`, or `RETURN` in any `plugins/modules/*.py` file
- Adding or removing a module
- Changing `plugins/doc_fragments/fragments.py`
- Modifying Jinja2 templates in `docs/_templates/`

The generated MDX files are checked into git, so regenerating them produces a visible diff that should be included in your commit.

## Detailed Reference

- [../dev/guidelines/documentation.md](../dev/guidelines/documentation.md) — full documentation guidelines
