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

1. **Skip guard** — if the last commit is a `chore(release):` commit (the merge
   of a release pull request), the run stops, so preparing a release cannot
   trigger preparing another.
2. **`prepare_release`** — computes the next version with
   `version-drafter-action` (from the merged PR labels), then applies it:
   `uv version <next>` updates `pyproject.toml`, a `sed` rewrites the
   `version:` line in `galaxy.yml`, and `uv lock` refreshes the lock file. It
   then assembles `CHANGELOG.md` with `uv run towncrier build`, which consumes
   the news fragments in `changelog/`, and opens a
   **`chore(release): <version>` pull request** carrying all of it. Nothing is
   pushed to `stable` directly.
3. **Docs** — `workflow-changelog-and-docs.yml` regenerates the plugin
   reference with `uv run invoke generate-doc`, builds the site with
   `uv run invoke docusaurus`, and commits the result to `stable` as
   `chore: update docs`.

If there are no news fragments, `prepare_release` **fails** rather than cut a
version with an empty changelog. Add a fragment — `housekeeping` is fine — and
re-run.

## Merging the release pull request

The release pull request is the review point: it contains only the version bump
and the assembled changelog, so what users will read is visible in the diff.
Merging it is what authorises the release.

On merge, `.github/workflows/release-publish.yml` creates the tag and publishes
the GitHub Release with that changelog section as the body. It decides whether
to act by checking whether a tag already exists for the version in `galaxy.yml`,
so it behaves the same whether the pull request was squashed, rebased or merged.

`galaxy.yml` is the source of truth for the published version — you never edit
it by hand for a release; the workflow does. The changelog is `CHANGELOG.md`,
assembled by [towncrier](https://towncrier.readthedocs.io/) from per-change
fragments; it is never hand-edited.

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
3. Confirm the changes going out carry news fragments in `changelog/` —
   `uv run towncrier build --draft --version <next>` previews exactly what the
   release will say.
4. Merge `develop` into `stable`.
5. Watch `trigger-push-stable.yml`: a `chore(release): <version>` pull request
   should appear, along with the docs commit.
6. Review the assembled changelog in that pull request and merge it. The tag
   and the GitHub Release are created automatically.
7. Confirm the new version appears on Ansible Galaxy — publishing the Release
   is what triggers the upload.
