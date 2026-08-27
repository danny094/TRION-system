#!/usr/bin/env python3
TOOLS_PART = [
    {
        "name": "marketplace_bundle_list",
        "description": "List exported marketplace bundles from the commander marketplace directory.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'bundles': {'type': 'array', 'items': {'type': 'object', 'properties': {'filename': {'type': 'string'}, 'size_mb': {'type': 'number'}, 'id': {'type': 'string'}, 'name': {'type': 'string'}, 'version': {'type': 'string'}, 'tags': {'type': 'array', 'items': {}}, 'exported_at': {'type': 'string'}}, 'required': ['filename', 'size_mb', 'id', 'name', 'version', 'tags', 'exported_at'], 'additionalProperties': True}}, 'count': {'type': 'integer'}}, 'required': ['bundles', 'count'], 'additionalProperties': True},
    },
    {
        "name": "marketplace_starter_list",
        "description": "List built-in starter blueprints.",
        "inputSchema": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'starters': {'type': 'array', 'items': {'type': 'object', 'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'icon': {'type': 'string'}, 'tags': {'type': 'array', 'items': {'type': 'string'}}, 'network': {'type': 'string'}, 'dockerfile': {'type': 'string'}, 'resources': {'type': 'object', 'additionalProperties': True}}, 'required': ['id', 'name', 'description', 'icon', 'tags', 'network', 'dockerfile', 'resources'], 'additionalProperties': True}}, 'count': {'type': 'integer'}}, 'required': ['starters', 'count'], 'additionalProperties': True},
    },
    {
        "name": "marketplace_catalog_list",
        "description": "List cached catalog entries, optionally filtered by category and trust.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "category": {"type": "string"},
            "trusted_only": {"type": "boolean", "default": False}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'source': {'type': 'object', 'additionalProperties': True}, 'schema_version': {'type': 'string'}, 'trion_compat': {'type': 'object', 'additionalProperties': True}, 'synced_at': {'type': 'string'}, 'categories': {'type': 'object', 'additionalProperties': {'type': 'integer'}}, 'blueprints': {'type': 'array', 'items': {'type': 'object', 'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'category': {'type': 'string'}, 'tags': {'type': 'array', 'items': {'type': 'string'}}, 'icon': {'type': 'string'}, 'difficulty': {'type': 'string'}, 'network': {'type': 'string'}, 'requires_secrets': {'type': 'boolean'}, 'requires_runtime': {'type': 'string'}, 'requires_approval': {'type': 'boolean'}, 'requires_gpu': {'type': 'boolean'}, 'trusted_level': {'type': 'string'}, 'author': {'type': 'string'}, 'version': {'type': 'string'}, 'yaml_url': {'type': 'string'}, 'bundle_url': {'type': 'string'}, 'package_type': {'type': 'string'}, 'has_host_companion': {'type': 'boolean'}, 'supports_trion_addons': {'type': 'boolean'}, 'downloads': {'type': 'integer'}, 'stars': {'type': 'integer'}, 'health_profile': {'type': 'object', 'properties': {'ready_timeout_seconds': {'type': 'integer'}, 'interval_seconds': {'type': 'integer'}, 'timeout_seconds': {'type': 'integer'}, 'retries': {'type': 'integer'}}, 'required': ['ready_timeout_seconds', 'interval_seconds', 'timeout_seconds', 'retries'], 'additionalProperties': True}}, 'required': ['id', 'name', 'category', 'tags', 'network', 'requires_secrets', 'requires_runtime', 'requires_approval', 'requires_gpu', 'trusted_level', 'version', 'yaml_url', 'downloads', 'stars', 'health_profile'], 'additionalProperties': True}}, 'count': {'type': 'integer'}, 'category': {'type': 'string'}, 'trusted_only': {'type': 'boolean'}}, 'required': ['source', 'schema_version', 'trion_compat', 'synced_at', 'categories', 'blueprints', 'count', 'category', 'trusted_only'], 'additionalProperties': True},
    },
    {
        "name": "marketplace_catalog_sync",
        "description": "Refresh the remote blueprint catalog cache from a GitHub-backed index.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "repo_url": {"type": "string"},
            "branch": {"type": "string", "default": 'main'}
        },
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'synced': {'type': 'boolean'}, 'count': {'type': 'integer'}, 'categories': {'type': 'object', 'additionalProperties': {'type': 'integer'}}, 'synced_at': {'type': 'string'}, 'source': {'type': 'object', 'additionalProperties': True}, 'schema_version': {'type': 'string'}, 'trion_compat': {'type': 'object', 'additionalProperties': True}}, 'required': ['synced', 'count', 'categories', 'synced_at', 'source', 'schema_version', 'trion_compat'], 'additionalProperties': True},
    },
    {
        "name": "marketplace_starter_install",
        "description": "Install one built-in starter blueprint into the commander store.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "starter_id": {"type": "string"}
        },
        "required": ["starter_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'installed': {'type': 'boolean'}, 'exists': {'type': 'boolean'}, 'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'definition'], 'additionalProperties': True}, 'error': {'type': 'string'}}, 'required': [], 'additionalProperties': True, 'anyOf': [{'required': ['installed', 'blueprint']}, {'required': ['exists', 'blueprint']}, {'required': ['error']}]},
    },
    {
        "name": "marketplace_catalog_install",
        "description": "Install one blueprint from the cached remote catalog.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"},
            "overwrite": {"type": "boolean", "default": False}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'installed': {'type': 'boolean'}, 'exists': {'type': 'boolean'}, 'imported': {'type': 'boolean'}, 'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'definition'], 'additionalProperties': True}, 'trust': {'type': 'object', 'properties': {'level': {'type': 'string'}, 'source': {'type': 'string'}, 'image_ref': {'type': 'string'}}, 'required': ['level', 'source', 'image_ref'], 'additionalProperties': True}, 'source': {'type': 'object', 'properties': {'id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'category': {'type': 'string'}, 'tags': {'type': 'array', 'items': {'type': 'string'}}, 'icon': {'type': 'string'}, 'difficulty': {'type': 'string'}, 'network': {'type': 'string'}, 'requires_secrets': {'type': 'boolean'}, 'requires_runtime': {'type': 'string'}, 'requires_approval': {'type': 'boolean'}, 'requires_gpu': {'type': 'boolean'}, 'trusted_level': {'type': 'string'}, 'author': {'type': 'string'}, 'version': {'type': 'string'}, 'yaml_url': {'type': 'string'}, 'bundle_url': {'type': 'string'}, 'package_type': {'type': 'string'}, 'has_host_companion': {'type': 'boolean'}, 'supports_trion_addons': {'type': 'boolean'}, 'downloads': {'type': 'integer'}, 'stars': {'type': 'integer'}, 'health_profile': {'type': 'object', 'properties': {'ready_timeout_seconds': {'type': 'integer'}, 'interval_seconds': {'type': 'integer'}, 'timeout_seconds': {'type': 'integer'}, 'retries': {'type': 'integer'}}, 'required': ['ready_timeout_seconds', 'interval_seconds', 'timeout_seconds', 'retries'], 'additionalProperties': True}}, 'required': ['id', 'name', 'category', 'tags', 'network', 'requires_secrets', 'requires_runtime', 'requires_approval', 'requires_gpu', 'trusted_level', 'version', 'yaml_url', 'downloads', 'stars', 'health_profile'], 'additionalProperties': True}, 'filename': {'type': 'string'}, 'error': {'type': 'string'}}, 'required': [], 'additionalProperties': True, 'anyOf': [{'required': ['installed', 'blueprint']}, {'required': ['exists', 'blueprint']}, {'required': ['imported']}, {'required': ['error']}]},
    },
    {
        "name": "marketplace_bundle_export",
        "description": "Export one blueprint as a shareable TRION bundle.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "blueprint_id": {"type": "string"}
        },
        "required": ["blueprint_id"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'exported': {'type': 'boolean'}, 'filename': {'type': 'string'}, 'blueprint_id': {'type': 'string'}}, 'required': ['exported', 'blueprint_id'], 'additionalProperties': True},
    },
    {
        "name": "marketplace_bundle_import",
        "description": "Import one TRION bundle from base64-encoded archive bytes.",
        "inputSchema": {
        "type": "object",
        "properties": {
            "bundle_bytes_b64": {"type": "string"},
            "filename": {"type": "string"},
            "overwrite": {"type": "boolean", "default": False}
        },
        "required": ["bundle_bytes_b64"],
        "additionalProperties": False,
        },
        "outputSchema": {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'type': 'object', 'properties': {'imported': {'type': 'boolean'}, 'created': {'type': 'boolean'}, 'updated': {'type': 'boolean'}, 'filename': {'type': 'string'}, 'blueprint': {'type': 'object', 'properties': {'blueprint_id': {'type': 'string'}, 'name': {'type': 'string'}, 'description': {'type': 'string'}, 'version': {'type': 'string'}, 'definition': {'type': 'object', 'additionalProperties': True}}, 'required': ['blueprint_id', 'name', 'definition'], 'additionalProperties': True}, 'trust': {'type': 'object', 'properties': {'level': {'type': 'string'}, 'source': {'type': 'string'}, 'image_ref': {'type': 'string'}}, 'required': ['level', 'source', 'image_ref'], 'additionalProperties': True}, 'error': {'type': 'string'}}, 'required': [], 'additionalProperties': True, 'anyOf': [{'required': ['imported']}, {'required': ['error']}]},
    }
]
