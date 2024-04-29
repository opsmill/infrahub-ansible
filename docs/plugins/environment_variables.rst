
:orphan:

.. _list_of_collection_env_vars:

Index of all Collection Environment Variables
=============================================

The following index documents all environment variables declared by plugins in collections.
Environment variables used by the ansible-core configuration are documented in :ref:`ansible_configuration_settings`.

.. envvar:: ANSIBLE_INVENTORY_USE_EXTRA_VARS

    Merge extra vars into the available variables for composition (highest precedence).

    *Used by:*
    :ref:`opsmill.infrahub.inventory inventory plugin <ansible_collections.opsmill.infrahub.inventory_inventory>`
.. envvar:: INFRAHUB_API

    Endpoint of the Infrahub API

    *Used by:*
    :ref:`opsmill.infrahub.inventory inventory plugin <ansible_collections.opsmill.infrahub.inventory_inventory>`,
    :ref:`opsmill.infrahub.lookup lookup plugin <ansible_collections.opsmill.infrahub.lookup_lookup>`
.. envvar:: INFRAHUB_TOKEN

    Infrahub API token to be able to read against Infrahub.

    *Used by:*
    :ref:`opsmill.infrahub.inventory inventory plugin <ansible_collections.opsmill.infrahub.inventory_inventory>`,
    :ref:`opsmill.infrahub.lookup lookup plugin <ansible_collections.opsmill.infrahub.lookup_lookup>`
