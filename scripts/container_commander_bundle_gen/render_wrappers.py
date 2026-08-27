from __future__ import annotations

from collections import defaultdict

from .contracts import SourceModuleSpec


def render_wrapper_module(module: SourceModuleSpec) -> str:
    imports: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for tool in module.tools:
        for imported_name, target_module, target_name in tool.import_map:
            imports[target_module].append((imported_name, target_name))
    lines = ["#!/usr/bin/env python3", ""]
    for target_module in sorted(imports):
        parts = []
        seen: set[tuple[str, str]] = set()
        for imported_name, target_name in imports[target_module]:
            pair = (imported_name, target_name)
            if pair in seen:
                continue
            seen.add(pair)
            parts.append(target_name if target_name == imported_name else f"{target_name} as {imported_name}")
        lines.append(f"from {target_module} import {', '.join(parts)}")
    lines.append("")
    for tool in module.tools:
        lines.append(tool.function_source.rstrip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
