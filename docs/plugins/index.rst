

.. meta::
  :antsibull-docs: 2.10.0


.. _plugins_in_opsmill.infrahub:

Opsmill.Infrahub
================

Collection version 1.0.4

.. contents::
   :local:
   :depth: 1

Description
-----------

This is a collection of Infrahub Ansible modules

**Author:**

* OpsMill <info@opsmill.com>

**Supported ansible-core versions:**

* 2.14.0 or newer

.. ansible-links::

  - title: "Issue Tracker"
    url: "https://github.com/opsmill/infrahub-ansible/issues"
    external: true
  - title: "Homepage"
    url: "https://www.opsmill.com/"
    external: true
  - title: "Repository (Sources)"
    url: "https://github.com/opsmill/infrahub-ansible"
    external: true




.. toctree::
    :maxdepth: 1

Plugin Index
------------

These are the plugins in the opsmill.infrahub collection:


Modules
~~~~~~~

* :ansplugin:`artifact_fetch module <opsmill.infrahub.artifact_fetch#module>` -- Fetch the content of an artifact from Infrahub
* :ansplugin:`query_graphql module <opsmill.infrahub.query_graphql#module>` -- Queries and returns elements from Infrahub GraphQL API

.. toctree::
    :maxdepth: 1
    :hidden:

    artifact_fetch_module
    query_graphql_module


Inventory Plugins
~~~~~~~~~~~~~~~~~

* :ansplugin:`inventory inventory <opsmill.infrahub.inventory#inventory>` -- Infrahub inventory source (using GraphQL)

.. toctree::
    :maxdepth: 1
    :hidden:

    inventory_inventory


Lookup Plugins
~~~~~~~~~~~~~~

* :ansplugin:`lookup lookup <opsmill.infrahub.lookup#lookup>` -- Queries and returns elements from Infrahub (using GraphQL)

.. toctree::
    :maxdepth: 1
    :hidden:

    lookup_lookup


Role Index
----------

These are the roles in the opsmill.infrahub collection:

* :ansplugin:`install role <opsmill.infrahub.install#role>` -- Install Infrahub

.. toctree::
    :maxdepth: 1
    :hidden:

    install_role

