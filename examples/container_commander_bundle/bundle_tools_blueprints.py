#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "blueprint_list",
        "description": "List blueprints with the v2 summary shape.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'blueprints': {'type': 'array', 'items': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}}, 'required': ['blueprint_id', 'name', 'description', 'version'], 'additionalProperties': True}}}, 'required': ['blueprints'], 'additionalProperties': True},
    },
    {
        "name": "blueprint_get",
        "description": "Get one blueprint with the v2 detail shape.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'description', 'version', 'definition'], 'additionalProperties': True}}, 'required': ['blueprint'], 'additionalProperties': True},
    },
    {
        "name": "blueprint_create",
        "description": "Create one blueprint in the commander store.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint": {"type": "object"}
        },
        "required": ["blueprint"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'created': {'type': 'boolean'}, 'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'definition'], 'additionalProperties': True}, 'trust': {'type': 'object', 'properties': {'level': {'type': 'string'}, 'source': {'type': 'string'}, 'image_ref': {'type': 'string'}}, 'required': ['level', 'source', 'image_ref'], 'additionalProperties': True}}, 'required': ['created', 'blueprint', 'trust'], 'additionalProperties': True},
    },
    {
        "name": "blueprint_update",
        "description": "Update one blueprint in the commander store.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"},
            "updates": {"type": "object"}
        },
        "required": ["blueprint_id", "updates"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'updated': {'type': 'boolean'}, 'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'definition'], 'additionalProperties': True}, 'trust': {'type': 'object', 'properties': {'level': {'type': 'string'}, 'source': {'type': 'string'}, 'image_ref': {'type': 'string'}}, 'required': ['level', 'source', 'image_ref'], 'additionalProperties': True}}, 'required': ['updated', 'blueprint', 'trust'], 'additionalProperties': True},
    },
    {
        "name": "blueprint_delete",
        "description": "Soft-delete one blueprint in the commander store.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'deleted': {'type': 'boolean'}, 'blueprint_id': {'type': 'string'}}, 'required': ['deleted', 'blueprint_id'], 'additionalProperties': True},
    },
    {
        "name": "blueprint_import_yaml",
        "description": "Import one blueprint from YAML.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "yaml": {"type": "string"}
        },
        "required": ["yaml"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'created': {'type': 'boolean'}, 'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'definition'], 'additionalProperties': True}, 'trust': {'type': 'object', 'properties': {'level': {'type': 'string'}, 'source': {'type': 'string'}, 'image_ref': {'type': 'string'}}, 'required': ['level', 'source', 'image_ref'], 'additionalProperties': True}, 'error': {'type': 'string'}}, 'required': [], 'additionalProperties': True, 'anyOf': [{'required': ['created', 'blueprint', 'trust']}, {'required': ['error']}]},
    },
    {
        "name": "blueprint_export_yaml",
        "description": "Export one blueprint as YAML.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'yaml': {'type': 'string'}}, 'required': ['blueprint_id', 'yaml'], 'additionalProperties': True},
    }
]
