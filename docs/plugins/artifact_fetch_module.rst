
.. Document meta

:orphan:

.. |antsibull-internal-nbsp| unicode:: 0xA0
    :trim:

.. meta::
  :antsibull-docs: 2.6.1

.. Anchors

.. _ansible_collections.opsmill.infrahub.artifact_fetch_module:

.. Anchors: short name for ansible.builtin

.. Title

opsmill.infrahub.artifact_fetch module -- Fetch the content of an artifact from Infrahub
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

.. Collection note

.. note::
    This module is part of the `opsmill.infrahub collection <https://galaxy.ansible.com/ui/repo/published/opsmill/infrahub/>`_ (version 1.0.2).

    It is not included in ``ansible-core``.
    To check whether it is installed, run :code:`ansible-galaxy collection list`.

    To install it, use: :code:`ansible-galaxy collection install opsmill.infrahub`.
    You need further requirements to be able to use this module,
    see :ref:`Requirements <ansible_collections.opsmill.infrahub.artifact_fetch_module_requirements>` for details.

    To use it in a playbook, specify: :code:`opsmill.infrahub.artifact_fetch`.

.. version_added

.. rst-class:: ansible-version-added

New in opsmill.infrahub 0.0.3

.. contents::
   :local:
   :depth: 1

.. Deprecated


Synopsis
--------

.. Description

- Fetch the content of an artifact from Infrahub through Infrahub SDK

.. note::
    This module has a corresponding :ref:`action plugin <action_plugins>`.

.. Aliases


.. Requirements

.. _ansible_collections.opsmill.infrahub.artifact_fetch_module_requirements:

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

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-api_endpoint:

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
        <div class="ansibleOptionAnchor" id="parameter-artifact_name"></div>

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-artifact_name:

      .. rst-class:: ansible-option-title

      **artifact_name**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-artifact_name" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string` / :ansible-option-required:`required`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Name of the artifact


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-branch"></div>

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-branch:

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
        <div class="ansibleOptionAnchor" id="parameter-target_id"></div>

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-target_id:

      .. rst-class:: ansible-option-title

      **target_id**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-target_id" title="Permalink to this option"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string` / :ansible-option-required:`required`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Id of the target for this artifact


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-timeout"></div>

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-timeout:

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

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-token:

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

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__parameter-validate_certs:

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

    
    - name: Infrahub action plugin Fetch_artifact
      gather_facts: false
      hosts: platform_eos
      vars:
        ansible_become: true

      tasks:
        - name: Query Startup Config for Edge Devices
          opsmill.infrahub.artifact_fetch:
            artifact_name: "Startup Config for Edge devices"
            target_id: "{{ id }}"
          register: startup_artifact

        - name: Save configs to localhost
          ansible.builtin.copy:
            content: "{{ startup_artifact.text }}"
            dest: "/tmp/{{ inventory_hostname }}-startup.conf"
            mode: '644'
          delegate_to: localhost




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
        <div class="ansibleOptionAnchor" id="return-json"></div>

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__return-json:

      .. rst-class:: ansible-option-title

      **json**

      .. raw:: html

        <a class="ansibleOptionLink" href="#return-json" title="Permalink to this return value"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`dictionary`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Content of the artifact in JSON format.


      .. rst-class:: ansible-option-line

      :ansible-option-returned-bold:`Returned:` success


      .. raw:: html

        </div>


  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="return-text"></div>

      .. _ansible_collections.opsmill.infrahub.artifact_fetch_module__return-text:

      .. rst-class:: ansible-option-title

      **text**

      .. raw:: html

        <a class="ansibleOptionLink" href="#return-text" title="Permalink to this return value"></a>

      .. ansible-option-type-line::

        :ansible-option-type:`string`

      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Content of the artifact in TEXT format.


      .. rst-class:: ansible-option-line

      :ansible-option-returned-bold:`Returned:` success


      .. raw:: html

        </div>



..  Status (Presently only deprecated)


.. Authors

Authors
~~~~~~~

- Damien Garros (@dgarros)



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

