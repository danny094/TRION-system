from __future__ import annotations

import json
import shutil
from pathlib import Path

from .contracts import BuildContext
from .render_dispatch import render_dispatch
from .render_tools import render_tools_module
from .render_wrappers import render_wrapper_module


def write_bundle(context: BuildContext) -> None:
    context.out_dir.mkdir(parents=True, exist_ok=True)
    _seed_bundle_source(context)
    _remove_stale_outputs(context)
    _write_wrapper_modules(context)
    _write_tools_modules(context)
    _write_dispatch(context)
    _write_metadata_outputs(context)


def _seed_bundle_source(context: BuildContext) -> None:
    if not isinstance(context.out_dir, Path):
        return
    if context.bundle_dir.resolve() == context.out_dir.resolve():
        return
    shutil.copytree(
        context.bundle_dir,
        context.out_dir,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc", ".DS_Store"),
    )


def _remove_stale_outputs(context: BuildContext) -> None:
    for path in _owned_output_paths(context):
        if path.exists():
            path.unlink()
    pycache_dir = context.out_dir / "__pycache__"
    if pycache_dir.exists():
        for child in pycache_dir.iterdir():
            child.unlink()
        pycache_dir.rmdir()


def _owned_output_paths(context: BuildContext) -> tuple[Path, ...]:
    module_paths = []
    for module in context.modules:
        module_paths.append(context.out_dir / f"bundle_generated_{module.output_name}.py")
        module_paths.append(context.out_dir / f"bundle_tools_{module.output_name}.py")
    legacy_paths = [
        context.out_dir / "bundle_tools_data.py",
        context.out_dir / "bundle_tools_platform.py",
    ]
    fixed_paths = [
        context.out_dir / "bundle_dispatch.py",
        context.out_dir / "mcp.json",
        context.out_dir / "requirements.txt",
        context.out_dir / "tool_intents.json",
    ]
    return tuple(module_paths + legacy_paths + fixed_paths)


def _write_wrapper_modules(context: BuildContext) -> None:
    for module in context.modules:
        path = context.out_dir / f"bundle_generated_{module.output_name}.py"
        path.write_text(render_wrapper_module(module))


def _write_tools_modules(context: BuildContext) -> None:
    for module in context.modules:
        path = context.out_dir / f"bundle_tools_{module.output_name}.py"
        path.write_text(
            render_tools_module(module, context.container_reference_contract)
        )


def _write_dispatch(context: BuildContext) -> None:
    (context.out_dir / "bundle_dispatch.py").write_text(render_dispatch(context))


def _write_metadata_outputs(context: BuildContext) -> None:
    metadata = {
        "schema_version": 1,
        "id": context.metadata["bundle_id"],
        "display_name": context.metadata["display_name"],
        "version": context.metadata["server_info"]["version"],
        "description": context.metadata["description"],
        "transport": context.metadata["transport"],
        "entry": {
            "type": context.metadata["transport"],
            "command": context.metadata["entry_command"],
        },
        "ui": context.metadata["ui"],
        "install": context.metadata["install"],
    }
    (context.out_dir / "mcp.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n"
    )
    (context.out_dir / "requirements.txt").write_text(
        "\n".join(context.metadata["requirements"]) + "\n"
    )
    (context.out_dir / "tool_intents.json").write_text(
        context.tool_intents_path.read_text()
    )
