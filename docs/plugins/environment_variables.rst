
:orphan:

.. meta::
  :antsibull-docs: 2.5.0

.. _list_of_collection_env_vars:

Index of all Collection Environment Variables
=============================================

The following index documents all environment variables declared by plugins in collections.
Environment variables used by the ansible-core configuration are documented in :ref:`ansible_configuration_settings`.

.. envvar:: ANSIBLE_INVENTORY_USE_EXTRA_VARS

    Merge extra vars into the available variables for composition (highest precedence).

    *Used by:*
    :ansplugin:`infrahub.infrahub.inventory inventory plugin <infrahub.infrahub.inventory#inventory>`
.. envvar:: INFRAHUB_API

    Endpoint of the Infrahub API

    *Used by:*
    :ansplugin:`infrahub.infrahub.inventory inventory plugin <infrahub.infrahub.inventory#inventory>`,
    :ansplugin:`infrahub.infrahub.lookup lookup plugin <infrahub.infrahub.lookup#lookup>`
.. envvar:: INFRAHUB_TOKEN

    Infrahub API token to be able to read against Infrahub.

    *Used by:*
    :ansplugin:`infrahub.infrahub.inventory inventory plugin <infrahub.infrahub.inventory#inventory>`,
    :ansplugin:`infrahub.infrahub.lookup lookup plugin <infrahub.infrahub.lookup#lookup>`
