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
| Push to `stable` | `trigger-push-stable.yml` | Version bump + changelog → opens the release PR |
| Push to docs on `stable` | `trigger-push-docs-stable.yml` | Docs sync |
| Merge of the release PR | `release-publish.yml` | Tag + publish the GitHub Release |
| Release | `trigger-release.yml` | Galaxy publish |
| Any PR | `changelog-check.yml` | Requires a news fragment |

## Changelog

`CHANGELOG.md` is assembled by [towncrier](https://towncrier.readthedocs.io/) from news
fragments in `changelog/` — one per change, written in the same PR that makes the change.
CI fails a pull request that adds neither a fragment nor the `ci/skip-changelog` label.

```bash
uv run towncrier create -c "Fixed the thing" 42.fixed.md   # <issue>.<type>.md
uv run towncrier build --draft --version 1.8.4             # preview
```

Types: `security`, `removed`, `deprecated`, `added`, `changed`, `fixed`, `housekeeping`.
Without an issue or PR number, use a descriptive slug prefixed with `+`, e.g.
`+inventory-batching.fixed.md`.

Never run `towncrier build` or edit `CHANGELOG.md` by hand — the release workflow does it and
opens a `chore(release):` pull request with the result.

> `CHANGELOG.rst` was the previous, hand-maintained changelog. It fell out of use — four
> releases shipped without an entry — and has been replaced by `CHANGELOG.md`.

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
- `*.tar.gz`, `uv.lock`, `pyproject.toml`
