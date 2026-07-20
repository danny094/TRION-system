import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from mcp.installer_common import InstallationError


def prepare_runtime(target_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any]:
    entry = manifest.get("entry") or {}
    entry_type = str(entry.get("type", "")).strip()
    runtime = ((manifest.get("install") or {}).get("runtime") or {})
    runtime_kind = str(runtime.get("kind", "")).strip() or default_runtime_kind(entry_type)

    if entry_type != "stdio":
        return {
            "runtime_kind": runtime_kind,
            "runtime_created_paths": [],
        }

    if runtime_kind == "venv":
        venv_dir = target_dir / ".venv"
        create_venv(venv_dir)
        install_requirements(venv_dir, target_dir / "requirements.txt")
        manifest["command"] = str(entry.get("command", "")).strip()
        manifest["cwd"] = str(target_dir)
        return {
            "runtime_kind": "venv",
            "runtime_created_paths": [str(venv_dir)],
        }

    manifest["command"] = str(entry.get("command", "")).strip()
    manifest["cwd"] = str(target_dir)
    return {
        "runtime_kind": runtime_kind,
        "runtime_created_paths": [],
    }


def default_runtime_kind(entry_type: str) -> str:
    if entry_type == "stdio":
        return "venv"
    return "remote_url"


def create_venv(venv_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(venv_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InstallationError(f"Virtual environment creation failed: {result.stderr}", venv_dir.parent)


def install_requirements(venv_dir: Path, requirements_path: Path) -> None:
    if not requirements_path.exists():
        return
    python_bin = venv_dir / "bin" / "python"
    result = subprocess.run(
        [str(python_bin), "-m", "pip", "install", "-r", str(requirements_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise InstallationError(f"Dependency installation failed: {result.stderr}", venv_dir.parent)
