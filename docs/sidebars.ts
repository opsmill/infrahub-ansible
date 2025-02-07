import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  ansibleSidebar: [
    'ansible/readme',
    {
      type: 'category',
      label: 'Guides',
      items: [
        'ansible/guides/installation',
        'ansible/guides/dynamic-inventory',
        'ansible/guides/query-and-lookup',
        'ansible/guides/create-node',
        'ansible/guides/create-branch',
      ],
    },
    {
      type: 'category',
      label: 'Reference',
      items: [
        'ansible/references/plugins/inventory_inventory',
        'ansible/references/plugins/lookup_lookup',
        'ansible/references/plugins/artifact_fetch_module',
        'ansible/references/plugins/query_graphql_module',
        'ansible/references/plugins/create_node_module',
        'ansible/references/plugins/create_branch_module',
        // 'ansible/references/roles',
      ],
    },
  ]
};

export default sidebars;
