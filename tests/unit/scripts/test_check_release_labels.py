# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Regression tests for the release bump label contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))

import check_release_labels

BUMP_LABELS = ["changes/major", "changes/minor", "changes/patch"]
REPOSITORY = "opsmill/infrahub-ansible"

# The release pull request trigger-push-stable.yml opens; each negative case
# below breaks exactly one of these fields.
RELEASE_PR = {
    "title": "chore(release): 1.2.3",
    "head_ref": "release/1.2.3",
    "author_login": "opsmill-bot",
    "head_repository": REPOSITORY,
}


def run(labels: list[str], **overrides: str) -> int:
    fields = {
        "title": "fix: example",
        "head_ref": "feature/example",
        "author_login": "contributor",
        "head_repository": "contributor/infrahub-ansible",
        **overrides,
    }
    return check_release_labels.main(
        [
            "--labels-json",
            json.dumps(labels),
            "--title",
            fields["title"],
            "--head-ref",
            fields["head_ref"],
            "--author-login",
            fields["author_login"],
            "--head-repository",
            fields["head_repository"],
            "--repository",
            REPOSITORY,
        ]
    )


def test_version_drafter_reads_only_bump_labels() -> None:
    config = yaml.safe_load((REPO_ROOT / ".github" / "version-drafter.yml").read_text())
    assert config == {
        "major-labels": ["changes/major"],
        "minor-labels": ["changes/minor"],
        "patch-labels": ["changes/patch"],
    }


def test_bump_labels_are_declared() -> None:
    declared = {label["name"] for label in yaml.safe_load((REPO_ROOT / ".github" / "labels.yml").read_text())}
    assert set(BUMP_LABELS) <= declared


@pytest.mark.parametrize("label", BUMP_LABELS)
def test_accepts_exactly_one_bump_label(label: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert run([label, "type/housekeeping"]) == 0
    assert label in capsys.readouterr().out


@pytest.mark.parametrize(
    "labels",
    [[], ["type/bug"], ["changes/patch", "changes/minor"]],
    ids=["none", "type-only", "conflicting"],
)
def test_rejects_missing_or_conflicting_bump_labels(labels: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert run(labels) == 1
    assert "exactly one" in capsys.readouterr().err


@pytest.mark.parametrize("labels_json", ["not json", '{"a": 1}', "[1]"])
def test_rejects_malformed_labels(labels_json: str, capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["--labels-json", labels_json, "--title", "t", "--head-ref", "h"]
    argv += ["--author-login", "a", "--head-repository", "r", "--repository", REPOSITORY]
    assert check_release_labels.main(argv) == 1
    assert "Invalid labels JSON" in capsys.readouterr().err


def test_exempts_generated_release_pr(capsys: pytest.CaptureFixture[str]) -> None:
    assert run([], **RELEASE_PR) == 0
    assert "generated release pull request" in capsys.readouterr().out


@pytest.mark.parametrize(
    "override",
    [
        {"title": "chore(release): 1.2.3 with reviewed changelog"},
        {"head_ref": "release/1.2.3-rc.1"},
    ],
    ids=["retitled", "prerelease"],
)
def test_exemption_survives_retitle_and_prerelease(override: dict[str, str]) -> None:
    assert run([], **{**RELEASE_PR, **override}) == 0


@pytest.mark.parametrize(
    "override",
    [
        {"author_login": "contributor"},
        {"author_login": "opsmill-bot[bot]"},
        {"head_repository": "fork/infrahub-ansible"},
        {"head_ref": "feature/1.2.3"},
        {"head_ref": "release/anything"},
        {"head_ref": "release/1.2.3/extra"},
        {"title": "fix: 1.2.3"},
    ],
    ids=[
        "other-author",
        "app-identity",
        "fork",
        "non-release-branch",
        "non-version-release-branch",
        "trailing-path",
        "non-release-title",
    ],
)
def test_near_miss_release_prs_still_need_a_bump_label(
    override: dict[str, str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert run([], **{**RELEASE_PR, **override}) == 1
    assert "exactly one" in capsys.readouterr().err
