import asyncio
import inspect

import pytest

from core.output import execution_consistency_guard as execution_guard_module
from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest, OutputResult
from core.output.output import generate_output
from core.output.stream import _stream_output, complete_output
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceItem, OutputEvidenceState
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
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            _chat_request("Antworte kurz: WebUI smoke ok."),
            complete_output_fn=_complete_with(content),
        )
    )

    assert result.content == content


def test_execution_claim_without_validated_evidence_still_blocks():
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
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
            ),
            _chat_request("Pruef mal die Stichwortsuche."),
            complete_output_fn=_complete_with(content),
        )
    )

    assert "keine positiven Ausfuehrungsbelege" in result.content


@pytest.mark.parametrize(
    ("source_chunks", "expected_sink"),
    [
        (["Ich habe 5 Stichwoerter getestet. Ergebnisse: eins, zwei, drei."], []),
        (["Ich habe 5 Stichwoerter ", "getestet. Ergebnisse: eins, zwei, drei."], []),
    ],
)
def test_execution_claim_without_evidence_never_reaches_stream_sink(source_chunks, expected_sink):
    content = "".join(source_chunks)
    streamed_chunks: list[str] = []

    async def fake_stream(**_kwargs):
        for chunk in source_chunks:
            yield chunk

    async def streaming_complete(output_request, chat_request, **kwargs):
        return await complete_output(
            output_request,
            chat_request,
            chunk_sink=kwargs["chunk_sink"],
            stream_chat_fn=fake_stream,
        )

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Antworte kurz: WebUI smoke ok.",
                thinking_plan=ThinkingPlan(
                    intent="answer_user",
                    steps=[],
                    needs_task_loop=False,
                    risk_level=RiskLevel.SAFE,
                ),
                output_evidence=OutputEvidenceHandoff(OutputEvidenceState.NO_TASK_LOOP),
                context={},
                stream=True,
            ),
            _chat_request("Antworte kurz: WebUI smoke ok."),
            complete_output_fn=streaming_complete,
            chunk_sink=streamed_chunks.append,
        )
    )

    assert "keine positiven Ausfuehrungsbelege" in result.content
    assert streamed_chunks == expected_sink


def test_stream_execution_guard_has_bounded_signature():
    assert len(inspect.signature(_stream_output).parameters) <= 5


def test_stream_execution_guard_has_single_subject_source():
    source = inspect.getsource(execution_guard_module)
    assert source.count("ich habe") == 1
    assert source.count("wir haben") == 1


def test_execution_claim_with_validated_evidence_allows_only_attested_completion():
    content = "Ich habe die Uhrzeit geprueft. Ergebnisse: 12:00 UTC."
    request = OutputRequest(
        user_text="Wie viel Uhr ist es?",
        thinking_plan=None,
        output_evidence=OutputEvidenceHandoff(
            OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE,
            (OutputEvidenceItem({"ok": True}),),
        ),
        context={},
    )

    result = asyncio.run(
        generate_output(request, _chat_request(request.user_text), complete_output_fn=_complete_with(content))
    )

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."
