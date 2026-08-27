import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.output import generate_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan

def test_generate_output_rejects_pseudo_tool_markup_without_recovery():
    async def fake_complete_output(output_request, chat_request, **kwargs):
        return type(
            "Result",
            (),
            {
                "content": '[TOOL_CALL]\n{tool => "memory_graph_search", args => { --query "Python" }}\n[/TOOL_CALL]',
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    plan = ThinkingPlan(
        intent="Memory-Suchen ausführen",
        steps=[
            PlanStep("tool_1", "Attempt 1", "Search Python", tool="memory_graph_search", tool_arguments={"query": "Python"}),
            PlanStep("tool_2", "Attempt 2", "Search Projekt", tool="memory_graph_search", tool_arguments={"query": "Projekt"}),
            PlanStep("tool_3", "Attempt 3", "Search Name", tool="memory_graph_search", tool_arguments={"query": "Name"}),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
    )

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text='Führe 3 Memory-Suchen aus: "Python", "Projekt", "Name".',
                thinking_plan=plan,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "task_loop": {
                        "artifacts": [
                            {"artifact_type": "tool_result", "source_step_id": "tool_1", "output": '{"count":0,"results":[]}'},
                            {"artifact_type": "tool_result", "source_step_id": "tool_2", "output": '{"count":2,"results":[{},{}]}'},
                            {"artifact_type": "tool_result", "source_step_id": "tool_3", "output": '{"count":1,"results":[{}]}'},
                        ]
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content='Führe 3 Memory-Suchen aus: "Python", "Projekt", "Name".')],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == (
        "Die Antwort enthielt unzulässiges Tool-Markup und wurde verworfen. "
        "Bitte wiederhole die Anfrage."
    )


def test_generate_output_rejects_memory_tool_markup_without_recovery():
    async def fake_complete_output(output_request, chat_request, **kwargs):
        return type(
            "Result",
            (),
            {
                "content": '[TOOL_CALL]\n{tool => "memory_graph_search", args => { --query "billigobige" }}\n[/TOOL_CALL]',
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    plan = ThinkingPlan(
        intent="Memory nach billigobige durchsuchen",
        steps=[
            PlanStep("tool_1", "Use memory_graph_search", "Search billigobige", tool="memory_graph_search", tool_arguments={"query": "billigobige"}),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
    )

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text='Suche in deinen Memorys nach "billigobige" und gib mir den Inhalt.',
                thinking_plan=plan,
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "source_step_id": "tool_1",
                                "tool": "memory_graph_search",
                                "output": (
                                    '{"count":1,"results":[{"content":"billigobige ist als Teststichwort im Memory gespeichert.",'
                                    '"type":"fact","depth":0,"node_id":7}],"source":"graph_walk"}'
                                ),
                            }
                        ]
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content='Suche in deinen Memorys nach "billigobige" und gib mir den Inhalt.')],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == (
        "Die Antwort enthielt unzulässiges Tool-Markup und wurde verworfen. "
        "Bitte wiederhole die Anfrage."
    )
