from invoke import Context, task

from .utils import ESCAPED_REPO_PATH

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-TEST"


# ----------------------------------------------------------------------------
# Tests tasks
# ----------------------------------------------------------------------------
@task
def tests_sanity(context: Context):
    """Run sanity tests"""
    print(f" - [{NAMESPACE}] Run sanity tests")
    exec_cmd = f"docker-compose up --build --force-recreate --quiet-pull --exit-code-from sanity sanity"
    try:
        python_ver = context.config["infrahub_ansible"]["python_ver"]
    except KeyError:
        raise KeyError("Could not find python_ver in context.config['infrahub_ansible']")
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd, env={"PYTHON_VER": python_ver})


@task
def tests_unit(context: Context):
    """Run unit tests"""
    print(f" - [{NAMESPACE}] Run unit tests")
    exec_cmd = f"docker-compose up --build --force-recreate --quiet-pull --exit-code-from unit unit"
    try:
        python_ver = context.config["infrahub_ansible"]["python_ver"]
    except KeyError:
        raise KeyError("Could not find python_ver in context.config['infrahub_ansible']")
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd, env={"PYTHON_VER": python_ver})


@task
def tests_integration(context: Context):
    """Run integration tests"""
    print(f" - [{NAMESPACE}] Run integration tests")
    exec_cmd = f"docker-compose up --build --force-recreate  --quiet-pull --exit-code-from integration integration"
    try:
        python_ver = context.config["infrahub_ansible"]["python_ver"]
    except KeyError:
        raise KeyError("Could not find python_ver in context.config['infrahub_ansible']")
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd, env={"PYTHON_VER": python_ver})
