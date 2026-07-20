import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest, OutputResult
from core.output.output import generate_output
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def _chat_request(text: str) -> CoreChatRequest:
    return CoreChatRequest(
        model="default",
        messages=[Message(role=MessageRole.USER, content=text)],
        conversation_id="execution-guard",
    )


def _result(content: str) -> OutputResult:
    return OutputResult(content=content, truncated=False, postcheck_applied=False)


def _complete_with(content: str):
    async def _complete(output_request, chat_request, **kwargs):
        return _result(content)

    return _complete


def test_direct_answer_smoke_text_is_not_replaced_without_task_loop_context():
    content = "Smoke test: ok."

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Antworte kurz: WebUI smoke ok.",
                thinking_plan=ThinkingPlan(
                    intent="answer_user",
                    steps=[
                        PlanStep(
                            step_id="answer_user",
                            title="Answer user",
                            goal="Generate a direct answer.",
                            tool=None,
                            risk=RiskLevel.SAFE,
                        )
                    ],
                    needs_task_loop=False,
                    risk_level=RiskLevel.SAFE,
                ),
                context={},
            ),
            _chat_request("Antworte kurz: WebUI smoke ok."),
            complete_output_fn=_complete_with(content),
        )
    )

    assert result.content == content


def test_execution_claim_without_evidence_still_blocks_in_task_loop_context():
    content = "Ich habe 5 Stichwoerter getestet. Ergebnisse: eins, zwei, drei."

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Pruef mal die Stichwortsuche.",
                thinking_plan=ThinkingPlan(
                    intent="answer_user",
                    steps=[
                        PlanStep(
                            step_id="tool_1",
                            title="Use memory search",
                            goal="Search memory.",
                            tool="memory_graph_search",
                            risk=RiskLevel.SAFE,
                        )
                    ],
                    needs_task_loop=True,
                    risk_level=RiskLevel.SAFE,
                ),
                context={"task_loop": {"artifacts": [], "snapshot": {"completed_steps": []}}},
            ),
            _chat_request("Pruef mal die Stichwortsuche."),
            complete_output_fn=_complete_with(content),
        )
    )

    assert "keine positiven Ausfuehrungsbelege" in result.content
