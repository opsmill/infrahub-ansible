import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  ansibleSidebar: [
    'infrahub-ansible/readme',
    // Guides
    'infrahub-ansible/guides/getting-started',
    // References
    'infrahub-ansible/references/plugins/inventory_inventory',
    'infrahub-ansible/references/plugins/lookup_lookup',
    'infrahub-ansible/references/plugins/artifact_fetch_module',
    'infrahub-ansible/references/plugins/query_graphql_module',
    // 'infrahub-ansible/references/roles',
  ]
};

export default sidebars;
