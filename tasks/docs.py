from invoke import Context, task

from .utils import ESCAPED_REPO_PATH

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-DOCS"


# ----------------------------------------------------------------------------
# Documentation tasks
# ----------------------------------------------------------------------------
@task
def generate_doc(context: Context):
    """Generate the documentation ."""

    COMMANDS = (
        ("rm -rf ~/.ansible/collections/ansible_collections/infrahub"),
        ("rm -f opsmill-infrahub-*.tar.gz"),
        ("rm -rf tests/output"),
        ("rm -rf .pytest_cache"),
        ("ansible-galaxy collection build --force --verbose ."),
        ("ansible-galaxy collection install opsmill-infrahub-*.tar.gz -f"),
        ("antsibull-docs collection --use-current --squash-hierarchy --dest-dir docs/plugins/ opsmill.infrahub"),
    )

    print(f" - [{NAMESPACE}] Generate documentation")
    for exec_cmd in COMMANDS:
        with context.cd(ESCAPED_REPO_PATH):
            context.run(exec_cmd)
