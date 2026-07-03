# Module Docstrings

Every plugin in `plugins/` carries module-level docstrings that Ansible and the
doc pipeline parse as YAML. This guideline covers the rules for writing them;
for the generation pipeline itself see [documentation.md](documentation.md).

## The Three Docstrings

- **`DOCUMENTATION`** — the module's identity and option schema (YAML). Include
  `module`/`name`, `author`, `short_description`, `description`, `requirements`,
  and an `options:` map. Each option declares `description`, `type`, `required`,
  and a `default` where applicable. This block is the contract that
  `ansible-test sanity` validates against the `argument_spec`, so the two must
  agree (option names, types, and which are required).
- **`EXAMPLES`** — runnable playbook snippets in YAML. Lead each with a `name:`
  and call the plugin by its fully qualified name (`opsmill.infrahub.<plugin>`).
- **`RETURN`** — the shape of what the plugin returns, keyed by return name with
  `description`, `returned`, and `type`.

The YAML inside these strings must be valid and yamllint-clean. Mark token and
secret options with `no_log: True` and `INFRAHUB_*` `env` fallbacks.

## Doc Fragments

Options shared across plugins live in
[`plugins/doc_fragments/fragments.py`](../../plugins/doc_fragments/fragments.py)
as attributes of `ModuleDocFragment` — for example `BASE` (the common
`api_endpoint`, `token`, `timeout`, `branch`, `validate_certs` options) and
`TAGS`. A plugin pulls these in through `extends_documentation_fragment` rather
than restating the options. Add a fragment instead of copy-pasting shared
options; the how-to is in
[../guides/adding-a-doc-fragment.md](../guides/adding-a-doc-fragment.md).

## Regenerating and the Generated-File Rule

After editing any docstring, run `invoke generate-doc` to refresh the MDX
reference under `docs/docs/references/plugins/` and `docs/docs/readme.mdx`.
**Never hand-edit those generated MDX files** — they are overwritten on the next
run. Edit the source docstrings or the Jinja2 templates in `docs/_templates/`
instead.
