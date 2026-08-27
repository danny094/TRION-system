from __future__ import annotations

import ast
import json
from pathlib import Path

from .contracts import BuildContext, BundleModuleSpec, ParameterSpec, SourceModuleSpec, ToolSpec
from .source_contracts import assert_contract_bindings, load_container_reference_contract


def load_context(root: Path, out_dir: Path) -> BuildContext:
    source_dir = root / "mcp-servers" / "container-commander"
    bundle_dir = root / "examples" / "container_commander_bundle"
    metadata_path = source_dir / "bundle_build_metadata.json"
    tool_intents_path = source_dir / "tool_intents.json"
    output_schemas_path = source_dir / "output_schemas.json"
    metadata = json.loads(metadata_path.read_text())
    tool_intents = json.loads(tool_intents_path.read_text())
    output_schemas = json.loads(output_schemas_path.read_text())
    reference_contract = load_container_reference_contract(source_dir / "contracts.py")
    bundle_modules = _load_bundle_modules(bundle_dir)
    order = _server_order(source_dir / "server.py")
    modules = tuple(
        _load_source_module(source_dir, stem, register_name, bundle_modules, output_schemas)
        for stem, register_name in order
    )
    assert_contract_bindings(
        modules,
        tool_intents,
        output_schemas,
        reference_contract,
    )
    return BuildContext(
        root,
        source_dir,
        bundle_dir,
        out_dir,
        metadata_path,
        metadata,
        tool_intents_path,
        tool_intents,
        output_schemas_path,
        output_schemas,
        reference_contract,
        modules,
        bundle_modules,
    )


def _load_bundle_modules(bundle_dir: Path) -> dict[str, BundleModuleSpec]:
    specs: dict[str, BundleModuleSpec] = {}
    for path in sorted(bundle_dir.glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        funcs = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
        specs[path.stem] = BundleModuleSpec(path.stem, frozenset(funcs))
    return specs


def _server_order(server_path: Path) -> list[tuple[str, str]]:
    tree = ast.parse(server_path.read_text(), filename=str(server_path))
    imports = {alias.asname or alias.name: alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names}
    order: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
            continue
        module_name = imports.get(func.value.id)
        if module_name and module_name.startswith("tools_"):
            order.append((module_name, func.attr))
    return order


def _load_source_module(source_dir: Path, stem: str, register_name: str, bundle_modules: dict[str, BundleModuleSpec], output_schemas: dict[str, dict[str, object]]) -> SourceModuleSpec:
    path = source_dir / f"{stem}.py"
    source = path.read_text()
    tree = ast.parse(source, filename=str(path))
    imports = _import_entries(tree)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    register_node = functions[register_name]
    tool_names = _register_tool_names(register_node)
    tools = tuple(
        _load_tool(
            source,
            functions[name],
            stem,
            register_name,
            imports,
            bundle_modules,
            output_schemas,
        )
        for name in tool_names
    )
    return SourceModuleSpec(stem, _output_name(stem, register_name), path, tools)


def _import_entries(tree: ast.Module) -> dict[str, str]:
    entries: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                entries[alias.asname or alias.name] = node.module
    return entries


def _register_tool_names(register_node: ast.FunctionDef) -> list[str]:
    names: list[str] = []
    for stmt in register_node.body:
        call = stmt.value if isinstance(stmt, ast.Expr) else None
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue
        if call.func.attr != "tool" or not call.args or not isinstance(call.args[0], ast.Name):
            continue
        names.append(call.args[0].id)
    return names


def _load_tool(source: str, node: ast.FunctionDef, module_name: str, register_name: str, imports: dict[str, str], bundle_modules: dict[str, BundleModuleSpec], output_schemas: dict[str, dict[str, object]]) -> ToolSpec:
    params = tuple(_parameter_specs(node))
    import_map = tuple(_tool_import_map(node, imports, bundle_modules))
    return ToolSpec(
        name=node.name,
        source_module=module_name,
        register_name=register_name,
        description=ast.get_docstring(node) or "",
        function_source=ast.get_source_segment(source, node) or "",
        parameters=params,
        import_map=import_map,
        output_schema=output_schemas.get(node.name, {}),
    )


def _parameter_specs(node: ast.FunctionDef) -> list[ParameterSpec]:
    defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + list(node.args.defaults)
    specs: list[ParameterSpec] = []
    for arg, default in zip(node.args.args, defaults):
        specs.append(ParameterSpec(arg.arg, ast.unparse(arg.annotation) if arg.annotation else None, default is not None, ast.unparse(default) if default else None))
    return specs


def _tool_import_map(node: ast.FunctionDef, imports: dict[str, str], bundle_modules: dict[str, BundleModuleSpec]) -> list[tuple[str, str, str]]:
    names = sorted({sub.id for sub in ast.walk(node) if isinstance(sub, ast.Name) and sub.id in imports})
    return [_target_binding(imports[name], name, node.name, bundle_modules) for name in names]


def _target_binding(source_module: str, imported_name: str, tool_name: str, bundle_modules: dict[str, BundleModuleSpec]) -> tuple[str, str, str]:
    module_name = _target_module(source_module, tool_name, bundle_modules)
    return imported_name, module_name, _target_callable(module_name, imported_name, tool_name, bundle_modules)


def _target_module(source_module: str, tool_name: str, bundle_modules: dict[str, BundleModuleSpec]) -> str:
    if source_module == "volume_views":
        return "bundle_snapshots" if tool_name.startswith("snapshot_") else "bundle_volumes"
    candidates = [source_module, f"bundle_{source_module}"]
    if source_module.endswith("_views"):
        candidates.append(f"bundle_{source_module[:-6]}")
    for candidate in candidates:
        if candidate in bundle_modules:
            return candidate
    raise ValueError(f"no bundle module for {source_module}")


def _target_callable(module_name: str, imported_name: str, tool_name: str, bundle_modules: dict[str, BundleModuleSpec]) -> str:
    funcs = bundle_modules[module_name].functions
    if imported_name in funcs:
        return imported_name
    if tool_name in funcs:
        return tool_name
    raise ValueError(f"no callable for {imported_name} in {module_name}")


def _output_name(stem: str, register_name: str) -> str:
    suffix = stem.removeprefix("tools_")
    if register_name == "register":
        return suffix
    return f"{suffix}_{register_name.removeprefix('register_')}"
