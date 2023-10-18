
.. Document meta

:orphan:

.. |antsibull-internal-nbsp| unicode:: 0xA0
    :trim:

.. meta::
  :antsibull-docs: 2.5.0

.. Anchors

.. _ansible_collections.infrahub.infrahub.query_graphql_module:

.. Anchors: short name for ansible.builtin

.. Title

infrahub.infrahub.query_graphql module -- Queries and returns elements from Infrahub GraphQL API
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. Collection note

.. note::
    This module is part of the `infrahub.infrahub collection <https://galaxy.ansible.com/ui/repo/published/infrahub/infrahub/>`_ (version 0.0.1).

    It is not included in ``ansible-core``.
    To check whether it is installed, run :code:`ansible-galaxy collection list`.

    To install it, use: :code:`ansible-galaxy collection install infrahub.infrahub`.
    You need further requirements to be able to use this module,
    see :ref:`Requirements <ansible_collections.infrahub.infrahub.query_graphql_module_requirements>` for details.

    To use it in a playbook, specify: :code:`infrahub.infrahub.query_graphql`.

.. version_added

.. rst-class:: ansible-version-added

New in infrahub.infrahub 0.0.1

.. contents::
   :local:
   :depth: 1

.. Deprecated


Synopsis
--------

.. Description

- Queries Infrahub via its GraphQL API through pyinfrahub

.. note::
    This module has a corresponding :ref:`action plugin <action_plugins>`.

.. Aliases


.. Requirements

.. _ansible_collections.infrahub.infrahub.query_graphql_module_requirements:

Requirements
------------
The below requirements are needed on the host that executes this module.

- pyinfrahub






.. Options

Parameters
----------

.. tabularcolumns:: \X{1}{3}\X{2}{3}

.. list-table::
  :width: 100%
  :widths: auto
  :header-rows: 1
  :class: longtable ansible-option-table

  * - Parameter
    - Comments

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-api_endpoint"></div>

      .. _ansible_collections.infrahub.infrahub.query_graphql_module__parameter-api_endpoint:

      .. rst-class:: ansible-option-title

      **api_endpoint**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-api_endpoint" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Endpoint of the Infrahub API, optional env=INFRAHUB\_API


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-api_version"></div>

      .. _ansible_collections.infrahub.infrahub.query_graphql_module__parameter-api_version:

      .. rst-class:: ansible-option-title

      **api_version**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-api_version" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      API Version Infrahub API


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-graph_variables"></div>

      .. _ansible_collections.infrahub.infrahub.query_graphql_module__parameter-graph_variables:

      .. rst-class:: ansible-option-title

      **graph_variables**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-graph_variables" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`dictionary`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Dictionary of keys/values to pass into the GraphQL query


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`{}`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-query"></div>

      .. _ansible_collections.infrahub.infrahub.query_graphql_module__parameter-query:

      .. rst-class:: ansible-option-title

      **query**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-query" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string` / :ansible-option-required:`required`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      GraphQL query parameters or filters to send to Infrahub to obtain desired data


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-token"></div>

      .. _ansible_collections.infrahub.infrahub.query_graphql_module__parameter-token:

      .. rst-class:: ansible-option-title

      **token**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-token" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      The API token created through Infrahub, optional env=INFRAHUB\_TOKEN


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-validate_certs"></div>

      .. _ansible_collections.infrahub.infrahub.query_graphql_module__parameter-validate_certs:

      .. rst-class:: ansible-option-title

      **validate_certs**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-validate_certs" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`boolean`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Whether or not to validate SSL of the Infrahub instance


      .. rst-class:: ansible-option-line

      :ansible-option-choices:`Choices:`

      - :ansible-option-choices-entry:`false`
      - :ansible-option-choices-entry-default:`true` :ansible-option-choices-default-mark:`← (default)`


      .. raw:: html

        </div>


.. Attributes


.. Notes


.. Seealso


.. Examples

Examples
--------

.. code-block:: yaml+jinja

    




.. Facts


.. Return values


..  Status (Presently only deprecated)


.. Authors

Authors
~~~~~~~

- Benoit Kohler (@bearchitek)



.. Extra links

Collection links
~~~~~~~~~~~~~~~~

.. ansible-links::

  - title: "Issue Tracker"
    url: "https://github.com/opsmill/infrahub-ansible/issues"
    external: true
  - title: "Repository (Sources)"
    url: "https://github.com/opsmill/infrahub-ansible"
    external: true


.. Parsing errors

