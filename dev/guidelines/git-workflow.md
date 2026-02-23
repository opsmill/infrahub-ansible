# Git Workflow

## Branch Model

| Branch | Purpose |
|--------|---------|
| `develop` | Active development — PRs target here |
| `stable` | Release branch — merged from develop for releases |

## PR Conventions

- PRs target `develop` unless they are hotfixes for `stable`
- CI runs on every PR to `develop`: linting, sanity tests, unit tests
- CI runs on every PR to `stable`: same checks plus documentation build and publish checks

## CI Workflows

| Trigger | Workflow | What runs |
|---------|----------|-----------|
| PR to `develop` | `trigger-pr-develop.yml` | Linter + Ansible tests |
| PR to `stable` | `trigger-pr-stable.yml` | Linter + Ansible tests + changelog/docs |
| Push to `stable` | `trigger-push-stable.yml` | Publish + release |
| Push to docs on `stable` | `trigger-push-docs-stable.yml` | Docs sync |
| Release | `trigger-release.yml` | Galaxy publish |

## Changelog

The changelog is in `CHANGELOG.rst` (reStructuredText format). It's updated as part of the release process.

Release drafts are managed by the `workflow-release-drafter.yml` workflow.

## Version Bumping

The collection version is tracked in `galaxy.yml`:

```yaml
version: 1.7.0
```

Note: `pyproject.toml` has its own version field, but `galaxy.yml` is the source of truth for the Ansible Galaxy published version.

## Building the Collection

```bash
# Build the collection tarball
invoke galaxy-build

# Or directly:
ansible-galaxy collection build --output-path ./dist/ .
```

The built artifact goes to `build/` or `dist/`.

## Commit Messages

Follow conventional commit style where practical:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `chore:` for maintenance tasks
- `test:` for test additions/changes

## What Gets Published

The `galaxy.yml` `build_ignore` list excludes from the published collection:
- `venv`, `ansible_collections`
- `tests/output`
- `.pytest_cache`, `.vscode`
- `*.tar.gz`, `poetry.lock`, `pyproject.toml`
