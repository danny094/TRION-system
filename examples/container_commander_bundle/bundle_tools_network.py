#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "network_list",
        "description": "List TRION-managed Docker networks.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'networks': {'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'id': {'type': 'string'}, 'type': {'type': 'string'}, 'internal': {'type': 'boolean'}, 'driver': {'type': 'string'}, 'container_count': {'type': 'integer'}, 'containers': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['name', 'id', 'type', 'internal', 'driver', 'container_count', 'containers'], 'additionalProperties': True}}}, 'required': ['networks'], 'additionalProperties': True},
    },
    {
        "name": "network_info",
        "description": "Get network details for a specific container.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'networks': {'type': 'object', 'additionalProperties': {'type': 'object', 'properties': {'ip': {'type': 'string'}, 'gateway': {'type': 'string'}, 'mac': {'type': 'string'}}, 'required': [], 'additionalProperties': True}}}, 'required': ['container_id', 'networks'], 'additionalProperties': True},
    },
    {
        "name": "network_cleanup",
        "description": "Remove empty isolated TRION-managed networks.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'removed': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['removed'], 'additionalProperties': True},
    },
    {
        "name": "proxy_start",
        "description": "Enable the commander proxy policy surface.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'started': {'type': 'boolean'}, 'enabled': {'type': 'boolean'}}, 'required': ['started', 'enabled'], 'additionalProperties': True},
    },
    {
        "name": "proxy_stop",
        "description": "Disable the commander proxy policy surface.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'stopped': {'type': 'boolean'}, 'enabled': {'type': 'boolean'}}, 'required': ['stopped', 'enabled'], 'additionalProperties': True},
    },
    {
        "name": "proxy_whitelist_get",
        "description": "Read the allowed outbound domains for one blueprint.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'domains': {'type': 'array', 'items': {'type': 'string'}}, 'enabled': {'type': 'boolean'}}, 'required': ['blueprint_id', 'domains', 'enabled'], 'additionalProperties': True},
    },
    {
        "name": "proxy_whitelist_set",
        "description": "Store the allowed outbound domains for one blueprint.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"},
            "domains": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["blueprint_id", "domains"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'updated': {'type': 'boolean'}, 'blueprint_id': {'type': 'string'}, 'domains': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['updated', 'blueprint_id', 'domains'], 'additionalProperties': True},
    }
]
