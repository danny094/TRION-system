#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "dashboard_overview",
        "description": "Aggregate commander runtime inventory into a dashboard-shaped read model.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'generated_at': {'type': 'string'}, 'health': {'type': 'object', 'properties': {'runtime': {'type': 'string'}, 'blueprint_store': {'type': 'string'}, 'proxy_policy': {'type': 'string'}}, 'required': ['runtime', 'blueprint_store', 'proxy_policy'], 'additionalProperties': True}, 'resources': {'type': 'object', 'properties': {'containers': {'type': 'object', 'properties': {'total': {'type': 'integer'}, 'running': {'type': 'integer'}, 'stopped': {'type': 'integer'}}, 'required': ['total', 'running', 'stopped'], 'additionalProperties': True}, 'blueprints': {'type': 'object', 'properties': {'total': {'type': 'integer'}}, 'required': ['total'], 'additionalProperties': True}, 'networks': {'type': 'object', 'properties': {'total': {'type': 'integer'}}, 'required': ['total'], 'additionalProperties': True}, 'volumes': {'type': 'object', 'properties': {'total': {'type': 'integer'}}, 'required': ['total'], 'additionalProperties': True}}, 'required': ['containers', 'blueprints', 'networks', 'volumes'], 'additionalProperties': True}, 'alerts': {'type': 'array', 'items': {'type': 'object', 'properties': {'level': {'type': 'string'}, 'message': {'type': 'string'}}, 'required': ['level', 'message'], 'additionalProperties': True}}, 'events': {'type': 'array', 'items': {'type': 'object', 'additionalProperties': True}}}, 'required': ['generated_at', 'health', 'resources', 'alerts', 'events'], 'additionalProperties': True},
    }
]
