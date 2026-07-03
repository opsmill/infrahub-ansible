# Releasing the Collection

How a release of `opsmill.infrahub` is cut, built, and published to Ansible
Galaxy. The release is **automated off the `stable` branch** — there is no
manual version bump and no manual publish command. This guide documents what
happens and the one manual lever you pull. For the branch model and commit
conventions, see [../guidelines/git-workflow.md](../guidelines/git-workflow.md).

## The one manual step: merge develop into stable

Active development lands on `develop`. A release is started by merging `develop`
into `stable` (a PR from `develop` to `stable`). Everything after the push to
`stable` is automated.

## What runs automatically on push to stable

`.github/workflows/trigger-push-stable.yml` fires on every push to `stable`
(ignoring docs-only changes) and runs three stages:

1. **Skip guard** — if the last commit is the bot's own
   `chore: update pyproject.toml & galaxy.yml`, the run stops, so the version
   bump does not re-trigger itself.
2. **`prepare_release`** — computes the next version with
   `version-drafter-action` (from the merged PR labels), then applies it:
   `uv version <next>` updates `pyproject.toml`, a `sed` rewrites the
   `version:` line in `galaxy.yml`, `uv lock` refreshes the lock file, and the
   `opsmill-bot` account commits `pyproject.toml`, `galaxy.yml`, and `uv.lock`
   back to `stable` as `chore: update pyproject.toml & galaxy.yml`.
3. **Docs + release** — it then calls two reusable workflows:
   - `workflow-changelog-and-docs.yml` regenerates the plugin reference with
     `uv run invoke generate-doc`, builds the site with `uv run invoke
     docusaurus`, and commits the result to `stable` as `chore: update docs`.
   - `workflow-release-drafter.yml` tags the computed version, pushes the tag,
     and runs `release-drafter` (config `.github/release-drafter.yml`) to draft
     and publish the GitHub Release.

`galaxy.yml` is the source of truth for the published version — note you never
edit it by hand for a release; the workflow does. The changelog lives in
`CHANGELOG.rst` (reStructuredText) and is maintained through the release-drafter
flow, not a hand-edited changelog fragment system.

## Publishing to Ansible Galaxy

Publishing is triggered by the **published GitHub Release**, not by the push to
`stable`. `.github/workflows/trigger-release.yml` listens for
`release: published` and calls `workflow-publish.yml`, which:

- builds the collection with `ansible-galaxy collection build --output-path
  build`,
- uploads the resulting tarball to the GitHub Release assets, and
- publishes to Ansible Galaxy via `artis3n/ansible_galaxy_collection`, using the
  `INFRAHUB_GALAXY_API_TOKEN` secret and the release tag as the version.

There is **no `invoke` publish task** — `tasks/galaxy.py` exposes only
`galaxy-build`. Publishing to Galaxy only happens through the release CI above.

## Building the tarball locally

To produce the same artifact CI builds — for inspection or a manual/offline
install — run:

```bash
invoke galaxy-build
# add --force to overwrite an existing build/ artifact
```

This runs `ansible-galaxy collection build . --output-path build`, writing
`build/opsmill-infrahub-<version>.tar.gz`. This is only a local build step; it
does not publish anything.

## Release checklist

1. Ensure `develop` is green (`invoke lint`, `tests-sanity`, `tests-unit`).
2. Confirm PRs are labelled so `version-drafter-action` computes the intended
   semver bump.
3. Merge `develop` into `stable`.
4. Watch `trigger-push-stable.yml`: version bump commit, docs commit, and the
   drafted GitHub Release should all appear.
5. Publish the GitHub Release to trigger the Galaxy publish, and confirm the new
   version appears on Ansible Galaxy.
