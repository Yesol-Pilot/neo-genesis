from scripts.agent.update_callable_tools_registry import build_registry
from scripts.agent.update_external_tool_capability_registry import build_registry as build_external_registry


def test_callable_tools_registry_contains_shared_tools():
    registry = build_registry(updated_by="pytest")
    names = {tool["name"]: tool for tool in registry["tools"]}

    assert registry["diagnostics"]["route_error_count"] == 0
    assert "list_callable_tools" in names
    assert "refresh_callable_tools_registry" in names
    assert "list_external_tool_capabilities" in names
    assert "refresh_external_tool_capability_registry" in names
    assert "list_agent_tool_capabilities" in names
    assert names["list_callable_tools"]["policy"]["authority_tier"] == "G1"
    assert names["refresh_callable_tools_registry"]["policy"]["authority_tier"] == "G2"
    assert names["list_external_tool_capabilities"]["policy"]["authority_tier"] == "G1"
    assert names["refresh_external_tool_capability_registry"]["policy"]["authority_tier"] == "G2"


def test_callable_tools_registry_agent_routes_can_refresh():
    registry = build_registry(updated_by="pytest")

    assert "list_callable_tools" in registry["agent_routes"]["dev_ops"]["tool_names"]
    assert "refresh_callable_tools_registry" in registry["agent_routes"]["dev_ops"]["tool_names"]
    assert "list_external_tool_capabilities" in registry["agent_routes"]["dev_ops"]["tool_names"]
    assert "refresh_external_tool_capability_registry" in registry["agent_routes"]["dev_ops"]["tool_names"]
    assert "list_agent_tool_capabilities" in registry["agent_routes"]["dev_ops"]["tool_names"]
    assert "list_callable_tools" in registry["agent_routes"]["system_monitor"]["tool_names"]
    assert "refresh_callable_tools_registry" in registry["agent_routes"]["system_monitor"]["tool_names"]
    assert "list_external_tool_capabilities" in registry["agent_routes"]["system_monitor"]["tool_names"]
    assert "refresh_external_tool_capability_registry" in registry["agent_routes"]["system_monitor"]["tool_names"]
    assert "list_agent_tool_capabilities" in registry["agent_routes"]["system_monitor"]["tool_names"]


def test_external_tool_capability_registry_indexes_codex_tools():
    registry = build_external_registry(updated_by="pytest")
    capabilities = {item["id"]: item for item in registry["capabilities"]}

    assert registry["diagnostics"]["error_count"] == 0
    assert "functions.shell_command" in capabilities
    assert "tool_search.tool_search_tool" in capabilities
    assert "plugin.vercel" in capabilities
    assert capabilities["plugin.vercel"]["authority_tier"] == "G5"
    assert "plugin" in registry["indexes"]["by_namespace"]
