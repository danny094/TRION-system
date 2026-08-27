#!/usr/bin/env python3
import json

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    yaml = None


def json_text(value, default):
    return json.dumps(value if value is not None else default)


def parse_simple_yaml(yaml_content):
    data = {}
    for raw_line in yaml_content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"unsupported yaml line: {raw_line}")
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            raise ValueError(f"missing key in yaml line: {raw_line}")
        if value in {"", "null", "~"}:
            parsed = None
        elif value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
            parsed = value[1:-1]
        elif value in {"true", "false"}:
            parsed = value == "true"
        elif value.startswith("[") or value.startswith("{"):
            parsed = json.loads(value)
        else:
            parsed = value
        data[key] = parsed
    return data


def yaml_load(yaml_content):
    if yaml is not None:
        data = yaml.safe_load(yaml_content) or {}
    else:
        data = parse_simple_yaml(yaml_content)
    if not isinstance(data, dict):
        raise ValueError("yaml must describe an object")
    return data


def yaml_dump(data):
    if yaml is not None:
        return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    lines = []
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            rendered = json.dumps(value, ensure_ascii=False)
        elif value is None:
            rendered = "null"
        elif isinstance(value, bool):
            rendered = "true" if value else "false"
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    return "\n".join(lines) + ("\n" if lines else "")
