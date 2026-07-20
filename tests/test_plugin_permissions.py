from plugins.permissions import is_api_allowed, is_tool_allowed


def test_api_permission_supports_exact_and_prefix_rules():
    manifest = {"permissions": {"api": ["/api/plugins/installed", "/api/mcp/*"], "tools": []}}
    assert is_api_allowed(manifest, "/api/plugins/installed")
    assert is_api_allowed(manifest, "/api/mcp/list")
    assert not is_api_allowed(manifest, "/api/chat")


def test_tool_permission_requires_explicit_match():
    manifest = {"permissions": {"api": [], "tools": ["time_now", "memory_*"]}}
    assert is_tool_allowed(manifest, "time_now")
    assert is_tool_allowed(manifest, "memory_search")
    assert not is_tool_allowed(manifest, "container_start")
