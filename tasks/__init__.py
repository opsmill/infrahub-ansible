from invoke import Collection, Context, task

from . import docs, galaxy, linter, tests

ns = Collection("infrahub_ansible")
ns.configure(
    {
        "infrahub_ansible": {
            "infrahub_ver": "0.0.1",
            "project_name": "infrahub_ansible",
            "python_ver": "3.10",
            "local": False,
        }
    }
)

ns.add_collection(linter)
ns.add_collection(docs)
ns.add_collection(galaxy)
ns.add_collection(tests)


@task
def yamllint(context: Context):
    """This will run yamllint to validate formatting of all yaml files."""

    exec_cmd = "yamllint ."
    context.run(exec_cmd, pty=True)


@task(name="format")
def format_all(context: Context):
    linter.format_all(context)


@task(name="lint")
def lint_all(context: Context):
    yamllint(context)


@task(name="tests-all")
def test_all(context: Context):
    tests.tests_sanity(context)
    tests.tests_unit(context)
    tests.tests_integration(context)


@task(name="tests-sanity")
def tests_sanity(context: Context):
    tests.tests_sanity(context)


@task(name="tests-unit")
def tests_unit(context: Context):
    tests.tests_unit(context)


@task(name="tests-integration")
def tests_integration(context: Context):
    tests.tests_integration(context)


@task(name="generate-doc")
def generate_doc(context: Context):
    docs.generate_doc(context)


@task(
    name="galaxy-build",
    optional=["force"],
)
def galaxy_build(context: Context, force=False):
    galaxy.galaxy_build(context, force=force)


ns.add_task(format_all)
ns.add_task(lint_all)
ns.add_task(yamllint)
ns.add_task(test_all)
ns.add_task(tests_sanity)
ns.add_task(tests_unit)
ns.add_task(tests_integration)
ns.add_task(generate_doc)
ns.add_task(galaxy_build)
