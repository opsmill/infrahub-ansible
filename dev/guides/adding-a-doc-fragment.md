# Adding a Doc Fragment

Doc fragments let several plugins share one copy of a `DOCUMENTATION` options
block. Reach for one when the same options would otherwise be pasted into more
than one plugin's docstring.

## When and Why

Add a fragment when an option (or a group of options) is identical across
plugins — connection settings, common flags, a shared `tags` field. A single
source means a description fix or a new shared option lands everywhere at once,
and `ansible-test sanity` validates the shared block once. Do not add a fragment
for options that are genuinely plugin-specific.

## Where Fragments Live

All fragments are attributes of the `ModuleDocFragment` class in
[`plugins/doc_fragments/fragments.py`](../../plugins/doc_fragments/fragments.py).
Today it defines:

- `BASE` — the common connection options (`api_endpoint`, `token`, `timeout`,
  `branch`, `validate_certs`) plus the `requirements` list.
- `TAGS` — the shared `tags` option.

## Adding One

1. Add a new raw-string attribute to `ModuleDocFragment`. Keep the same YAML
   shape as the existing fragments — a top-level `options:` map (and, if needed,
   `requirements:`):

   ```python
   class ModuleDocFragment:
       BASE = r"""..."""

       MY_FRAGMENT = r"""
   options:
     my_option:
       description:
         - What this option does.
       required: False
       type: str
   """
   ```

2. Reference it from each plugin's `DOCUMENTATION` via
   `extends_documentation_fragment`, using the collection-qualified name:

   ```yaml
   extends_documentation_fragment:
     - opsmill.infrahub.my_fragment
   ```

   (Ansible-builtin fragments such as `constructed` and `inventory_cache` —
   used by the inventory plugin — are referenced unqualified.)

3. Remove the now-duplicated options from each plugin's inline `options:` block
   so the fragment is the only source.

## Regenerate the Docs

Fragments are expanded into the rendered reference pages. After changing a
fragment or its consumers, run `invoke generate-doc` and verify with
`invoke tests-sanity`. See [../guidelines/module-docstrings.md](../guidelines/module-docstrings.md)
and [../guidelines/documentation.md](../guidelines/documentation.md) for the
docstring rules and the generation pipeline.
