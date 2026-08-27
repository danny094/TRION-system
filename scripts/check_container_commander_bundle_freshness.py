#!/usr/bin/env python3
"""Regenerate the Container Commander bundle in temp storage and compare it.

The committed bundle remains the comparison target. This script neither writes
to it nor chooses which source or bundle contract is authoritative.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True

COMMITTED_BUNDLE = Path("examples/container_commander_bundle")
FIXED_GENERATOR_OUTPUTS = frozenset(
    {"bundle_dispatch.py", "mcp.json", "requirements.txt", "tool_intents.json"}
)


class _MemoryFile:
    def __init__(self, files: dict[Path, bytes], path: Path) -> None:
        self._files = files
        self._path = path

    def exists(self) -> bool:
        return False

    def unlink(self) -> None:
        raise AssertionError("read-only generation must not unlink")

    def write_text(self, content: str) -> None:
        self._files[self._path] = content.encode("utf-8")


class _MemoryDirectory:
    def __init__(self) -> None:
        self.files: dict[Path, bytes] = {}

    def mkdir(self, **_kwargs: object) -> None:
        return None

    def exists(self) -> bool:
        return False

    def iterdir(self) -> tuple[()]:
        return ()

    def rmdir(self) -> None:
        raise AssertionError("read-only generation must not remove directories")

    def __truediv__(self, name: str) -> _MemoryFile:
        return _MemoryFile(self.files, Path(name))


def compare(expected_files: dict[Path, bytes], generated: dict[Path, bytes]) -> list[str]:
    differences = []
    for path in sorted(set(expected_files) | set(generated)):
        if path not in expected_files:
            differences.append(f"unexpected generated file: {path}")
        elif path not in generated:
            differences.append(f"missing generated file: {path}")
        elif expected_files[path] != generated[path]:
            differences.append(f"content differs: {path}")
    return differences


def is_generator_owned(path: Path) -> bool:
    return path.name in FIXED_GENERATOR_OUTPUTS or path.name.startswith(
        ("bundle_generated_", "bundle_tools_")
    )


def tracked_generated_files(root: Path, bundle: Path, generated: dict[Path, bytes]) -> tuple[dict[Path, bytes], list[str]]:
    result = subprocess.run(
        ["git", "ls-files", "--", str(bundle)], cwd=root, capture_output=True, text=True, check=True
    )
    tracked = {Path(path).relative_to(bundle) for path in result.stdout.splitlines() if path.strip()}
    expected_files: dict[Path, bytes] = {}
    differences: list[str] = []
    for path in sorted(path for path in tracked if is_generator_owned(path)):
        expected_path = root / bundle / path
        if not expected_path.is_file():
            differences.append(f"tracked bundle file is missing: {path}")
            continue
        expected_files[path] = expected_path.read_bytes()
    for path in generated:
        if path not in tracked:
            differences.append(f"generated file is not tracked: {path}")
    return expected_files, differences


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    expected = root / COMMITTED_BUNDLE
    if not expected.is_dir():
        print(f"Bundle freshness check: expected directory is missing: {expected}")
        return 1
    sys.path.insert(0, str(root / "scripts"))
    from container_commander_bundle_gen.render_bundle import write_bundle
    from container_commander_bundle_gen.source_ast import load_context

    generated = _MemoryDirectory()
    write_bundle(load_context(root, generated))
    expected_files, differences = tracked_generated_files(root, COMMITTED_BUNDLE, generated.files)
    differences += compare(expected_files, generated.files)
    if not differences:
        print("Bundle freshness check: generated output matches the committed bundle.")
        return 0
    print("Bundle freshness check: generated output differs:")
    print("\n".join(f"  {difference}" for difference in differences))
    return 1


if __name__ == "__main__":
    sys.exit(main())
