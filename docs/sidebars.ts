import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  ansibleSidebar: [
    'readme',
    {
      type: 'category',
      label: 'Guides',
      items: [
        'guides/installation',
        'guides/dynamic-inventory',
        'guides/query-and-lookup',
        'guides/create-node',
        'guides/create-branch',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'references/plugins/inventory_inventory',
        'references/plugins/lookup_lookup',
        'references/plugins/artifact_fetch_module',
        'references/plugins/query_graphql_module',
        'references/plugins/create_node_module',
        'references/plugins/create_branch_module',
        // 'references/roles',
      ],
    },
  ]
};

export default sidebars;
