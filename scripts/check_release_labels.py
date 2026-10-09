"""Validate the explicit release bump label selected for a pull request."""

from __future__ import annotations

import argparse
import json
import re
import sys

BUMP_LABELS = frozenset({"changes/major", "changes/minor", "changes/patch"})
RELEASE_PR_PREFIX = "chore(release):"
# trigger-push-stable.yml names the branch `release/<version>` (no `v`) and
# validates <version> with this same pattern before it opens the pull request;
# a unit test fails if the two copies drift.
RELEASE_BRANCH_PATTERN = re.compile(r"release/[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?")
# trigger-push-stable.yml opens release pull requests with GH_INFRAHUB_BOT_TOKEN,
# a personal access token of this user account (not a GitHub App, which would
# surface as "<slug>[bot]").
RELEASE_PR_AUTHOR = "opsmill-bot"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels-json", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--head-ref", required=True)
    parser.add_argument("--author-login", required=True)
    parser.add_argument("--head-repository", required=True)
    parser.add_argument("--repository", required=True)
    return parser


def is_generated_release_pr(
    *, title: str, head_ref: str, author_login: str, head_repository: str, repository: str
) -> bool:
    """Return True only for the release pull request trigger-push-stable.yml opens.

    Every condition is required: the title alone is user-controlled, and a fork
    can name its branch anything. The title is matched by prefix only, so a
    maintainer retitling the release pull request does not lose the exemption.
    """
    return (
        title.startswith(RELEASE_PR_PREFIX)
        and RELEASE_BRANCH_PATTERN.fullmatch(head_ref) is not None
        and author_login == RELEASE_PR_AUTHOR
        and head_repository == repository
    )


def parse_labels(labels_json: str) -> list[str]:
    """Parse the label names GitHub passes as a JSON array."""
    raw = json.loads(labels_json)
    if not isinstance(raw, list) or not all(isinstance(label, str) for label in raw):
        msg = "Labels JSON must be an array of strings."
        raise TypeError(msg)
    return raw


def main(argv: list[str] | None = None) -> int:
    """Validate that a normal pull request has exactly one release label."""
    args = build_parser().parse_args(argv)

    if is_generated_release_pr(
        title=args.title,
        head_ref=args.head_ref,
        author_login=args.author_login,
        head_repository=args.head_repository,
        repository=args.repository,
    ):
        sys.stdout.write("Skipping label check for generated release pull request.\n")
        return 0

    try:
        labels = parse_labels(args.labels_json)
    except (json.JSONDecodeError, TypeError) as exc:
        sys.stderr.write(f"Invalid labels JSON: {exc}\n")
        return 1

    selected = sorted(BUMP_LABELS.intersection(labels))
    if len(selected) != 1:
        choices = ", ".join(sorted(BUMP_LABELS))
        found = ", ".join(selected) if selected else "none"
        sys.stderr.write(f"Pull requests must have exactly one release bump label ({choices}); found: {found}.\n")
        return 1

    sys.stdout.write(f"Release bump label: {selected[0]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
