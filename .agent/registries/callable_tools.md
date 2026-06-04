<!-- generated: scripts/agent/update_callable_tools_registry.py -->
# Callable Tools Registry

- Generated at: `2026-05-24T17:51:50+09:00`
- Updated by: `codex`
- Registry revision: `e136d339100685db`
- Tool count: `54`
- Agent route count: `9`
- JSON SSOT: `.agent/registries/callable_tools.json`
- Refresh: `python scripts/agent/update_callable_tools_registry.py --updated-by <agent>`

## Tools By Module
- `src.core.brain.agent_router` (5): `calendar_create_event`, `calendar_delete_event`, `calendar_list_events`, `calendar_today`, `generate_image`
- `src.core.tools.comfyui_tools` (5): `comfyui_generate_image`, `comfyui_list_models`, `comfyui_start`, `comfyui_status`, `comfyui_stop`
- `src.core.tools.memory_tools` (8): `graph_add_knowledge`, `graph_search`, `graph_status`, `rag_index`, `rag_search`, `rag_status`, `recall_from_memory`, `save_to_memory`
- `src.core.tools.system_tools` (36): `check_environment`, `confirm_pending_command`, `edit_file`, `find_files`, `get_system_status`, `get_today_schedule`, `grep_code`, `list_agent_tool_capabilities`, `list_callable_tools`, `list_connected_pcs`, `list_directory`, `list_external_tool_capabilities`, `read_file`, `read_recent_logs`, `refresh_callable_tools_registry`, `refresh_external_tool_capability_registry`, `remote_batch_exec`, `remote_claude_chat`, `remote_claude_run`, `remote_docker_logs`, `remote_docker_ps`, `remote_git_commit_push`, `remote_git_status`, `remote_npm_build_deploy`, `remote_pc_command`, `remote_pc_file_read`, `remote_pc_file_write`, `remote_pc_process_list`, `remote_pc_screenshot`, `remote_pc_status`, `remote_vercel_deploy`, `remote_web_crawl`, `remote_web_search`, `run_daemon_job`, `run_pc_command`, `write_file`

## Tools By Authority Tier
- `G1` (28): `calendar_list_events`, `calendar_today`, `check_environment`, `comfyui_list_models`, `comfyui_status`, `get_system_status`, `get_today_schedule`, `graph_search`, `graph_status`, `list_agent_tool_capabilities`, `list_callable_tools`, `list_connected_pcs`, `list_directory`, `list_external_tool_capabilities`, `rag_search`, `rag_status`, `read_file`, `read_recent_logs`, `recall_from_memory`, `remote_docker_logs`, `remote_docker_ps`, `remote_git_status`, `remote_pc_file_read`, `remote_pc_process_list`, `remote_pc_screenshot`, `remote_pc_status`, `remote_web_crawl`, `remote_web_search`
- `G2` (10): `confirm_pending_command`, `edit_file`, `find_files`, `graph_add_knowledge`, `grep_code`, `rag_index`, `refresh_callable_tools_registry`, `refresh_external_tool_capability_registry`, `save_to_memory`, `write_file`
- `G3` (9): `comfyui_start`, `comfyui_stop`, `remote_batch_exec`, `remote_claude_chat`, `remote_claude_run`, `remote_pc_command`, `remote_pc_file_write`, `run_daemon_job`, `run_pc_command`
- `G4` (5): `calendar_create_event`, `calendar_delete_event`, `comfyui_generate_image`, `generate_image`, `remote_git_commit_push`
- `G5` (2): `remote_npm_build_deploy`, `remote_vercel_deploy`

## Agent Routes
- `calendar` (4): `calendar_list_events`, `calendar_create_event`, `calendar_delete_event`, `calendar_today`
- `chat` (0): 
- `dev_ops` (18): `remote_claude_run`, `remote_claude_chat`, `remote_docker_ps`, `remote_docker_logs`, `remote_git_status`, `remote_git_commit_push`, `remote_vercel_deploy`, `remote_npm_build_deploy`, `remote_batch_exec`, `rag_search`, `recall_from_memory`, `remote_pc_file_read`, `list_connected_pcs`, `list_callable_tools`, `refresh_callable_tools_registry`, `list_external_tool_capabilities`, `refresh_external_tool_capability_registry`, `list_agent_tool_capabilities`
- `governance` (0): 
- `image` (4): `generate_image`, `comfyui_generate_image`, `comfyui_status`, `comfyui_stop`
- `knowledge` (8): `save_to_memory`, `recall_from_memory`, `graph_add_knowledge`, `graph_search`, `graph_status`, `rag_index`, `rag_search`, `rag_status`
- `pc_control` (7): `list_connected_pcs`, `remote_pc_command`, `remote_pc_screenshot`, `remote_pc_status`, `remote_pc_file_read`, `remote_pc_file_write`, `remote_pc_process_list`
- `system_monitor` (12): `get_system_status`, `get_today_schedule`, `read_recent_logs`, `run_pc_command`, `check_environment`, `run_daemon_job`, `list_connected_pcs`, `list_callable_tools`, `refresh_callable_tools_registry`, `list_external_tool_capabilities`, `refresh_external_tool_capability_registry`, `list_agent_tool_capabilities`
- `web_search` (2): `remote_web_search`, `remote_web_crawl`
