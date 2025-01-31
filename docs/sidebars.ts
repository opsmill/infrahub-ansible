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
        'ansible/guides/lookup',
        'ansible/guides/query',
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
        // 'ansible/references/roles',
      ],
    },
  ]
};

export default sidebars;
