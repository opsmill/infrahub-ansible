# Python Guidelines

## Tooling

- **Formatter/Linter:** [Ruff](https://docs.astral.sh/ruff/) (version pinned in `pyproject.toml`)
- **Config:** `pyproject.toml` under `[tool.ruff]`

## Ruff Configuration

### Line Length

```toml
[tool.ruff]
line-length = 120

[tool.ruff.lint.pycodestyle]
max-line-length = 150
```

- Target line length: **120 characters**
- Hard limit (pycodestyle): **150 characters**

### Rule Selection

```toml
[tool.ruff.lint]
preview = true
select = ["ALL"]
```

All rules are enabled with preview mode. Specific categories and rules are then ignored:

**Permanently ignored categories:**

- `COM812` — trailing comma (conflicts with formatter)
- `CPY` — copyright notices (handled manually)
- `D` — docstring conventions (pydocstyle)
- `DOC` — documentation warnings
- `ISC` — implicit string concatenation
- `FBT` — boolean trap

**Ignored for investigation:**

- `PT` (pytest style), `PGH` (pygrep-hooks), `ERA` (eradicate), `SLF001` (private member access), `EM` (error messages), `TRY` (tryceratops), `TD`/`FIX` (todos), `TID` (tidy imports), `G` (logging format), `FLY` (flynt), `RSE` (raise), `BLE` (blind exception), `A` (builtins shadowing)

**Ignored for later reactivation:**

- `B904`, `C408`, `E402`, `INP001`, `N806`, `PLC0415`, `PLR0912`, `PLR6201`, `PLR6301`, `PLR1702`, `PLR0913`, `RET504`

### Per-File Ignores

```toml
[tool.ruff.lint.per-file-ignores]
"docs/**/*.py" = ["ALL"]
"plugins/**/*.py" = ["ANN201", "ANN202", "ANN204", "ANN401", "F404", "UP001", "UP010"]
"tasks/*.py" = ["T201"]
```

- **Plugin files** skip some annotation and future-import rules (Ansible compatibility)
- **Task files** allow `print()` calls
- **Doc generation** skips all rules

### Format Configuration

```toml
[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
```

- **Double quotes** for strings
- **Spaces** for indentation (not tabs)
- **Preserve** trailing commas

### Import Sorting

```toml
[tool.ruff.lint.isort]
known-first-party = ["infrahub"]
```

### Complexity

```toml
[tool.ruff.lint.mccabe]
max-complexity = 19
```

## Running Linters

```bash
# Check formatting and lint (CI-style, no changes)
invoke lint

# Auto-fix formatting and lint issues
invoke format
```

Or directly:

```bash
# Check
ruff format --check --diff .
ruff check --diff .

# Fix
ruff format .
ruff check --fix .
```

## Additional Linters

- **yamllint** — YAML formatting (config: `.yamllint.yml`)
- **ansible-lint** — Ansible-specific linting (config: `.ansible-lint`)
- **rumdl** — Markdown formatting (config: `[tool.rumdl]` in `pyproject.toml`)
- **Vale** — Documentation prose style (config: `.vale.ini`)

## Python Version

```toml
requires-python = ">=3.11,<3.15"
```

Target Python 3.11+ but maintain the Ansible `__future__` imports and `__metaclass__ = type` boilerplate for `ansible-test sanity` compliance.

## Type Hints

Use modern type hints (`str | None` not `Optional[str]`). The `from __future__ import annotations` import is present in all files.

### mypy

`invoke lint` runs mypy, and so does CI's `python-lint` job. To run it on its own:

```bash
uv run mypy .
```

`warn_return_any`, `disallow_untyped_defs`, and `warn_unused_ignores` are all on
(`[tool.mypy]` in `pyproject.toml`), so an unannotated helper or a stale `# type: ignore` fails the
build. Only `tests/` is excluded — every file under `plugins/` is checked.

Where the SDK's own types defeat the checker — `InfrahubNodeSync.__getattr__` returning a union, the
`Literal`-keyed `get`/`filters` overloads, the two mutually exclusive `HAS_INFRAHUBCLIENT` blocks —
suppress at the site with a narrow `# type: ignore[code]` and say why in a comment. Do not widen the
config: `warn_unused_ignores` retires an inline ignore once it stops being needed, and it cannot do
that for an exclusion.

## Dependencies

Managed via uv:

```bash
uv sync                           # Install all deps
uv sync --group dev               # Include dev deps
uv add <package>                  # Add a dependency
uv add --group dev <package>      # Add a dev dependency
```
