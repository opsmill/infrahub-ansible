# Fix Bug

Guided workflow for investigating and fixing a bug in the `opsmill.infrahub` Ansible collection.

## Instructions

Follow this structured workflow to investigate and fix a bug.

### 1. Understand the Bug

Ask the user for:
- **Description** — what's happening vs. what's expected
- **Module/plugin** affected (e.g., `node`, `inventory`, `lookup`)
- **Error message** or traceback (if available)
- **Reproduction steps** — playbook snippet, inventory config, etc.

### 2. Investigate

Read the relevant source files. Start from the user-facing layer and trace inward:

**For module bugs:**
```
plugins/modules/<name>.py          # Module stub (arg spec, docs)
plugins/action/<name>.py           # Action plugin (if exists)
plugins/module_utils/<name>.py     # Module class (if exists)
plugins/module_utils/infrahub_utils.py  # Base classes, SDK wrapper
plugins/module_utils/exception.py       # Exception handling
```

**For inventory bugs:**
```
plugins/inventory/inventory.py
plugins/module_utils/infrahub_utils.py  # InfrahubNodesProcessor
```

**For lookup bugs:**
```
plugins/lookup/lookup.py
plugins/module_utils/infrahub_utils.py  # InfrahubQueryProcessor
```

Understand the data flow (see `dev/knowledge/architecture.md`) and identify where the bug occurs.

### 3. Identify Root Cause

- Trace the execution path from user input to the error
- Check if the issue is in argument handling, SDK wrapper, API interaction, or result formatting
- Look for edge cases: missing parameters, None values, type mismatches, API response format changes

### 4. Implement Fix

- Make the minimal change needed to fix the bug
- Preserve existing behavior for non-buggy cases
- Follow existing code patterns (see `dev/knowledge/plugin-patterns.md`)
- Add or update error handling if the bug was caused by missing error handling

### 5. Write Tests

- Add a unit test that reproduces the bug (should fail without the fix)
- Verify the test passes with the fix
- Check that existing tests still pass

```bash
# Run unit tests
invoketests-unit

# Run sanity tests (ensure no regressions)
invoketests-sanity
```

### 6. Verify

- Run `invokelint` to check code style
- Run `invokeformat` to fix any formatting issues
- If documentation was affected, run `invokegenerate-doc`
- Confirm the fix addresses the original bug description

### 7. Summary

Provide the user with:
- Root cause explanation
- What was changed and why
- Any related issues or follow-up items
