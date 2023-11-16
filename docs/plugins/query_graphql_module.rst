
.. Document meta

:orphan:

.. |antsibull-internal-nbsp| unicode:: 0xA0
    :trim:

.. meta::
  :antsibull-docs: 2.5.0

.. Anchors

.. _ansible_collections.opsmill.infrahub.query_graphql_module:

.. Anchors: short name for ansible.builtin

.. Title

opsmill.infrahub.query_graphql module -- Queries and returns elements from Infrahub GraphQL API
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. Collection note

.. note::
    This module is part of the `opsmill.infrahub collection <https://galaxy.ansible.com/ui/repo/published/opsmill/infrahub/>`_ (version 1.0.0).

    It is not included in ``ansible-core``.
    To check whether it is installed, run :code:`ansible-galaxy collection list`.

    To install it, use: :code:`ansible-galaxy collection install opsmill.infrahub`.
    You need further requirements to be able to use this module,
    see :ref:`Requirements <ansible_collections.opsmill.infrahub.query_graphql_module_requirements>` for details.

    To use it in a playbook, specify: :code:`opsmill.infrahub.query_graphql`.

.. version_added

.. rst-class:: ansible-version-added

New in opsmill.infrahub 0.0.1

.. contents::
   :local:
   :depth: 1

.. Deprecated


Synopsis
--------

.. Description

- Queries Infrahub via its GraphQL API through Infrahub SDK

.. note::
    This module has a corresponding :ref:`action plugin <action_plugins>`.

.. Aliases


.. Requirements

.. _ansible_collections.opsmill.infrahub.query_graphql_module_requirements:

Requirements
------------
The below requirements are needed on the host that executes this module.

- infrahub-sdk






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

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-api_endpoint:

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
        <div class="ansibleOptionAnchor" id="parameter-branch"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-branch:

      .. rst-class:: ansible-option-title

      **branch**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-branch" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Branch in which the request is made


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`"main"`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-graph_variables"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-graph_variables:

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

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-query:

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
        <div class="ansibleOptionAnchor" id="parameter-timeout"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-timeout:

      .. rst-class:: ansible-option-title

      **timeout**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-timeout" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`integer`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Timeout for Infrahub requests in seconds


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`10`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-token"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-token:

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
        <div class="ansibleOptionAnchor" id="parameter-update_hostvars"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-update_hostvars:

      .. rst-class:: ansible-option-title

      **update_hostvars**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-update_hostvars" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`boolean`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Whether or not to populate data in the in the root (e.g. hostvars[inventory\_hostname]) or within the 'data' key (e.g. hostvars[inventory\_hostname]['data']). Beware, that the root keys provided by the query will overwrite any root keys already present, leverage the GraphQL alias feature to avoid issues.


      .. rst-class:: ansible-option-line

      :ansible-option-choices:`Choices:`

      - :ansible-option-choices-entry-default:`false` :ansible-option-choices-default-mark:`← (default)`
      - :ansible-option-choices-entry:`true`


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-validate_certs"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__parameter-validate_certs:

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

    
    - name: Infrahub action plugin
      gather_facts: false
      hosts: localhost

      tasks:
        - name: SET FACTS TO SEND TO GRAPHQL ENDPOINT
          ansible.builtin.set_fact:
            variables:
              device_name: "atl1-edge1"
              enabled: true

            query_dict:
              InfraDevice:
                '@filters': {name__value: '$device_name'}
                edges:
                  node:
                    name:
                      value: null
                    interfaces:
                      '@filters': {enabled__value: '$enabled'}
                      edges:
                        node:
                          name:
                            value: null

        - name: Action Plugin
          opsmill.infrahub.query_graphql:
            query: "{{ query_dict }}"
            graph_variables: "{{ variables }}"




.. Facts


.. Return values

Return Values
-------------
Common return values are documented :ref:`here <common_return_values>`, the following are the fields unique to this module:

.. tabularcolumns:: \X{1}{3}\X{2}{3}

.. list-table::
  :width: 100%
  :widths: auto
  :header-rows: 1
  :class: longtable ansible-option-table

  * - Key
    - Description

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="return-data"></div>

      .. _ansible_collections.opsmill.infrahub.query_graphql_module__return-data:

      .. rst-class:: ansible-option-title

      **data**

      .. raw:: html

        <a class="ansibleOptionLink" href="#return-data" title="Permalink to this return value"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`dictionary`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Data result from the Infrahub GraphQL endpoint


      .. rst-class:: ansible-option-line

      :ansible-option-returned-bold:`Returned:` success


      .. raw:: html

        </div>



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
  - title: "Homepage"
    url: "https://www.opsmill.com/"
    external: true
  - title: "Repository (Sources)"
    url: "https://github.com/opsmill/infrahub-ansible"
    external: true


.. Parsing errors

