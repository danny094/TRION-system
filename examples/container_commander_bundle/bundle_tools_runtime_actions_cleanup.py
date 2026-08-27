#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "runtime_cleanup_all",
        "description": "Stop and remove all TRION-managed containers.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'cleaned': {'type': 'boolean'}, 'removed': {'type': 'array', 'items': {'type': 'string'}}, 'errors': {'type': 'array', 'items': {'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'error': {'type': 'string'}}, 'required': ['container_id', 'error'], 'additionalProperties': True}}}, 'required': ['cleaned', 'removed', 'errors'], 'additionalProperties': True},
    },
    {
        "name": "remove_stopped_container",
        "description": "Remove one stopped TRION-managed container.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'removed': {'type': 'boolean'}, 'container_id': {'type': 'string'}, 'blueprint_id': {'type': 'string'}, 'reason': {'type': 'string'}, 'error': {'type': 'string'}}, 'required': ['removed', 'container_id'], 'additionalProperties': True},
    }
]
