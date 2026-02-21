## 2025-05-24 - Dynamic Breadcrumbs Pattern
**Learning:** Reusing navigation config from Sidebar for Header breadcrumbs works well but requires extracting the config to a separate file (e.g. `lib/navigation.ts`) to avoid breaking React Fast Refresh by exporting non-components from component files.
**Action:** When implementing navigation-based UI, always define the route configuration in a shared `lib` or `config` file first.
