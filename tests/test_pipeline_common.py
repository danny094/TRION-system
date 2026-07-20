from core.pipeline.common import merge_thinking_contexts


def test_merge_thinking_contexts_preserves_tool_details():
    merged = merge_thinking_contexts(
        {
            "available_tools": ["container_inspect"],
            "selected_tools": ["container_inspect"],
            "selected_tool_details": [
                {"name": "container_inspect", "capability_required_args": ["container_id_or_name"]}
            ],
            "context": {"home_context": {"container_id": "abc123"}},
        },
        {"context": {"document_tool_mode": "none"}},
    )

    assert merged["selected_tools"] == ["container_inspect"]
    assert merged["selected_tool_details"] == [
        {"name": "container_inspect", "capability_required_args": ["container_id_or_name"]}
    ]
    assert merged["context"]["home_context"]["container_id"] == "abc123"
