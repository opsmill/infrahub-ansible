"""Tests for scripts/update_infrahub_pins.py, the Infrahub bump pin editor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = next(
    parent / "scripts" / "update_infrahub_pins.py"
    for parent in Path(__file__).resolve().parents
    if (parent / "scripts" / "update_infrahub_pins.py").exists()
)
_spec = importlib.util.spec_from_file_location("update_infrahub_pins", SCRIPT)
assert _spec
assert _spec.loader
pins = importlib.util.module_from_spec(_spec)
sys.modules["update_infrahub_pins"] = pins
_spec.loader.exec_module(pins)

PYPROJECT = """[project]
dependencies = [
    "infrahub-sdk[all,ctl]>=1.23.0,<2",
]

[dependency-groups]
dev = [
    "infrahub-testcontainers>=1.11.5,<2",
    "pytest>=8",
]
"""


def make_repo(tmp_path: Path, pyproject: str = PYPROJECT, **files: str) -> Path:
    (tmp_path / "pyproject.toml").write_text(pyproject)
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    return tmp_path


def test_moves_testcontainers_lower_bound_and_keeps_the_rest(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    assert pins.update_pins(root, "1.11.7", "", []) == ["pyproject.toml"]
    text = (root / "pyproject.toml").read_text()
    assert '"infrahub-testcontainers>=1.11.7,<2"' in text
    assert '"infrahub-sdk[all,ctl]>=1.23.0,<2"' in text


def test_moves_sdk_lower_bound_and_keeps_extras(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    pins.update_pins(root, "", "1.24.0", [])
    assert '"infrahub-sdk[all,ctl]>=1.24.0,<2"' in (root / "pyproject.toml").read_text()


@pytest.mark.parametrize("operator", ["==", ">=", "~="])
def test_keeps_the_operator(tmp_path: Path, operator: str) -> None:
    root = make_repo(
        tmp_path,
        f'[dependency-groups]\nintegration = ["infrahub-testcontainers{operator}1.11.6"]\n',
    )
    pins.update_pins(root, "1.11.7", "", [])
    assert f'"infrahub-testcontainers{operator}1.11.7"' in (root / "pyproject.toml").read_text()


def test_skips_testcontainers_when_not_declared(tmp_path: Path) -> None:
    root = make_repo(tmp_path, '[project]\ndependencies = ["infrahub-sdk>=1.23.0"]\n')
    assert pins.update_pins(root, "1.11.7", "", []) == []


def test_fails_when_sdk_is_not_declared(tmp_path: Path) -> None:
    root = make_repo(tmp_path, '[dependency-groups]\ndev = ["infrahub-testcontainers>=1.11.5"]\n')
    with pytest.raises(pins.PinError, match="infrahub-sdk is not declared"):
        pins.update_pins(root, "", "1.24.0", [])


def test_refuses_to_lower_a_pin(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    with pytest.raises(pins.PinError, match="refusing to lower"):
        pins.update_pins(root, "1.11.0", "", [])
    assert (root / "pyproject.toml").read_text() == PYPROJECT


def test_same_version_changes_nothing(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    assert pins.update_pins(root, "1.11.5", "", []) == []


def test_moves_every_image_version_form(tmp_path: Path) -> None:
    dockerfile = (
        "ARG INFRAHUB_BASE_VERSION=1.11.5\nFROM registry.opsmill.io/opsmill/infrahub:${INFRAHUB_BASE_VERSION}\n"
    )
    compose = (
        "services:\n"
        "  server:\n"
        "    image: registry.opsmill.io/opsmill/infrahub:${VERSION:-1.11.5}\n"
        "  worker:\n"
        "    image: opsmill/infrahub-solution-demo:${INFRAHUB_BASE_VERSION:-1.11.5}\n"
    )
    ci = (
        "      - run: docker build --build-arg INFRAHUB_BASE_VERSION=1.11.5\n"
        "          -t opsmill/infrahub-solution-demo:1.11.5 .\n"
        '          INFRAHUB_TESTING_IMAGE_VER: "1.11.5"\n'
    )
    root = make_repo(tmp_path, **{"Dockerfile": dockerfile, "docker-compose.yml": compose, "ci.yml": ci})
    changed = pins.update_pins(root, "1.11.7", "", ["Dockerfile", "docker-compose.yml", "ci.yml"])
    assert changed == ["pyproject.toml", "Dockerfile", "docker-compose.yml", "ci.yml"]
    for name in ("Dockerfile", "docker-compose.yml", "ci.yml"):
        text = (root / name).read_text()
        assert "1.11.5" not in text, name
        assert "1.11.7" in text, name
    assert "FROM registry.opsmill.io/opsmill/infrahub:${INFRAHUB_BASE_VERSION}" in (root / "Dockerfile").read_text()


def test_fails_on_an_image_file_with_no_version(tmp_path: Path) -> None:
    root = make_repo(tmp_path, Dockerfile="FROM python:3.12-slim\n")
    with pytest.raises(pins.PinError, match="names no Infrahub version"):
        pins.update_pins(root, "1.11.7", "", ["Dockerfile"])


def test_refuses_to_lower_an_image_version(tmp_path: Path) -> None:
    root = make_repo(tmp_path, Dockerfile="ARG INFRAHUB_BASE_VERSION=1.12.0\n")
    with pytest.raises(pins.PinError, match="refusing to lower"):
        pins.update_pins(root, "1.11.7", "", ["Dockerfile"])


@pytest.mark.parametrize(
    ("infrahub", "sdk", "images", "message"),
    [
        ("", "", [], "pass --infrahub-version"),
        ("latest", "", [], "does not look like a version"),
        ("", "1.24.0", ["Dockerfile"], "--image-file needs --infrahub-version"),
    ],
)
def test_rejects_bad_arguments(tmp_path: Path, infrahub: str, sdk: str, images: list[str], message: str) -> None:
    root = make_repo(tmp_path)
    with pytest.raises(pins.PinError, match=message):
        pins.update_pins(root, infrahub, sdk, images)


def test_main_reports_changed_files_and_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = make_repo(tmp_path)
    assert pins.main(["--root", str(root), "--infrahub-version", "1.11.7"]) == 0
    assert "changed: pyproject.toml" in capsys.readouterr().out
    assert pins.main(["--root", str(root), "--infrahub-version", "1.11.0"]) == 1
    assert "refusing to lower" in capsys.readouterr().err
