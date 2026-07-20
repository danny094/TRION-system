from core.task_loop.document_resolution import collect_result_artifacts


def test_collect_result_artifacts_keeps_generic_tool_output_for_simple_tools():
    artifacts = collect_result_artifacts(
        "time_now",
        "tool_1",
        {"utc_iso": "2026-05-12T13:55:52Z", "time": "13:55:52"},
        [],
    )

    assert len(artifacts) == 1
    assert artifacts[0]["artifact_type"] == "tool_result"
    assert "utc_iso" in artifacts[0]["result"]


def test_collect_result_artifacts_keeps_semantic_search_artifacts_and_generic_output():
    artifacts = collect_result_artifacts(
        "memory_semantic_search",
        "tool_2",
        {
            "results": [
                {
                    "metadata": {"workspace_entry_id": 42},
                    "similarity": 0.91,
                }
            ]
        },
        [],
    )

    assert artifacts[0]["artifact_type"] == "tool_result"
    assert artifacts[1]["artifact_type"] == "semantic_search_result"
    assert artifacts[1]["workspace_entry_id"] == 42
