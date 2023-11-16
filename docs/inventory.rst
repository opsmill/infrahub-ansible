.. _inventory_module:


inventory -- Infrahub inventory source (using GraphQL)
======================================================

.. contents::
   :local:
   :depth: 1


Synopsis
--------

Get inventory hosts from Infrahub






Parameters
----------

  plugin (True, any, None)
    token that ensures this is a source file for the 'opsmill.infrahub' plugin.


  api_endpoint (True, any, None)
    Endpoint of the Infrahub API


  token (True, any, None)
    Infrahub API token to be able to read against Infrahub.


  timeout (False, int, 10)
    Timeout for Infrahub requests in seconds


  nodes (True, dict, None)
    Configuration for specific node types within Infrahub.

    Defines the attributes to include or exclude for each node.


    node_type (optional, dict, None)
      Configuration settings for a specific node type, e.g., "InfraDevice".

      Replace "node\_type" with the actual node type name you want to configure.


      filters (optional, dict, {})
        List of filters to apply on the query for node\_type.


      include (optional, list, [])
        List of attributes to include for node\_type.


      exclude (optional, list, [])
        List of attributes to exclude for node\_type.




  branch (False, str, main)
    Branch in which the request is made


  compose (optional, dict, {})
    List of custom ansible host vars to create from the objects fetched from Infrahub


  keyed_groups (False, list, [])
    Create groups based on attributes or relationships.

    groups is created as attribute\_\_value


    parent_group (optional, str, None)
      parent group for keyed group


    prefix (optional, str, )
      A keyed group name will start with this prefix


    separator (optional, str, _)
      separator used to build the keyed group name


    key (optional, str, None)
      The key from input dictionary used to generate groups


    default_value (optional, str, None)
      The default value when the host variable's value is an empty string.

      This option is mutually exclusive with \ :literal:`trailing\_separator`\ .


    trailing_separator (optional, bool, True)
      Set this option to \ :emphasis:`False`\  to omit the \ :literal:`separator`\  after the host variable when the value is an empty string.

      This option is mutually exclusive with \ :literal:`default\_value`\ .



  validate_certs (False, any, True)
    Whether or not to validate SSL of the Infrahub instance


  strict (optional, bool, False)
    If \ :literal:`yes`\  make invalid entries a fatal error, otherwise skip and continue.

    Since it is possible to use facts in the expressions they might not always be available and we ignore those errors by default.


  groups (optional, dict, {})
    Add hosts to group based on Jinja2 conditionals.


  use_extra_vars (optional, bool, False)
    Merge extra vars into the available variables for composition (highest precedence).


  leading_separator (optional, boolean, True)
    Use in conjunction with keyed\_groups.

    By default, a keyed group that does not have a prefix or a separator provided will have a name that starts with an underscore.

    This is because the default prefix is "" and the default separator is "\_".

    Set this option to False to omit the leading underscore (or other separator) if no prefix is given.

    If the group name is derived from a mapping the separator is still used to concatenate the items.

    To not use a separator in the group name at all, set the separator for the keyed group to an empty string instead.


  cache (optional, bool, False)
    Toggle to enable/disable the caching of the inventory's source data, requires a cache plugin setup to work.


  cache_plugin (optional, str, memory)
    Cache plugin to use for the inventory's source data.


  cache_timeout (optional, int, 3600)
    Cache duration in seconds


  cache_connection (optional, str, None)
    Cache connection data or path, read cache plugin documentation for specifics.


  cache_prefix (optional, any, ansible_inventory_)
    Prefix to use for cache plugin files/tables









Examples
--------

.. code-block:: yaml+jinja

    
    # inventory.yml file in YAML format
    # Example command line: ansible-inventory -v --list -i .yml
    # Add -vvv to the command to also see the GraphQL query that gets sent in the debug output.
    # Add -vvvv to the command to also see the JSON response that comes back in the debug output.

    # Minimum required parameters
    plugin: opsmill.infrahub.inventory
    api_endpoint: http://localhost:8000  # Can be omitted if the INFRAHUB_API environment variable is set
    token: 1234567890123456478901234567  # Can be omitted if the INFRAHUB_TOKEN environment variable is set

    # Complete Example
    # This will :
    # - Retrieve in the branch "branch1" attributes for the Node Kind "InfraDevice"
    # - The attributes wanted for "InfraDevice" are forced with the keyword "include"
    # - Create 2 compose variable "hostname" ad "platform" (platform will override the attribute platform retrieved)
    # - Create group based on the "site" name

    plugin: opsmill.infrahub.inventory
    api_endpoint: "http://localhost:8000"
    validate_certs: True

    strict: True

    branch: "branch1"

    nodes:
      InfraDevice:
        include:
          - name
          - platform
          - primary_address
          - interfaces
          - site

    compose:
      hostname: name
      platform: platform.ansible_network_os

    keyed_groups:
      - prefix: site
        key: site.name



Return Values
-------------

_list (, list, )
  list of composed dictionaries with key and value





Status
------





Authors
~~~~~~~

- Benoit Kohler (@bearchitek)

