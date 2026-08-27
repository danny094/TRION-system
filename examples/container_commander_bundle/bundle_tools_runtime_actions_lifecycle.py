#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "start_stopped_container",
        "description": "Start a stopped TRION-managed container.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'ok': {'type': 'boolean'}, 'action': {'type': 'string'}, 'container': {'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'name': {'type': 'string'}, 'image': {'type': 'string'}, 'status': {'type': 'string'}, 'created_at': {'type': 'string'}, 'managed_by_trion': {'type': 'boolean'}, 'actions_allowed': {'type': 'boolean'}, 'protected': {'type': 'boolean'}}, 'required': ['container_id', 'name', 'image', 'status'], 'additionalProperties': True}}, 'required': ['ok', 'action', 'container'], 'additionalProperties': True},
    },
    {
        "name": "stop_container",
        "description": "Stop a running TRION-managed container.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'ok': {'type': 'boolean'}, 'action': {'type': 'string'}, 'container': {'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'name': {'type': 'string'}, 'image': {'type': 'string'}, 'status': {'type': 'string'}, 'created_at': {'type': 'string'}, 'managed_by_trion': {'type': 'boolean'}, 'actions_allowed': {'type': 'boolean'}, 'protected': {'type': 'boolean'}}, 'required': ['container_id', 'name', 'image', 'status'], 'additionalProperties': True}}, 'required': ['ok', 'action', 'container'], 'additionalProperties': True},
    }
]
