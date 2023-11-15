==========================
Module Architecture
==========================

Overview
----------------------


Let's take a look at the output of the ``tree`` command within the ``plugins/`` directory.

.. code-block:: bash

plugins
├── action
│   ├── __init__.py
│   ├── artifact_fetch.py
│   └── query_graphql.py
├── doc_fragments
│   └── fragments.py
├── inventory
│   └── inventory.py
├── lookup
│   └── lookup.py
├── module_utils
│   ├── __init__.py
│   ├── exception.py
│   └── infrahub_utils.py
└── modules
    ├── __init__.py
    ├── artifact_fetch.py
    └── query_graphql.py
