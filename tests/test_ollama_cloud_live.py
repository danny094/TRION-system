import asyncio

import pytest
import requests

from core.input_processor.contracts import DocumentContext
from core.llm_provider_client import complete_chat, complete_prompt
from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.stream import complete_output
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict
from core.verifier.input_prepare import build_verifier_input
from core.verifier.llm_check import run_llm_check
from tests.conftest import env_or_dotenv


def _require_ollama_cloud_live() -> dict[str, str]:
    pytest.importorskip("httpx")

    enabled = env_or_dotenv("TRION_ENABLE_OLLAMA_CLOUD_TESTS", "").lower()
    if enabled not in {"1", "true", "yes", "on"}:
        pytest.skip("Set TRION_ENABLE_OLLAMA_CLOUD_TESTS=1 to run live Ollama Cloud tests.")

    api_key = env_or_dotenv("OLLAMA_API_KEY", "") or env_or_dotenv("OLLAMA_CLOUD_API_KEY", "")
    if not api_key:
        pytest.skip("OLLAMA_API_KEY missing for live Ollama Cloud tests.")

    base = env_or_dotenv("OLLAMA_CLOUD_BASE", "https://ollama.com").rstrip("/")
    try:
        response = requests.get(
            f"{base}/api/tags",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        response.raise_for_status()
    except Exception as exc:
        pytest.skip(f"Ollama Cloud unavailable: {exc}")

    models = response.json().get("models", [])
    names = [str(item.get("name") or "").strip() for item in models if isinstance(item, dict)]
    names = [name for name in names if name]
    preferred = env_or_dotenv("TRION_OLLAMA_CLOUD_SMOKE_MODEL", "").strip()
    model = preferred if preferred in names else (names[0] if names else preferred)
    if not model:
        pytest.skip("No Ollama Cloud models visible for the configured API key.")
    return {"api_key": api_key, "base": base, "model": model}


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="answer_user",
        steps=[PlanStep(step_id="step-1", title="Antworten", goal="User kurz beantworten")],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="Kurz und direkt antworten.",
        plan_id="ollama-cloud-live-plan",
    )


def _document() -> DocumentContext:
    return DocumentContext(
        conversation_id="ollama-cloud-live",
        summary="Kurzes Testdokument mit Kapiteluebersicht.",
        key_facts=["Kapitel sind nummeriert"],
        total_chunks=2,
        workspace_entry_ids=[1, 2],
        preferred_entry_ids=[1],
        index_like_entry_ids=[1],
        chapter_candidate_entry_ids=[1],
        semantic_keys=["document_chunk_0"],
        semantic_candidate_keys=["document_chunk_0"],
        original_char_count=2048,
    )


def test_ollama_cloud_complete_chat_live():
    live = _require_ollama_cloud_live()

    result = asyncio.run(
        complete_chat(
            provider="ollama_cloud",
            model=live["model"],
            messages=[{"role": "user", "content": "Antworte nur mit: ok"}],
            timeout_s=45,
        )
    )

    assert isinstance(result, dict)
    assert isinstance(str(result.get("content") or ""), str)
    assert str(result.get("content") or "").strip()


def test_ollama_cloud_complete_output_live():
    live = _require_ollama_cloud_live()
    request = CoreChatRequest(
        model=live["model"],
        messages=[Message(role=MessageRole.USER, content="Antworte nur mit: output-ok")],
        conversation_id="ollama-cloud-output-live",
        raw_request={"provider": "ollama_cloud"},
    )
    output_request = OutputRequest(user_text="Antworte nur mit: output-ok", thinking_plan=_plan())

    result = asyncio.run(complete_output(output_request, request))

    assert isinstance(result.content, str)
    assert result.content.strip()


def test_ollama_cloud_verifier_llm_check_live(monkeypatch):
    live = _require_ollama_cloud_live()

    monkeypatch.setattr("core.verifier.llm_check.get_control_provider", lambda: "ollama_cloud")
    monkeypatch.setattr("core.verifier.llm_check.get_control_model", lambda: live["model"])
    monkeypatch.setattr("core.verifier.llm_check.get_control_model_deep", lambda: live["model"])
    monkeypatch.setattr("core.verifier.llm_check.get_control_timeout_interactive_s", lambda: 45)
    monkeypatch.setattr("core.verifier.llm_check.get_control_timeout_deep_s", lambda: 45)
    monkeypatch.setattr("core.verifier.llm_check.get_control_endpoint_override", lambda mode="interactive": "")

    verifier_input = build_verifier_input(
        "Wie viele Kapitel hat das Dokument?",
        _plan(),
        document_context=_document(),
    )

    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=complete_prompt, llm_enabled=True)

    assert result.verdict in {Verdict.APPROVED, Verdict.REJECTED, Verdict.HARD_BLOCK}
    assert isinstance(result.reason, str)
    assert "failed open" not in result.reason.lower()
