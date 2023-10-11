import os
import sys
from pathlib import Path

from invoke import Context, task

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-DOCS"

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
# Documentation tasks
# ----------------------------------------------------------------------------
@task
def generate_doc(context: Context):
    """Generate the documentation ."""

    COMMANDS = (
        ("rm -rf ~/.ansible/collections/ansible_collections/infrahub"),
        ("rm -f infrahub-infrahub-*.tar.gz"),
        ("rm -rf tests/output"),
        ("rm -rf .pytest_cache"),
        ("ansible-galaxy collection build --force --verbose ."),
        ("ansible-galaxy collection install infrahub-infrahub-*.tar.gz -f"),
        (
            "antsibull-docs collection --use-current --squash-hierarchy --dest-dir docs/plugins/ infrahub.infrahub"
        ),
    )

    print(f" - [{NAMESPACE}] Generate documentation")
    for exec_cmd in COMMANDS:
        with context.cd(REPO_BASE):
            context.run(exec_cmd)
