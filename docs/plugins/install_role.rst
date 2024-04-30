
.. Document meta

:orphan:

.. |antsibull-internal-nbsp| unicode:: 0xA0
    :trim:

.. meta::
  :antsibull-docs: 2.10.0

.. Anchors

.. _ansible_collections.opsmill.infrahub.install_role:

.. Title

opsmill.infrahub.install role -- Install Infrahub
+++++++++++++++++++++++++++++++++++++++++++++++++

.. Collection note

.. note::
    This role is part of the `opsmill.infrahub collection <https://galaxy.ansible.com/ui/repo/published/opsmill/infrahub/>`_ (version 1.0.6).

    It is not included in ``ansible-core``.
    To check whether it is installed, run :code:`ansible-galaxy collection list`.

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
        <div class="ansibleOptionAnchor" id="parameter-main--infrahub_config"></div>

      .. _ansible_collections.opsmill.infrahub.install_role__parameter-main__infrahub_config:

      .. rst-class:: ansible-option-title

      **infrahub_config**

      .. raw:: html

        <a class="ansibleOptionLink" href="#parameter-main--infrahub_config" title="Permalink to this option"></a>

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

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

      .. ansible-option-type-line::

        :ansible-option-type:`string`




      .. raw:: html

        </div>

    - .. raw:: html

        <div class="ansible-option-cell">

      Version of Infrahub to install.

      Can be any Docker image tag name.


      .. raw:: html

        </div>


.. Attributes


.. Notes


.. Seealso




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

