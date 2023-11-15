============
Inventory
============

This page will just have quick examples that people may have had questions about, but the normal plugin documentation should be referenced for normal usage.

The inventory plugin documentation can be found :ref:`here<ansible_collections.opsmill.infrahub.inventory>`.

Using Compose to Set ansible_network_os to Platform Slug
------------------------------------------------------------------

.. code-block:: yaml

  ---
  plugin: opsmill.infrahub.inventory
  compose:
    ansible_network_os: platform.name
