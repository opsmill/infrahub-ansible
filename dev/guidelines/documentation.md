# Documentation Guidelines

## Overview

Documentation lives in two places:
1. **Plugin docstrings** — `DOCUMENTATION`, `EXAMPLES`, `RETURN` in each module file
2. **Docusaurus site** — generated from docstrings + hand-written content in `docs/`

## Doc Generation Pipeline

```
Plugin Python files (DOCUMENTATION/EXAMPLES/RETURN docstrings)
  → tasks/docs.py (extract_docstring, parse_ansible_doc)
    → Jinja2 templates (docs/_templates/*.mdx.j2)
      → MDX files (docs/docs/references/plugins/*.mdx)
        → Docusaurus build → Static site
```

### Running Doc Generation

```bash
# Generate plugin reference docs from docstrings
invoke generate-doc

# Build the full Docusaurus site
invoke docusaurus
```

### Template Files

| Template | Purpose |
|----------|---------|
| `docs/_templates/plugin.mdx.j2` | Individual plugin reference page |
| `docs/_templates/readme.mdx.j2` | Landing page with plugin index |

### Generated Files

**Never edit these directly** — they are overwritten by `generate-doc`:

```
docs/docs/references/plugins/<name>_module.mdx
docs/docs/references/plugins/<name>_inventory.mdx
docs/docs/references/plugins/<name>_lookup.mdx
docs/docs/readme.mdx
```

Edit the source docstrings in `plugins/modules/*.py` or the Jinja2 templates instead.

## Plugin Docstring Format

### DOCUMENTATION

YAML format embedded in a Python triple-quoted string:

```python
DOCUMENTATION = """
---
module: <name>
author:
    - Opsmill (@opsmill)
version_added: "<x.y.z>"
short_description: <one line>
description:
    - <paragraph>
requirements:
    - infrahub-sdk
options:
    <param_name>:
        required: <True|False>
        description:
            - <text>
        type: <str|int|bool|dict|list|raw>
        default: <value>
"""
```

### EXAMPLES

YAML playbook examples:

```python
EXAMPLES = """
---
- name: Example playbook title
  gather_facts: false
  hosts: localhost
  tasks:
    - name: Task description
      opsmill.infrahub.<module>:
        param: value
"""
```

### RETURN

YAML describing return values:

```python
RETURN = """
object:
  description: The returned object
  returned: success
  type: dict
msg:
  description: Status message
  returned: always
  type: str
"""
```

## Docusaurus Site

### Structure

```
docs/
  docs/                     # Content pages
    references/
      plugins/              # Generated plugin docs (*.mdx)
    readme.mdx              # Generated landing page
  src/                      # Docusaurus React source
  static/                   # Static assets
  _templates/               # Jinja2 templates for generation
  docusaurus.config.ts      # Site configuration
  sidebars.ts               # Navigation sidebar
  package.json              # Node.js dependencies
```

### Building Locally

```bash
cd docs
npm install
npm run build    # or: invoke docusaurus
```

## Prose Linting with Vale

Configuration in `.vale.ini` at the repo root. Vale checks documentation for style consistency.

```bash
# Run Vale on docs
vale docs/
```

CI runs Vale automatically on documentation changes (`.github/workflows/workflow-linter.yml`).

## Markdown Linting

Configuration in `.markdownlint.yaml`. Ensures consistent markdown formatting.

## What to Document

When adding a new module:
1. Write complete `DOCUMENTATION`, `EXAMPLES`, and `RETURN` docstrings in the module file
2. Run `invoke generate-doc` to regenerate reference docs
3. Verify the generated MDX renders correctly with `invoke docusaurus`

When adding features to existing modules:
1. Update the relevant docstring sections
2. Add new examples if the feature introduces new usage patterns
3. Update `RETURN` if new return values are added
4. Regenerate docs
