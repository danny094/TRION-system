from __future__ import annotations

from pathlib import Path

from .path_policy import entry_from_target, open_target


def metadata_for(root: Path, relative_path: str) -> dict[str, object]:
    with open_target(root, relative_path) as target:
        return entry_from_target(target)
