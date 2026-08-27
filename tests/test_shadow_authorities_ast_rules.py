"""Tests for advisory AST shadow-authority findings."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_script():
    path = ROOT / "scripts" / "check_shadow_authorities.py"
    spec = importlib.util.spec_from_file_location("check_shadow_authorities", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def write_source(root, relative_path, source):
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return Path(relative_path)


def alias_finding(path, line):
    return f"alias_selection {path}:{line} container_id/container_name outside documented owner"


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("container_ref = container_id or container_name\n", 1),
        ("container_ref = container_id if container_id else container_name\n", 1),
        ("def choose():\n    return container_id or container_name\n", 2),
    ],
)
def test_alias_decision_outside_owner_is_review_required(tmp_path, source, line):
    module = load_script()
    path = write_source(tmp_path, "mcp/case.py", source)
    assert module.findings(tmp_path, [path]) == [alias_finding(path, line)]


def test_documented_alias_owners_and_safe_projections_are_allowed(tmp_path):
    module = load_script()
    sources = {
        "examples/container_commander_bundle/bundle_dispatch.py":
            "def normalize_container_reference():\n    return container_id or container_name\n",
        "mcp-servers/container-commander/contracts.py":
            "def normalize_container_reference():\n    return container_id or container_name\n",
        "core/consumer.py": "operation_contract = routing_frame['operation_contract']\n",
        "adapters/display.py": "def show(value):\n    return {'operation': value}\n",
        "examples/target.py":
            "def target(container_id='', container_name=''):\n    return {'container_id': container_id}\n",
    }
    paths = [write_source(tmp_path, path, source) for path, source in sources.items()]
    assert module.findings(tmp_path, paths) == []


def test_frame_rederivation_and_mixed_frame_expression_are_review_required(tmp_path):
    module = load_script()
    sources = {
        "core/raw.py": "operation_contract = derive_operation_from_text(raw_text)\n",
        "core/mixed.py":
            "operation_contract = derive_from_text(raw_text) or routing_frame.get('operation_contract')\n",
    }
    paths = [write_source(tmp_path, path, source) for path, source in sources.items()]
    assert module.findings(tmp_path, paths) == [
        "routing_signal core/raw.py:1 operation_contract re-derived outside documented owner",
        "routing_signal core/mixed.py:1 operation_contract re-derived outside documented owner",
    ]


def test_documented_frame_readers_and_neutral_fallback_are_allowed(tmp_path):
    module = load_script()
    path = write_source(
        tmp_path,
        "core/consumer.py",
        "execution_mode = str(routing_frame.get('execution_mode') or '').strip()\n"
        "dialogue_signal = dialogue_signal_from_frame(frame, text)\n"
        "live_claim = live_claim_from_frame(frame, lowered)\n",
    )
    assert module.findings(tmp_path, [path]) == []


def test_prompt_error_and_result_aliases_are_review_required(tmp_path):
    module = load_script()
    path = write_source(
        tmp_path,
        "mcp/projection.py",
        "async def admin_prompt():\n"
        "    messages = [{'content': f'Container: {container_name or container_id}'}]\n"
        "    return await _complete_commander_chat(messages=messages, model='test')\n"
        "def unavailable():\n"
        "    container_ref = container_id or container_name\n"
        "    return error_result('NOT_FOUND', f'Container {container_ref}')\n"
        "def result():\n"
        "    resolved_id = str(container_id or container_name)\n"
        "    return {'container_id': resolved_id}\n"
        "def model():\n    return ContainerLogsResult(container_id=container_id or container_name)\n",
    )
    assert module.findings(tmp_path, [path]) == [
        alias_finding(path, 2),
        alias_finding(path, 5),
        alias_finding(path, 8),
        alias_finding(path, 11),
    ]


@pytest.mark.parametrize(
    "relative_path",
    [
        "examples/container_commander_bundle/bundle_dispatch.py",
        "mcp-servers/container-commander/contracts.py",
    ],
)
def test_owner_path_wrong_function_is_review_required(tmp_path, relative_path):
    module = load_script()
    path = write_source(
        tmp_path,
        relative_path,
        "def choose_container():\n    return container_id or container_name\n",
    )
    assert module.findings(tmp_path, [path]) == [alias_finding(path, 2)]


def test_old_source_resolver_is_no_longer_an_alias_owner(tmp_path):
    module = load_script()
    path = write_source(
        tmp_path,
        "mcp-servers/container-commander/container_reference.py",
        "def resolve_container_reference():\n    return container_id or container_name\n",
    )
    assert module.findings(tmp_path, [path]) == [alias_finding(path, 2)]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("def run():\n    return {'target': container_id or container_name}\n", 2),
        ("def run():\n    return {'operation': container_id or container_name}\n", 2),
        ("def run():\n    return {'tool': container_id or container_name}\n", 2),
        ("def run():\n    execute_tool(f'{container_id or container_name}')\n", 2),
        ("def run():\n    resolve_container_reference(client, f'{container_id or container_name}')\n", 2),
        ("def run():\n    guard_allows(f'{container_id or container_name}')\n", 2),
        ("def run():\n    label = f'{container_id or container_name}'\n    execute_tool(label)\n", 2),
        ("def run():\n    label = f'{container_id or container_name}'\n    resolve_container_reference(client, label)\n", 2),
        ("def run():\n    label = f'{container_id or container_name}'\n    guard_allows(label)\n", 2),
        ("def run():\n    label = container_id or container_name\n    execute_tool(container_id=label)\n", 2),
        ("def run():\n    label = container_id or container_name\n    resolve_container_reference(client, container_id=label)\n", 2),
        ("def run():\n    label = container_id or container_name\n    guard_allows(container_id=label)\n", 2),
        ("def run():\n    payload = {'content': container_id or container_name}\n    execute_tool(payload)\n", 2),
        ("def run():\n    payload = {'container_id': container_id or container_name}\n    resolve_container_reference(client, payload)\n", 2),
        ("def run():\n    payload = {'container_id': container_id or container_name}\n    unknown_call(payload)\n", 2),
        ("def run():\n    return f'{container_id or container_name}'\n", 2),
        ("def run():\n    return {'content': container_id or container_name}\n", 2),
        ("def run():\n    return {'message': container_id or container_name}\n", 2),
    ],
)
def test_alias_flow_to_decision_context_is_review_required(tmp_path, source, line):
    module = load_script()
    path = write_source(tmp_path, "mcp/decision.py", source)
    assert module.findings(tmp_path, [path]) == [alias_finding(path, line)]
