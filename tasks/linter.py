from invoke import Context, task

from .utils import ESCAPED_REPO_PATH

MAIN_DIRECTORY = "."
NAMESPACE = "INFRAHUB-ANSIBLE-LINT"


@task(name="format")
def lint_all(context: Context):
    """This will run all formatter."""

    lint_autoflake(context)
    lint_ruff(context)
    lint_yaml(context)

    print(f" - [{NAMESPACE}] All formatters have been executed!")


# ----------------------------------------------------------------------------
# Linter tasks - Python
# ----------------------------------------------------------------------------
@task
def lint_autoflake(context: Context):
    """Run autoflack to format all Python files."""

    print(f" - [{NAMESPACE}] Format code with autoflake")
    exec_cmd = f"autoflake --recursive --verbose --in-place --remove-all-unused-imports --remove-unused-variables {MAIN_DIRECTORY}"
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd)


@task
def lint_pylint(context: Context):
    """This will run pylint for the specified name and Python version."""

    print(f" - [{NAMESPACE}] Check code with pylint")
    exec_cmd = f"pylint {MAIN_DIRECTORY}"
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd)


@task
def lint_ruff(context: Context):
    """This will run ruff."""

    print(f" - [{NAMESPACE}] Check code with ruff")
    exec_cmd = f"ruff format --check --diff {MAIN_DIRECTORY} &&"
    exec_cmd += f"ruff check --diff {MAIN_DIRECTORY}"
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd)

# ----------------------------------------------------------------------------
# Linter tasks - Yaml
# ----------------------------------------------------------------------------

@task
def lint_yaml(context: Context):
    """This will run yamllint to validate formatting of all yaml files."""

    print(f" - [{NAMESPACE}] Format yaml with yamllint")
    exec_cmd = "yamllint ."
    context.run(exec_cmd, pty=True)

# ----------------------------------------------------------------------------
# Formatting tasks - Python
# ----------------------------------------------------------------------------
@task
def format_ruff(context: Context):
    """This will run ruff."""

    print(f" - [{NAMESPACE}] Check code with ruff")
    exec_cmd = f"ruff format {MAIN_DIRECTORY} && "
    exec_cmd += f"ruff check --fix {MAIN_DIRECTORY}"
    with context.cd(ESCAPED_REPO_PATH):
        context.run(exec_cmd)
