
.. Document meta

:orphan:

.. role:: ansible-option-type
.. role:: ansible-option-elements
.. role:: ansible-option-required
.. role:: ansible-option-versionadded
.. role:: ansible-option-aliases
.. role:: ansible-option-choices
.. role:: ansible-option-choices-default-mark
.. role:: ansible-option-default-bold

.. Anchors

.. _ansible_collections.opsmill.infrahub.install_role:

.. Anchors: aliases


.. Title

opsmill.infrahub.install role -- Install Infrahub
+++++++++++++++++++++++++++++++++++++++++++++++++

.. Collection note

.. note::
    This role is part of the `opsmill.infrahub collection <https://galaxy.ansible.com/opsmill/infrahub>`_ (version 1.0.4).

    To install it use: :code:`ansible-galaxy collection install opsmill.infrahub`.

    To use it in a playbook, specify: :code:`opsmill.infrahub.install`.

.. contents::
   :local:
   :depth: 2


.. Entry point title

Entry point ``main`` -- Install Infrahub
----------------------------------------

.. version_added


.. Deprecated


Synopsis
^^^^^^^^

.. Description

- The main entry point installs Infrahub.
- This role requires Docker Engine with Docker Compose v2 to be installed.

.. Requirements


.. Options

Parameters
^^^^^^^^^^

.. rst-class:: ansible-option-table

.. list-table::
  :width: 100%
  :widths: auto
  :header-rows: 1

  * - Parameter
    - Comments

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_config"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_config:

      .. rst-class:: ansible-option-title

      **infrahub_config**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_config" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`dictionary`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Environment variables to pass as configuration for Infrahub.


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_docker_project"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_docker_project:

      .. rst-class:: ansible-option-title

      **infrahub_docker_project**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_docker_project" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Docker project name to use when starting Infrahub.


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`"infrahub"`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_docker_pull_images"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_docker_pull_images:

      .. rst-class:: ansible-option-title

      **infrahub_docker_pull_images**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_docker_pull_images" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`boolean`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Whether to pull the required Docker images.


      .. rst-class:: ansible-option-line

      :ansible-option-choices:`Choices:`

      - :ansible-option-choices-entry:`false`
      - :ansible-option-choices-entry-default:`true` :ansible-option-choices-default-mark:`← (default)`


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_install_directory"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_install_directory:

      .. rst-class:: ansible-option-title

      **infrahub_install_directory**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_install_directory" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Install directory for the Infrahub files (docker-compose and config file).


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`"/opt/infrahub"`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_setup_systemd"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_setup_systemd:

      .. rst-class:: ansible-option-title

      **infrahub_setup_systemd**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_setup_systemd" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`boolean`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Whether to install the systemd service for Infrahub.


      .. rst-class:: ansible-option-line

      :ansible-option-choices:`Choices:`

      - :ansible-option-choices-entry:`false`
      - :ansible-option-choices-entry-default:`true` :ansible-option-choices-default-mark:`← (default)`


      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_systemd_directory"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_systemd_directory:

      .. rst-class:: ansible-option-title

      **infrahub_systemd_directory**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_systemd_directory" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Where to install the systemd service unit file.


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`"/etc/systemd/system/"`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_systemd_service_state"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_systemd_service_state:

      .. rst-class:: ansible-option-title

      **infrahub_systemd_service_state**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_systemd_service_state" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Target state of the systemd service.

      Can be used to avoid starting Infrahub during the role's execution.


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`"restarted"`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_url"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_url:

      .. rst-class:: ansible-option-title

      **infrahub_url**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_url" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      URL from where to fetch the Infrahub docker-compose file.


      .. rst-class:: ansible-option-line

      :ansible-option-default-bold:`Default:` :ansible-option-default:`"https://infrahub.opsmill.io"`

      .. raw:: html

        </div>

  * - .. raw:: html

        <div class="ansible-option-cell">
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_version"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_version:

      .. rst-class:: ansible-option-title

      **infrahub_version**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_version" title="Permalink to this option"></a>

      .. rst-class:: ansible-option-type-line

      :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Version of Infrahub to install.

      Can be any Docker image tag name.


      .. raw:: html

        </div>


.. Notes


.. Seealso




.. Extra links

Collection links
~~~~~~~~~~~~~~~~

.. raw:: html

  <p class="ansible-links">
    <a href="https://github.com/opsmill/infrahub-ansible/issues" aria-role="button" target="_blank" rel="noopener external">Issue Tracker</a>
    <a href="https://www.opsmill.com/" aria-role="button" target="_blank" rel="noopener external">Homepage</a>
    <a href="https://github.com/opsmill/infrahub-ansible" aria-role="button" target="_blank" rel="noopener external">Repository (Sources)</a>
  </p>

.. Parsing errors

