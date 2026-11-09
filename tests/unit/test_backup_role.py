# Copyright (c) 2026 Opsmill
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""Regression tests for backup role task resolution."""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCKER_TASKS = REPO_ROOT / "roles" / "backup" / "tasks" / "docker" / "main.yml"


@pytest.mark.parametrize(
    ("task_name", "task_file"),
    [
        ("Validate Docker platform inputs", "validate.yml"),
        ("Setup systemd", "setup_systemd.yml"),
    ],
)
def test_docker_task_imports_are_anchored_to_the_role(task_name: str, task_file: str):
    """Caller-owned task files must not replace the backup role's platform tasks."""
    tasks = yaml.safe_load(DOCKER_TASKS.read_text(encoding="utf-8"))
    task = next(item for item in tasks if item["name"] == task_name)

    assert task["ansible.builtin.import_tasks"] == f"{{{{ role_path }}}}/tasks/docker/{task_file}"
