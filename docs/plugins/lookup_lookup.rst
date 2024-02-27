
.. Document meta

:orphan:

.. |antsibull-internal-nbsp| unicode:: 0xA0
    :trim:

.. meta::
  :antsibull-docs: 2.7.0

.. Anchors

.. _ansible_collections.opsmill.infrahub.lookup_lookup:

.. Anchors: short name for ansible.builtin

.. Title

opsmill.infrahub.lookup lookup -- Queries and returns elements from Infrahub (using GraphQL)
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. Collection note

.. note::
    This lookup plugin is part of the `opsmill.infrahub collection <https://galaxy.ansible.com/ui/repo/published/opsmill/infrahub/>`_ (version 1.0.3).

    It is not included in ``ansible-core``.
    To check whether it is installed, run :code:`ansible-galaxy collection list`.

    To install it, use: :code:`ansible-galaxy collection install opsmill.infrahub`.

    To use it in a playbook, specify: :code:`opsmill.infrahub.lookup`.

.. version_added


.. contents::
   :local:
   :depth: 1

.. Deprecated


Synopsis
--------

.. Description

- Get inventory hosts from Infrahub


.. Aliases


.. Requirements






.. Options

Keyword parameters
------------------

This describes keyword parameters of the lookup. These are the values ``key1=value1``, ``key2=value2`` and so on in the following
examples: ``lookup('opsmill.infrahub.lookup', key1=value1, key2=value2, ...)`` and ``query('opsmill.infrahub.lookup', key1=value1, key2=value2, ...)``

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

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-api_endpoint:

      .. rst-class:: ansible-option-title

      **api_endpoint**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-api_endpoint" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string` / :ansible-option-required:`required`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Endpoint of the Infrahub API


      .. rst-class:: ansible-option-line

      :ansible-option-configuration:`Configuration:`

      - Environment variable: :envvar:`INFRAHUB\_API`


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-branch"></div>

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-branch:

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

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-graph_variables:

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

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-query:

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

      GraphQL query to send to Infrahub to obtain desired data


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-timeout"></div>

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-timeout:

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

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-token:

      .. rst-class:: ansible-option-title

      **token**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-token" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string` / :ansible-option-required:`required`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Infrahub API token to be able to read against Infrahub.


      .. rst-class:: ansible-option-line

      :ansible-option-configuration:`Configuration:`

      - Environment variable: :envvar:`INFRAHUB\_TOKEN`


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-validate_certs"></div>

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__parameter-validate_certs:

      .. rst-class:: ansible-option-title

      **validate_certs**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-validate_certs" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Whether or not to validate SSL of the Infrahub instance


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`true`

      .. raw:: html

        </div>


.. Attributes


.. Notes


.. Seealso


.. Examples

Examples
--------

.. code-block:: yaml+jinja

    
    - name: Infrahub lookup
      gather_facts: false
      hosts: localhost

      tasks:
        - name: SET FACT OF STRING
          ansible.builtin.set_fact:
            query_string: |
              query {
                BuiltinLocation {
                  edges {
                    node {
                      name {
                        value
                      }
                    }
                  }
                }
              }

        - name: Obtain list of sites from Infrahub
          ansible.builtin.set_fact:
            query_response: "{{ query('opsmill.infrahub.lookup', query=query_string) }}"

        - name: Print result
          ansible.builtin.debug:
            msg: "{{ query_response }}"




.. Facts


.. Return values

Return Value
------------

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

      .. _ansible_collections.opsmill.infrahub.lookup_lookup__return-data:

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


.. hint::
    Configuration entries for each entry type have a low to high priority order. For example, a variable that is lower in the list will override a variable that is higher up.

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

