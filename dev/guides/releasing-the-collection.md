# Releasing the Collection

How a release of `opsmill.infrahub` is cut, built, and published to Ansible
Galaxy. There is no manual version bump and no manual publish command, but
starting a release is deliberate: you merge to `stable` and then dispatch the
preparation. This guide documents what happens and the levers you pull. For the
branch model and commit conventions, see
[../guidelines/git-workflow.md](../guidelines/git-workflow.md).

## Step 1: merge develop into stable

Active development lands on `develop`. A release starts by merging `develop`
into `stable` (a PR from `develop` to `stable`). Merging does not by itself
prepare a release.

## Step 2: dispatch the release preparation

Run **Actions → Push on stable → Run workflow**, with `stable` selected as the
branch. `develop` is this repository's default branch, so the branch selector
offers it first and `prepare_release` refuses to run if it is left there.

Leave **version** empty to have `version-drafter-action` compute the next
version from the merged pull-request labels — that is the usual case. Fill it
in to state the version yourself, the way infrahub and infrahub-sdk-python do
for every release.

`.github/workflows/trigger-push-stable.yml` then runs two stages:

1. **`prepare_release`** — applies the resolved version: `uv version <next>`
   updates `pyproject.toml`, a `sed` rewrites the `version:` line in
   `galaxy.yml`, and `uv lock` refreshes the lock file. It then assembles
   `CHANGELOG.md` with `uv run towncrier build`, which consumes the news
   fragments in `changelog/`, and opens a
   **`chore(release): <version>` pull request** carrying all of it. Nothing is
   pushed to `stable` directly.
2. **Docs** — `workflow-changelog-and-docs.yml` regenerates the plugin
   reference with `uv run invoke generate-doc`, builds the site with
   `uv run invoke docusaurus`, and commits the result to `stable` as
   `chore: update docs`.

This used to fire on every push to `stable` instead. That re-opened or
force-updated the release pull request under whoever was reviewing it, so
deciding to release is now a separate act from merging.

If there are no news fragments, `prepare_release` **fails** rather than cut a
version with an empty changelog. Add a fragment — `housekeeping` is fine — and
dispatch again. It also fails when the resolved version is already the one in
`galaxy.yml`: under the old push trigger that was a silent skip, but a dispatch
is someone asking for a release, so having nothing to cut is reported rather
than passed over.

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

Publishing is triggered by the **published GitHub Release**, not by the merge to
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
5. Dispatch `trigger-push-stable.yml` from Actions with `stable` selected as the
   branch, leaving **version** empty unless you mean to state it. A
   `chore(release): <version>` pull request should appear, along with the docs
   commit.
6. Review the assembled changelog in that pull request and merge it. The tag
   and the GitHub Release are created automatically.
7. Confirm the new version appears on Ansible Galaxy — publishing the Release
   is what triggers the upload.
