#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "volume_list",
        "description": "List TRION-managed workspace volumes.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'volumes': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'blueprint_id': {'type': 'string'}, 'created_at': {'type': 'string'}, 'driver': {'type': 'string'}, 'mountpoint': {'type': 'string'}}, 'required': ['name', 'blueprint_id', 'created_at', 'driver', 'mountpoint'], 'additionalProperties': True}}}, 'required': ['volumes'], 'additionalProperties': True},
    },
    {
        "name": "volume_get",
        "description": "Get one volume with snapshot metadata.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "volume_name": {"type": "string"}
        },
        "required": ["volume_name"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'volume': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'blueprint_id': {'type': 'string'}, 'created_at': {'type': 'string'}, 'driver': {'type': 'string'}, 'mountpoint': {'type': 'string'}, 'snapshots': {'type': 'array', 'items': {'type': 'object', 'properties': {'filename': {'type': 'string'}, 'size_mb': {'type': 'number'}, 'created_at': {'type': 'string'}}, 'required': ['filename', 'size_mb', 'created_at'], 'additionalProperties': True}}}, 'required': ['name', 'blueprint_id', 'created_at', 'driver', 'mountpoint', 'snapshots'], 'additionalProperties': True}}, 'required': ['volume'], 'additionalProperties': True},
    },
    {
        "name": "volume_remove",
        "description": "Remove one workspace volume.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "volume_name": {"type": "string"},
            "force": {"type": "boolean", "default": False}
        },
        "required": ["volume_name"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'removed': {'type': 'boolean'}, 'volume': {'type': 'string'}}, 'required': ['removed', 'volume'], 'additionalProperties': True},
    },
    {
        "name": "volume_cleanup",
        "description": "Find and optionally remove orphaned workspace volumes.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "dry_run": {"type": "boolean", "default": True}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'orphaned': {'type': 'array', 'items': {'type': 'string'}}, 'dry_run': {'type': 'boolean'}}, 'required': ['orphaned', 'dry_run'], 'additionalProperties': True},
    },
    {
        "name": "snapshot_list",
        "description": "List snapshots, optionally filtered by volume prefix.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "volume_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'snapshots': {'type': 'array', 'items': {'type': 'object', 'properties': {'filename': {'type': 'string'}, 'size_mb': {'type': 'number'}, 'created_at': {'type': 'string'}}, 'required': ['filename', 'size_mb', 'created_at'], 'additionalProperties': True}}}, 'required': ['snapshots'], 'additionalProperties': True},
    },
    {
        "name": "snapshot_delete",
        "description": "Delete one stored snapshot tarball.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "filename": {"type": "string"}
        },
        "required": ["filename"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'deleted': {'type': 'boolean'}, 'filename': {'type': 'string'}}, 'required': ['deleted', 'filename'], 'additionalProperties': True},
    },
    {
        "name": "snapshot_create",
        "description": "Create one snapshot tarball for a workspace volume.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "volume_name": {"type": "string"},
            "tag": {"type": "string"}
        },
        "required": ["volume_name"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'created': {'type': 'boolean'}, 'filename': {'type': 'string'}, 'volume': {'type': 'string'}}, 'required': ['created', 'filename', 'volume'], 'additionalProperties': True},
    },
    {
        "name": "snapshot_restore",
        "description": "Restore one snapshot tarball into a target or derived volume.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "target_volume": {"type": "string"}
        },
        "required": ["filename"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'restored': {'type': 'boolean'}, 'volume': {'type': 'string'}, 'filename': {'type': 'string'}}, 'required': ['restored', 'volume', 'filename'], 'additionalProperties': True},
    }
]
