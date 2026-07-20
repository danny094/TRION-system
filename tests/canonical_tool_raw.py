def canonical_raw_tool(
    name: str, domain: str, operation: str, *, evidence: list[str],
    required: list[str], scopes: list[str], output_schema: str = "",
) -> dict:
    return {
        "name": name,
        "tool_intent": {
            "name": name,
            "domain": domain,
            "operation": operation,
            "evidence_types": evidence,
            "requires": required,
            "target_scopes": scopes,
            "risk": "read_only",
            "output_schema": output_schema,
            "tool_intent_meta": {
                "schema_version": 1,
                "source_sha256": "a" * 64,
                "bundle_version": "test",
            },
        },
    }
