#!/usr/bin/env python3
"""DEPRECATED 2026-09-15 compatibility facade for ``check_code_caps.py``."""
from __future__ import annotations

import sys

if __package__:
    from .check_code_caps import CODE_SUFFIXES, LINE_CAP, find_violations, main
else:
    from check_code_caps import CODE_SUFFIXES, LINE_CAP, find_violations, main

__all__ = ("CODE_SUFFIXES", "LINE_CAP", "find_violations", "main")


if __name__ == "__main__":
    sys.exit(main())
