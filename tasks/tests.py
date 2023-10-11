import os
import sys
from pathlib import Path

from invoke import Context, task

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-TEST"

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
# Tests tasks
# ----------------------------------------------------------------------------
@task
def tests_unit(context: Context):
    """Run unit tests"""
    print(f" - [{NAMESPACE}] Run unit tests")
    exec_cmd = f"docker-compose up --build --force-recreate --quiet-pull --exit-code-from unit unit"
    try:
        python_ver = context.config["infrahub_ansible"]["python_ver"]
    except KeyError:
        raise KeyError(
            "Could not find python_ver in context.config['infrahub_ansible']"
        )
    with context.cd(REPO_BASE):
        context.run(exec_cmd, env={"PYTHON_VER": python_ver})


@task
def tests_integration(context: Context):
    """Run integration tests"""
    print(f" - [{NAMESPACE}] Run integration tests")
    exec_cmd = f""
    with context.cd(REPO_BASE):
        context.run(exec_cmd)
