<!-- generated: scripts/agent/update_external_tool_capability_registry.py -->
# External Tool Capabilities

- Generated at: `2026-05-24T17:51:50+09:00`
- Updated by: `codex`
- Registry revision: `bf7e63c66389797c`
- Capability count: `28`
- JSON SSOT: `.agent/registries/external_tool_capabilities.json`
- Source: `.agent/registries/external_tool_capabilities.source.json`
- Refresh: `python scripts/agent/update_external_tool_capability_registry.py --updated-by <agent>`

## By Namespace
- `codex_app` (3): `codex_app.automation_update`, `codex_app.load_workspace_dependencies`, `codex_app.read_thread_terminal`
- `functions` (7): `functions.apply_patch`, `functions.list_mcp_resources`, `functions.read_mcp_resource`, `functions.request_plugin_install`, `functions.shell_command`, `functions.update_plan`, `functions.view_image`
- `image_gen` (1): `image_gen.imagegen`
- `multi_tool_use` (1): `multi_tool_use.parallel`
- `plugin` (11): `plugin.browser`, `plugin.build_web_apps`, `plugin.chrome`, `plugin.figma`, `plugin.github`, `plugin.gmail`, `plugin.google_calendar`, `plugin.google_drive`, `plugin.slack`, `plugin.supabase`, `plugin.vercel`
- `tool_search` (1): `tool_search.tool_search_tool`
- `web` (4): `web.finance`, `web.open`, `web.search_query`, `web.weather`

## By Capability Type
- `automation_management` (1): `codex_app.automation_update`
- `coordination` (2): `functions.update_plan`, `multi_tool_use.parallel`
- `current_data` (1): `web.weather`
- `deferred_plugin_family` (11): `plugin.browser`, `plugin.build_web_apps`, `plugin.chrome`, `plugin.figma`, `plugin.github`, `plugin.gmail`, `plugin.google_calendar`, `plugin.google_drive`, `plugin.slack`, `plugin.supabase`, `plugin.vercel`
- `file_edit` (1): `functions.apply_patch`
- `file_inspection` (1): `functions.view_image`
- `image_generation` (1): `image_gen.imagegen`
- `local_execution` (1): `functions.shell_command`
- `market_data` (1): `web.finance`
- `mcp_resource_inspection` (2): `functions.list_mcp_resources`, `functions.read_mcp_resource`
- `plugin_management` (1): `functions.request_plugin_install`
- `runtime_inspection` (1): `codex_app.load_workspace_dependencies`
- `terminal_inspection` (1): `codex_app.read_thread_terminal`
- `tool_discovery` (1): `tool_search.tool_search_tool`
- `web_research` (2): `web.open`, `web.search_query`

## By Authority Tier
- `G0` (2): `functions.update_plan`, `multi_tool_use.parallel`
- `G1` (10): `codex_app.load_workspace_dependencies`, `codex_app.read_thread_terminal`, `functions.list_mcp_resources`, `functions.read_mcp_resource`, `functions.view_image`, `tool_search.tool_search_tool`, `web.finance`, `web.open`, `web.search_query`, `web.weather`
- `G2` (2): `functions.apply_patch`, `plugin.browser`
- `G3` (3): `functions.shell_command`, `plugin.build_web_apps`, `plugin.chrome`
- `G4` (10): `codex_app.automation_update`, `functions.request_plugin_install`, `image_gen.imagegen`, `plugin.figma`, `plugin.github`, `plugin.gmail`, `plugin.google_calendar`, `plugin.google_drive`, `plugin.slack`, `plugin.supabase`
- `G5` (1): `plugin.vercel`
