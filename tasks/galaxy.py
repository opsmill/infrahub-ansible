import os
import sys
from pathlib import Path

from invoke import Context, task

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-GALAXY"

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
# Ansible Galaxy tasks
# ----------------------------------------------------------------------------
@task(optional=["force"])
def galaxy_build(context: Context, force=False):
    """Build the collection."""
    print(f" - [{NAMESPACE}] Building collection with ansible-galaxy")
    exec_cmd = f"ansible-galaxy collection build {MAIN_DIRECTORY}"
    if force:
        exec_cmd += " --force"
    with context.cd(REPO_BASE):
        context.run(exec_cmd)
