#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "host_companion_check",
        "description": "Inspect host-companion/package manifest status for one blueprint.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'checked': {'type': 'boolean'}, 'blueprint_id': {'type': 'string'}, 'configured': {'type': 'boolean'}, 'status': {'type': 'string'}, 'host_companion': {'type': 'object', 'additionalProperties': True}, 'package_manifest_present': {'type': 'boolean'}, 'package_type': {'type': 'string'}}, 'required': ['checked', 'blueprint_id', 'configured', 'status', 'host_companion', 'package_manifest_present', 'package_type'], 'additionalProperties': True},
    },
    {
        "name": "host_companion_repair",
        "description": "Attempt host-companion repair for one blueprint.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'repaired': {'type': 'boolean'}, 'skipped': {'type': 'boolean'}, 'reason': {'type': 'string'}, 'blueprint_id': {'type': 'string'}, 'host_companion': {'type': 'object', 'additionalProperties': True}, 'package_manifest_present': {'type': 'boolean'}}, 'required': ['repaired', 'skipped', 'reason', 'blueprint_id'], 'additionalProperties': True},
    },
    {
        "name": "host_companion_uninstall",
        "description": "Attempt host-companion uninstall for one blueprint.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'uninstalled': {'type': 'boolean'}, 'skipped': {'type': 'boolean'}, 'reason': {'type': 'string'}, 'removed_paths': {'type': 'array', 'items': {'type': 'string'}}, 'blueprint_id': {'type': 'string'}, 'host_companion': {'type': 'object', 'additionalProperties': True}, 'package_manifest_present': {'type': 'boolean'}}, 'required': ['uninstalled', 'skipped', 'reason', 'removed_paths', 'blueprint_id'], 'additionalProperties': True},
    },
    {
        "name": "package_manifest_get",
        "description": "Read the local package manifest for one blueprint if present.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'manifest': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'manifest'], 'additionalProperties': True},
    }
]
