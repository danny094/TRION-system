import pytest

from config.autonomy.tool_policy import (
    get_autonomy_tool_allowlist,
    get_autonomy_tool_blocklist,
    get_autonomy_approval_required_tools,
)


class _NoOverrideSettings:
    """Settings stub that has no overrides — simulates a clean ENV-only state."""
    def get(self, key, default=None):
        return default


def _no_override(monkeypatch):
    monkeypatch.setattr("config.autonomy.tool_policy.settings", _NoOverrideSettings())


# ── Defaults ─────────────────────────────────────────────────────────────────

def test_tool_policy_defaults_are_empty_lists(monkeypatch):
    _no_override(monkeypatch)
    monkeypatch.delenv("AUTONOMY_TOOL_ALLOWLIST", raising=False)
    monkeypatch.delenv("AUTONOMY_TOOL_BLOCKLIST", raising=False)
    monkeypatch.delenv("AUTONOMY_APPROVAL_REQUIRED_TOOLS", raising=False)

    assert get_autonomy_tool_allowlist() == []
    assert get_autonomy_tool_blocklist() == []
    assert get_autonomy_approval_required_tools() == []


# ── ENV source ───────────────────────────────────────────────────────────────

def test_tool_policy_reads_allowlist_from_env(monkeypatch):
    _no_override(monkeypatch)
    monkeypatch.setenv("AUTONOMY_TOOL_ALLOWLIST", "tool_a,tool_b,tool_c")

    assert get_autonomy_tool_allowlist() == ["tool_a", "tool_b", "tool_c"]


def test_tool_policy_reads_blocklist_from_env(monkeypatch):
    _no_override(monkeypatch)
    monkeypatch.setenv("AUTONOMY_TOOL_BLOCKLIST", "dangerous_tool")

    assert get_autonomy_tool_blocklist() == ["dangerous_tool"]


def test_tool_policy_reads_approval_tools_from_env(monkeypatch):
    _no_override(monkeypatch)
    monkeypatch.setenv("AUTONOMY_APPROVAL_REQUIRED_TOOLS", "deploy_container,run_command")

    assert get_autonomy_approval_required_tools() == ["deploy_container", "run_command"]


def test_tool_policy_strips_whitespace_around_entries(monkeypatch):
    _no_override(monkeypatch)
    monkeypatch.setenv("AUTONOMY_TOOL_ALLOWLIST", " tool_a , tool_b , tool_c ")

    assert get_autonomy_tool_allowlist() == ["tool_a", "tool_b", "tool_c"]


def test_tool_policy_ignores_empty_entries(monkeypatch):
    _no_override(monkeypatch)
    monkeypatch.setenv("AUTONOMY_TOOL_BLOCKLIST", "tool_a,,tool_b,")

    assert get_autonomy_tool_blocklist() == ["tool_a", "tool_b"]


# ── Blocking logic ────────────────────────────────────────────────────────────
#
# Mirror of the formula used in adapters/admin-api/tools_routes.py:
#   blocked = (bool(allowlist_set) and name not in allowlist_set) or name in blocklist_set

def _is_blocked(name: str, allowlist: list[str], blocklist: list[str]) -> bool:
    allowlist_set = set(allowlist)
    blocklist_set = set(blocklist)
    return (bool(allowlist_set) and name not in allowlist_set) or name in blocklist_set


def test_blocking_empty_policy_allows_all():
    assert _is_blocked("any_tool", [], []) is False


def test_blocking_allowlist_permits_listed_tools():
    assert _is_blocked("tool_b", ["tool_a", "tool_b"], []) is False


def test_blocking_allowlist_blocks_unlisted_tools():
    assert _is_blocked("tool_c", ["tool_a", "tool_b"], []) is True


def test_blocking_empty_allowlist_does_not_restrict():
    assert _is_blocked("any_tool", [], ["other_tool"]) is False


def test_blocking_blocklist_blocks_regardless_of_allowlist():
    assert _is_blocked("dangerous", ["dangerous"], ["dangerous"]) is True
    assert _is_blocked("dangerous", [], ["dangerous"]) is True


def test_blocking_blocklist_applied_after_allowlist():
    # tool_a passes the allowlist but is then removed by the blocklist
    assert _is_blocked("tool_a", ["tool_a", "tool_b"], ["tool_a"]) is True
    assert _is_blocked("tool_b", ["tool_a", "tool_b"], ["tool_a"]) is False


def test_blocking_approval_set_is_independent_of_blocked():
    # approval_required is purely set membership — does not imply blocked
    approval_set = {"deploy_container"}
    assert "deploy_container" in approval_set
    assert "memory_save" not in approval_set
    # a tool can be approval_required but not blocked
    assert _is_blocked("deploy_container", [], []) is False
