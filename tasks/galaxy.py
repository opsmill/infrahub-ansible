from invoke import Context, task

from .utils import ESCAPED_REPO_PATH

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-GALAXY"


# ----------------------------------------------------------------------------
# Ansible Galaxy tasks
# ----------------------------------------------------------------------------
@task(optional=["force"])
def galaxy_build(context: Context, force=False):
    """Build the collection."""
    print(f" - [{NAMESPACE}] Building collection with ansible-galaxy")
    exec_cmd = f"ansible-galaxy collection build {MAIN_DIRECTORY} -output-path build"
    if force:
        exec_cmd += " --force"
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd)
