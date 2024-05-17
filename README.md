[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

# Infrahub modules for Ansible using Ansible Collections

[Infrahub](https://github.com/opsmill/infrahub) by [OpsMill](https://opsmill.com) acts as a central hub to manage the data, templates and playbooks that powers your infrastructure. At its heart, Infrahub is built on 3 fundamental pillars:

- **A Flexible Schema**: A model of the infrastructure and the relation between the objects in the model, that's easily extensible.
- **Version Control**: Natively integrated into the graph database which opens up some new capabilities like branching, diffing, and merging data directly in the database.
- **Unified Storage**: By combining a graph database and git, Infrahub stores data and code needed to manage the infrastructure.

## Support

To keep the code simple, we only officially support the two latest releases of Infrahub and don't guarantee backwards compatibility beyond that. We do try and keep these breaking changes to a minimum, but sometimes changes to Infrahub's API cause us to have to make breaking changes.

## Requirements

- The two latest Infrahub releases
- Python >=3.9, <3.13
- Python modules:
  - infrahub-sdk >= 0.9.0
- Ansible 2.12+
- Infrahub write-enabled token when using modules or read-only token for `lookup/inventory`

## Documentation

Please refer to the [opsmill.infrahub Ansible Collection](https://infrahub-ansible.readthedocs.io/en/latest/) documentation.

## Releasing, Versioning, and Deprecation

This collection follows [Semantic Versioning](https://semver.org/). More details on versioning can be found [in the Ansible docs](https://docs.ansible.com/ansible/latest/dev_guide/developing_collections.html#collection-versions).

We plan to regularly release new minor or bugfix versions once new features or bugfixes have been implemented.

Releasing the current major version happens from the `develop` branch with a release.

If backward incompatible changes are possible, we plan to deprecate the old behavior as early as possible. We also plan to backport at least bug fixes for the old major version for some time after releasing a new major version. We will not block community members from backporting other bugfixes and features from the latest stable version to older release branches, under the condition that these backports are of reasonable quality. Some changes may not be able to be backported.

Some changes that would require immediate patching that are breaking changes will fall to SemVer and constitute a breaking change. These will only be done when necessary, such as to support working with the most recent 3 versions of Ansible. Backporting these changes may not be possible.
