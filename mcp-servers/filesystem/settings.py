from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


PRODUCT_ROOT = Path("/trion-home")


class FilesystemConfigurationError(RuntimeError):
    pass


def load_root(environ: Mapping[str, str] | None = None) -> Path:
    source = os.environ if environ is None else environ
    raw = str(source.get("TRION_FILESYSTEM_ROOT", str(PRODUCT_ROOT))).strip()
    candidate = Path(raw)
    if not candidate.is_absolute() or candidate != PRODUCT_ROOT:
        raise FilesystemConfigurationError("TRION_FILESYSTEM_ROOT must be exactly /trion-home")
    if not candidate.is_dir():
        raise FilesystemConfigurationError("TRION_FILESYSTEM_ROOT must exist as a directory")
    return candidate
