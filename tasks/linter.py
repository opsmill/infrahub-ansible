import os
import sys
from pathlib import Path

from invoke import Context, task

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-LINT"

try:
    pass
except ImportError:
    sys.exit(
        "Please make sure to `pip install toml` or enable the Poetry shell and run `poetry install`."
    )

path = Path(__file__)
TASKS_DIR = str(path.parent)
REPO_BASE = os.path.join(TASKS_DIR, "..")


# ----------------------------------------------------------------------------
# Formatting tasks
# ----------------------------------------------------------------------------
@task
def format_black(context: Context):
    """Run black to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with black")
    exec_cmd = f"black {MAIN_DIRECTORY}/"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def format_autoflake(context: Context):
    """Run autoflack to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with autoflake")
    exec_cmd = f"autoflake --recursive --verbose --in-place --remove-all-unused-imports --remove-unused-variables {MAIN_DIRECTORY}"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task
def format_isort(context: Context):
    """Run isort to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with isort")
    exec_cmd = f"isort {MAIN_DIRECTORY}"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)


@task(name="format")
def format_all(context: Context):
    """This will run all formatter."""

    format_isort(context)
    format_autoflake(context)
    format_black(context)

    print(f" - [{NAMESPACE}] All formatters have been executed!")
