# Add Module

Scaffold a new Ansible module for the `opsmill.infrahub` collection.

## Instructions

You are adding a new module to this Ansible collection. Follow these steps carefully.

### 1. Gather Information

Ask the user for:
- **Module name** (e.g., `artifact_generate`)
- **Purpose** — what the module does
- **Parameters** — what arguments it accepts beyond the standard ones (api_endpoint, token, timeout, branch, validate_certs)
- **Pattern** — action plugin pattern (API calls only) or module_utils pattern (state management with idempotency)
- **Return values** — what the module returns on success

### 2. Read Existing Patterns

Before writing any code, read these files to match existing conventions:

```
plugins/modules/artifact_generate.py    # Action plugin pattern example
plugins/modules/node.py                 # Module utils pattern example
plugins/action/artifact_generate.py     # Action plugin implementation
plugins/module_utils/node.py            # Module utils implementation
plugins/module_utils/infrahub_utils.py  # Base classes and SDK wrapper
dev/knowledge/plugin-patterns.md        # Pattern documentation
dev/guides/creating-a-module.md         # Step-by-step guide
```

### 3. Create Files

Based on the chosen pattern, create:

**Always:**
- `plugins/modules/<name>.py` — module stub with DOCUMENTATION, EXAMPLES, RETURN

**Action plugin pattern:**
- `plugins/action/<name>.py` — ActionModule with run() method

**Module utils pattern:**
- `plugins/module_utils/<name>.py` — subclass of InfrahubModule
- Update `plugins/modules/<name>.py` to import and call the module_utils class

### 4. Verify

- Run `invoke tests-sanity` to check Ansible compliance
- Run `invoke generate-doc` to regenerate documentation
- Ensure the module appears in `ansible-doc opsmill.infrahub.<name>`

### 5. Conventions Checklist

Verify all of these:
- [ ] Copyright header with current year
- [ ] `from __future__ import absolute_import, annotations, division, print_function`
- [ ] `__metaclass__ = type`
- [ ] Complete DOCUMENTATION with all options documented
- [ ] At least 2 EXAMPLES showing common usage
- [ ] RETURN documenting all return values
- [ ] `no_log=True` on token parameter
- [ ] Conditional `HAS_INFRAHUBCLIENT` import check
- [ ] Environment variable fallbacks for api_endpoint and token
- [ ] Consistent with existing module naming and style
