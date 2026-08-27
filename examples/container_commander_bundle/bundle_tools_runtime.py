#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "container_list",
        "description": "List containers with stable v2 summary fields.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'containers': {'type': 'array', 'items': {'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'name': {'type': 'string'}, 'image': {'type': 'string'}, 'status': {'type': 'string'}, 'created_at': {'type': 'string'}, 'managed_by_trion': {'type': 'boolean'}, 'actions_allowed': {'type': 'boolean'}, 'protected': {'type': 'boolean'}}, 'required': ['container_id', 'name', 'image', 'status', 'created_at', 'managed_by_trion', 'actions_allowed', 'protected'], 'additionalProperties': True}}}, 'required': ['containers'], 'additionalProperties': True},
    },
    {
        "name": "container_inspect",
        "description": "Inspect one container with stable v2 detail fields.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {'type': 'string'},
            "container_name": {'type': 'string'}
        },
        "oneOf": [{'required': ['container_id'], 'properties': {'container_id': {'pattern': '\\S'}, 'container_name': {'pattern': '^\\s*$'}}}, {'required': ['container_name'], 'properties': {'container_id': {'pattern': '^\\s*$'}, 'container_name': {'pattern': '\\S'}}}],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'container': {'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'name': {'type': 'string'}, 'image': {'type': 'string'}, 'status': {'type': 'string'}, 'created_at': {'type': 'string'}, 'managed_by_trion': {'type': 'boolean'}, 'actions_allowed': {'type': 'boolean'}, 'protected': {'type': 'boolean'}, 'blueprint_id': {'type': 'string'}, 'labels': {'type': 'object', 'additionalProperties': {'type': 'string'}}, 'ports': {'type': 'array', 'items': {'type': 'object', 'properties': {'host_port': {'type': 'string'}, 'container_port': {'type': 'string'}, 'protocol': {'type': 'string'}}, 'required': [], 'additionalProperties': True}}, 'mounts': {'type': 'array', 'items': {'type': 'string'}}, 'runtime_state': {'type': 'object', 'additionalProperties': True}, 'home_scope': {'type': 'object', 'additionalProperties': True}}, 'required': ['container_id', 'name', 'image', 'status', 'created_at', 'managed_by_trion', 'actions_allowed', 'protected', 'blueprint_id', 'labels', 'ports', 'mounts', 'runtime_state', 'home_scope'], 'additionalProperties': True}}, 'required': ['container'], 'additionalProperties': True},
    },
    {
        "name": "container_logs",
        "description": "Read bounded container logs.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {'type': 'string'},
            "tail": {"type": "integer", "default": 200},
            "since": {"type": "string"},
            "limit_chars": {"type": "integer", "default": 16000},
            "container_name": {'type': 'string'}
        },
        "oneOf": [{'required': ['container_id'], 'properties': {'container_id': {'pattern': '\\S'}, 'container_name': {'pattern': '^\\s*$'}}}, {'required': ['container_name'], 'properties': {'container_id': {'pattern': '^\\s*$'}, 'container_name': {'pattern': '\\S'}}}],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'logs': {'type': 'string'}, 'truncated': {'type': 'boolean'}, 'tail': {'type': 'integer'}, 'since': {'type': 'string'}, 'limit_chars': {'type': 'integer'}}, 'required': ['container_id', 'logs', 'tail', 'limit_chars'], 'additionalProperties': True},
    },
    {
        "name": "container_stats",
        "description": "Read live container resource stats with a stable v2 shape.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'container_id': {'type': 'string'}, 'cpu_percent': {'type': 'number'}, 'memory_mb': {'type': 'number'}, 'memory_limit_mb': {'type': 'number'}, 'network_rx_bytes': {'type': 'integer'}, 'network_tx_bytes': {'type': 'integer'}, 'ip_address': {'type': 'string'}, 'ports': {'type': 'array', 'items': {'type': 'object', 'properties': {'host_port': {'type': 'string'}, 'container_port': {'type': 'string'}, 'protocol': {'type': 'string'}}, 'required': [], 'additionalProperties': True}}, 'efficiency': {'type': 'object', 'properties': {'score': {'type': 'number'}, 'level': {'type': 'string'}}, 'required': ['score', 'level'], 'additionalProperties': True}, 'deploy_warnings': {'type': 'array', 'items': {'type': 'string'}}}, 'required': ['container_id', 'cpu_percent', 'memory_mb', 'memory_limit_mb', 'network_rx_bytes', 'network_tx_bytes', 'ip_address', 'ports', 'efficiency', 'deploy_warnings'], 'additionalProperties': True},
    },
    {
        "name": "runtime_quota",
        "description": "Read runtime session quota limits and current managed usage.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'max_containers': {'type': 'integer'}, 'max_total_memory_mb': {'type': 'integer'}, 'max_total_cpu': {'type': 'number'}, 'containers_used': {'type': 'integer'}, 'memory_used_mb': {'type': 'integer'}, 'cpu_used': {'type': 'number'}}, 'required': ['max_containers', 'max_total_memory_mb', 'max_total_cpu', 'containers_used', 'memory_used_mb', 'cpu_used'], 'additionalProperties': True},
    },
    {
        "name": "container_exec",
        "description": "Execute one bounded command inside a running container.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 30},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'exit_code': {'type': 'integer'}, 'output': {'type': 'string'}, 'container_id': {'type': 'string'}, 'timed_out': {'type': 'boolean'}}, 'required': ['exit_code', 'output', 'container_id'], 'additionalProperties': True},
    },
    {
        "name": "container_exec_detailed",
        "description": "Execute one bounded command and return split stdout/stderr details.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "container_id": {"type": "string"},
            "command": {"type": "string"},
            "timeout": {"type": "integer", "default": 30},
            "container_name": {"type": "string"}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'exit_code': {'type': 'integer'}, 'stdout': {'type': 'string'}, 'stderr': {'type': 'string'}, 'truncated': {'type': 'boolean'}, 'timed_out': {'type': 'boolean'}, 'container_id': {'type': 'string'}}, 'required': ['exit_code', 'stdout', 'stderr', 'truncated', 'timed_out', 'container_id'], 'additionalProperties': True},
    }
]
