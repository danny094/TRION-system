import json
import sys
from pathlib import Path

import container_commander_bundle_fakes  # noqa: F401
import mcp.installer_runtime as installer_runtime
from mcp.installer_manifest_normalize import normalize_mcp_manifest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from container_commander_bundle_gen.render_bundle import write_bundle  # noqa: E402
from container_commander_bundle_gen.source_ast import load_context  # noqa: E402
from container_commander_bundle_fakes import BUNDLE_DIR  # noqa: E402
from project_mcp_protocol_version import (  # noqa: E402
    project_protocol_version_literals,
    read_protocol_version_literal,
)
import bundle_dispatch  # noqa: E402

METADATA_PATH = ROOT / "mcp-servers" / "container-commander" / "bundle_build_metadata.json"


def _bundle_manifest():
    return json.loads((BUNDLE_DIR / "mcp.json").read_text(encoding="utf-8"))


def _bundle_requirements():
    return (BUNDLE_DIR / "requirements.txt").read_text(encoding="utf-8").splitlines()


def _owned_bundle_paths():
    names = {"bundle_dispatch.py", "mcp.json", "requirements.txt", "tool_intents.json"}
    names.update(path.name for path in BUNDLE_DIR.glob("bundle_generated_*.py"))
    names.update(path.name for path in BUNDLE_DIR.glob("bundle_tools_*.py"))
    return tuple(sorted(names))


def _bundle_files(bundle_dir):
    return tuple(
        sorted(
            path.relative_to(bundle_dir)
            for path in bundle_dir.rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and "__MACOSX" not in path.parts
            and ".pytest_cache" not in path.parts
            and path.name != ".DS_Store"
            and path.suffix != ".pyc"
        )
    )


def _generated_context(tmp_path):
    out_dir = tmp_path / "generated_bundle"
    context = load_context(ROOT, out_dir)
    write_bundle(context)
    return out_dir, context


def test_generator_outputs_are_byte_identical_to_committed_bundle(tmp_path):
    out_dir, _context = _generated_context(tmp_path)
    for name in _owned_bundle_paths():
        assert (out_dir / name).read_bytes() == (BUNDLE_DIR / name).read_bytes(), name


def test_generator_output_is_complete_installable_bundle(tmp_path):
    out_dir, _context = _generated_context(tmp_path)
    source_files = _bundle_files(BUNDLE_DIR)

    assert _bundle_files(out_dir) == source_files
    assert not any("__pycache__" in path.parts or ".pytest_cache" in path.parts or path.name == ".DS_Store" or path.suffix == ".pyc" for path in out_dir.rglob("*"))
    for relative_path in source_files:
        assert (out_dir / relative_path).read_bytes() == (BUNDLE_DIR / relative_path).read_bytes()


def test_protocol_version_is_projected_without_runtime_import(tmp_path):
    version = read_protocol_version_literal()
    target = tmp_path / "server.py"
    target.write_text('MCP_PROTOCOL_VERSION = "stale"\n', encoding="utf-8")
    assert project_protocol_version_literals(target_paths=(target,)) == version
    assert target.read_text(encoding="utf-8") == f'MCP_PROTOCOL_VERSION = "{version}"\n'

    time_source = (ROOT / "examples" / "time_mcp_bundle" / "server.py").read_text(encoding="utf-8")
    projection_source = (ROOT / "scripts" / "project_mcp_protocol_version.py").read_text(encoding="utf-8")
    commander_source = (BUNDLE_DIR / "bundle_dispatch.py").read_text(encoding="utf-8")
    assert f'MCP_PROTOCOL_VERSION = "{version}"' in time_source
    assert bundle_dispatch.MCP_PROTOCOL_VERSION == version
    assert "from mcp" not in projection_source
    assert "from mcp" not in time_source
    assert "from mcp" not in commander_source


def test_bundle_metadata_contract_is_derived_from_source_truth():
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    manifest = _bundle_manifest()
    assert manifest["entry"]["command"] == metadata["entry_command"]
    assert _bundle_requirements() == metadata["requirements"]


def test_dispatch_guard_rejects_invalid_container_reference_before_tool_call(monkeypatch):
    calls = []

    def fake_tool(container_id="", container_name=""):
        calls.append((container_id, container_name))
        return {"ok": True}

    monkeypatch.setattr(bundle_dispatch, "_find_tool", lambda _name: fake_tool)
    for arguments in ({}, {"container_id": "c1", "container_name": "demo"}):
        response = bundle_dispatch.handle_request(
            {
                "jsonrpc": "2.0",
                "id": "req-1",
                "method": "tools/call",
                "params": {"name": "container_stats", "arguments": arguments},
            }
        )
        assert response["error"] == {
            "code": -32602,
            "message": "Provide exactly one of container_id or container_name",
        }
    assert calls == []


def test_dispatch_guard_resolves_container_name_before_tool_call(monkeypatch):
    seen = {}

    def fake_tool(container_id="", container_name=""):
        seen["container_id"] = container_id
        seen["container_name"] = container_name
        return {"container_id": container_id}

    class _Container:
        id = "resolved-id"

    monkeypatch.setattr(bundle_dispatch, "_find_tool", lambda _name: fake_tool)
    monkeypatch.setattr(bundle_dispatch.bundle_docker, "get_docker_client", lambda: object())
    monkeypatch.setattr(
        bundle_dispatch,
        "resolve_container_reference",
        lambda client, container_name: _Container(),
    )
    response = bundle_dispatch.handle_request(
        {
            "jsonrpc": "2.0",
            "id": "req-2",
            "method": "tools/call",
            "params": {"name": "container_stats", "arguments": {"container_name": "demo"}},
        }
    )
    assert response["result"] == {
        "content": [],
        "structuredContent": {"container_id": "resolved-id"},
        "isError": False,
    }
    assert seen == {"container_id": "resolved-id", "container_name": ""}


def test_derived_tool_count_matches_generated_bundle_without_name_mirror(tmp_path):
    _out_dir, context = _generated_context(tmp_path)
    derived_names = tuple(tool.name for module in context.modules for tool in module.tools)
    committed_names = tuple(tool["name"] for tool in bundle_dispatch.TOOLS)
    assert len(derived_names) == 46
    assert committed_names == derived_names


def test_installer_runtime_consumes_manifest_command_and_requirements_single_path(monkeypatch, tmp_path):
    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    manifest = normalize_mcp_manifest(_bundle_manifest())
    calls = []

    monkeypatch.setattr(
        installer_runtime,
        "create_venv",
        lambda venv_dir: calls.append(("create_venv", venv_dir)),
    )
    monkeypatch.setattr(
        installer_runtime,
        "install_requirements",
        lambda venv_dir, requirements_path: calls.append(("install_requirements", venv_dir, requirements_path)),
    )

    target_dir = tmp_path / "install_target"
    target_dir.mkdir()
    state = installer_runtime.prepare_runtime(target_dir, manifest)

    assert state == {"runtime_kind": "venv", "runtime_created_paths": [str(target_dir / ".venv")]}
    assert calls == [
        ("create_venv", target_dir / ".venv"),
        ("install_requirements", target_dir / ".venv", target_dir / "requirements.txt"),
    ]
    assert manifest["command"] == metadata["entry_command"]
    assert manifest["cwd"] == str(target_dir)
