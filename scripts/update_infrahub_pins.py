"""Move this repository's Infrahub version pins to a new release.

Used by `.github/workflows/update-infrahub.yml`, and identical in every OpsMill
demo and solution repository. It edits each pin in place instead of letting
`uv add` rewrite the whole requirement, so the operator, the upper bound, the
extras and the dependency group stay as they are.

- `--infrahub-version` moves the lower bound of `infrahub-testcontainers` in
  pyproject.toml, and the Infrahub image version in every `--image-file`.
- `--sdk-version` moves the lower bound of `infrahub-sdk` in pyproject.toml.

The script refuses to lower a version, and fails when a listed image file holds
no Infrahub version it recognises. It does not run `uv lock`; the workflow does.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERSION_PATTERN = r"\d+(?:\.\d+)*(?:[a-zA-Z0-9.+-]*[a-zA-Z0-9])?"
VERSION = re.compile(rf"^{VERSION_PATTERN}$")

# Where an image file names the Infrahub version. Each pattern captures the text
# before the version in group 1 and the version in group 2.
IMAGE_VERSION_PATTERNS = (
    # Dockerfile `ARG INFRAHUB_BASE_VERSION=1.11.7` and shell or YAML assignments.
    re.compile(rf"(\bINFRAHUB_BASE_VERSION[=:][ \t]*[\"']?)({VERSION_PATTERN})"),
    # Compose defaults: `${INFRAHUB_BASE_VERSION:-1.11.7}`, `${VERSION:-1.11.7}`.
    re.compile(rf"(\$\{{(?:INFRAHUB_BASE_VERSION|VERSION):-)({VERSION_PATTERN})(?=\}})"),
    # Test image tag read by infrahub-testcontainers.
    re.compile(rf"(\bINFRAHUB_TESTING_IMAGE_VER[=:][ \t]*[\"']?)({VERSION_PATTERN})"),
    # Image references tagged with the Infrahub version: `opsmill/infrahub:1.11.7`,
    # `opsmill/infrahub-enterprise:1.11.7`, `opsmill/infrahub-solution-arista-avd:1.11.7`.
    re.compile(rf"(\bopsmill/infrahub(?:-[a-z0-9]+)*:)({VERSION_PATTERN})"),
)


class PinError(Exception):
    """A pin could not be moved safely."""


def release_tuple(version: str) -> tuple[int, ...]:
    """Return the numeric release segments of a version, ignoring any suffix."""
    match = re.match(r"\d+(?:\.\d+)*", version)
    if not match:
        msg = f"'{version}' does not start with a release number"
        raise PinError(msg)
    return tuple(int(part) for part in match.group(0).split("."))


def check_not_lower(name: str, current: str, new: str) -> None:
    """Refuse to move a pin to an older release."""
    if release_tuple(new) < release_tuple(current):
        msg = f"{name} is pinned at {current}; refusing to lower it to {new}"
        raise PinError(msg)


def bump_requirement(text: str, package: str, version: str) -> tuple[str, str | None]:
    """Move the first version of `package` in a quoted PEP 508 requirement.

    Returns the new text and the previous version, or `None` when the package
    is not declared.
    """
    pattern = re.compile(rf"(\"{re.escape(package)}(?:\[[^\]]*\])?[ \t]*(?:===|==|>=|~=|>)[ \t]*)({VERSION_PATTERN})")
    matches = list(pattern.finditer(text))
    if not matches:
        return text, None
    current = matches[0].group(2)
    for match in matches:
        check_not_lower(package, match.group(2), version)
    return pattern.sub(lambda m: f"{m.group(1)}{version}", text), current


def bump_image_file(text: str, version: str) -> tuple[str, list[str]]:
    """Move every Infrahub image version in an image file.

    Returns the new text and the versions it replaced.
    """
    found: list[str] = []

    def replace(match: re.Match[str]) -> str:
        found.append(match.group(2))
        return f"{match.group(1)}{version}"

    for pattern in IMAGE_VERSION_PATTERNS:
        text = pattern.sub(replace, text)
    return text, found


def check_arguments(infrahub_version: str, sdk_version: str, image_files: list[str]) -> None:
    """Reject argument combinations the bump cannot apply."""
    for name, value in (("--infrahub-version", infrahub_version), ("--sdk-version", sdk_version)):
        if value and not VERSION.match(value):
            msg = f"{name} '{value}' does not look like a version"
            raise PinError(msg)
    if not infrahub_version and not sdk_version:
        msg = "pass --infrahub-version, --sdk-version, or both"
        raise PinError(msg)
    if image_files and not infrahub_version:
        msg = "--image-file needs --infrahub-version"
        raise PinError(msg)


def bump_pyproject(text: str, infrahub_version: str, sdk_version: str) -> str:
    """Return pyproject.toml with the requested requirement pins moved."""
    if infrahub_version:
        text, current = bump_requirement(text, "infrahub-testcontainers", infrahub_version)
        if current is None:
            sys.stdout.write("infrahub-testcontainers is not declared; leaving it.\n")
    if sdk_version:
        text, current = bump_requirement(text, "infrahub-sdk", sdk_version)
        if current is None:
            msg = "infrahub-sdk is not declared in pyproject.toml"
            raise PinError(msg)
    return text


def bump_listed_image_file(name: str, text: str, version: str) -> str:
    """Return an image file with its Infrahub versions moved, or fail if it names none."""
    text, found = bump_image_file(text, version)
    if not found:
        msg = f"{name} is listed as an image file but names no Infrahub version"
        raise PinError(msg)
    for current in found:
        check_not_lower(name, current, version)
    return text


def update_pins(root: Path, infrahub_version: str, sdk_version: str, image_files: list[str]) -> list[str]:
    """Apply every requested bump under `root` and return the files it changed.

    Every file is checked before any is written, so a refused bump leaves the
    working tree untouched.
    """
    check_arguments(infrahub_version, sdk_version, image_files)
    originals = {name: (root / name).read_text(encoding="utf-8") for name in ["pyproject.toml", *image_files]}
    updated = {"pyproject.toml": bump_pyproject(originals["pyproject.toml"], infrahub_version, sdk_version)}
    for name in image_files:
        updated[name] = bump_listed_image_file(name, originals[name], infrahub_version)

    changed = [name for name, text in updated.items() if text != originals[name]]
    for name in changed:
        (root / name).write_text(updated[name], encoding="utf-8")
    return changed


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--infrahub-version", default="")
    parser.add_argument("--sdk-version", default="")
    parser.add_argument(
        "--image-file",
        action="append",
        default=[],
        help="file that names the Infrahub image version; repeat for each file",
    )
    parser.add_argument("--root", type=Path, default=Path())
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the bump and print each changed file on its own line."""
    args = build_parser().parse_args(argv)
    try:
        changed = update_pins(args.root, args.infrahub_version, args.sdk_version, args.image_file)
    except (PinError, OSError) as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 1
    for name in changed:
        sys.stdout.write(f"changed: {name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
