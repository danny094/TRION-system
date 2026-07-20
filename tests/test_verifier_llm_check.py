from core.input_processor.contracts import DocumentContext
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan
from core.verifier.contracts import Verdict
from core.verifier.input_prepare import build_verifier_input
from core.verifier.llm_check import run_llm_check
from core.verifier.prompts import build_verifier_prompt


def _plan() -> ThinkingPlan:
    return ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="step-1",
                title="Inspect chunk",
                goal="Read the uploaded chapter list.",
                tool="workspace_get",
                tool_arguments={"entry_id": 101},
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Read the relevant document chunks first.",
        plan_id="verify-plan-1",
    )


def _document() -> DocumentContext:
    return DocumentContext(
        conversation_id="conv-1",
        summary="Dokumentzusammenfassung fuer Planning: Kapiteluebersicht und Kapitelzaehlung.",
        key_facts=["Kapitel sind nummeriert"],
        total_chunks=4,
        workspace_entry_ids=[101, 102, 103, 104],
        preferred_entry_ids=[101, 102],
        index_like_entry_ids=[101],
        chapter_candidate_entry_ids=[101, 102],
        semantic_keys=["document_chunk_0", "document_chunk_1"],
        semantic_candidate_keys=["document_chunk_0"],
        original_char_count=12000,
    )


def test_build_verifier_prompt_uses_document_summary_not_raw_long_text():
    verifier_input = build_verifier_input("RAW " * 400, _plan(), document_context=_document())

    prompt = build_verifier_prompt(verifier_input, _plan())

    assert "VERIFY-INPUT" in prompt
    assert "Dokumentzusammenfassung fuer Planning" in prompt
    assert '"document_mode": "long_document"' in prompt
    assert '"document_retrieval_mode": "none"' in prompt
    assert '"document_retrieval": {' in prompt
    assert '"known_workspace_entry_ids": [' in prompt
    assert "RAW RAW RAW RAW" not in prompt


def test_build_verifier_prompt_includes_retrieval_mode_and_candidates():
    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[
            PlanStep(
                step_id="semantic_search_1",
                title="Search chunks",
                goal="Find the chapter list",
                tool="memory_semantic_search",
            ),
            PlanStep(
                step_id="workspace_101",
                title="Read chunk",
                goal="Read the chapter list",
                tool="workspace_get",
                tool_arguments={"entry_id": 101, "document_source_step": "semantic_search_1"},
            ),
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Search first, then read.",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="verify-plan-1",
    )

    verifier_input = build_verifier_input("Dokumentfrage", plan, document_context=_document())
    prompt = build_verifier_prompt(verifier_input, plan)

    assert '"retrieval_mode": "semantic_first"' in prompt
    assert '"question_focus": "semantic"' in prompt
    assert '"structure_required": false' in prompt
    assert '"known_workspace_entry_ids": [' in prompt
    assert '"preferred_entry_ids": [' in prompt
    assert '"chapter_candidate_entry_ids": [' in prompt
    assert '"retrieval_plan": {' in prompt
    assert '"search_step_ids": [' in prompt
    assert '"search_driven_workspace_reads": [' in prompt


def test_run_llm_check_returns_disabled_fallback_when_flag_is_off():
    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)

    result = run_llm_check(_plan(), verifier_input, llm_enabled=False)

    assert result.verdict == Verdict.APPROVED
    assert "disabled" in result.reason


def test_run_llm_check_stays_disabled_for_normal_input_when_only_long_document_gate_is_on(monkeypatch):
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_modes", lambda: ["off"])
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_enable", lambda: False)
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_long_document_enable", lambda: True)

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input)

    assert result.verdict == Verdict.APPROVED
    assert "disabled" in result.reason


def test_run_llm_check_uses_long_document_gate_when_global_flag_is_off(monkeypatch):
    seen = {}

    async def fake_complete_prompt(**kwargs):
        seen["prompt"] = kwargs.get("prompt")
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_modes", lambda: ["long_document"])
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_enable", lambda: False)
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_long_document_enable", lambda: True)

    verifier_input = build_verifier_input("Dokumentfrage", _plan(), document_context=_document())
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt)

    assert result.verdict == Verdict.APPROVED
    assert "prompt" in seen


def test_run_llm_check_uses_needs_confirmation_mode_for_risky_plan(monkeypatch):
    seen = {}

    async def fake_complete_prompt(**kwargs):
        seen["model"] = kwargs.get("model")
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    risky_plan = ThinkingPlan(
        intent="deploy_container",
        steps=[
            PlanStep(
                step_id="deploy",
                title="Deploy",
                goal="Run deployment",
                tool="deploy_container",
                risk=RiskLevel.NEEDS_CONFIRMATION,
            )
        ],
        needs_task_loop=True,
        risk_level=RiskLevel.NEEDS_CONFIRMATION,
        reasoning="Risky deploy.",
        plan_id="verify-plan-risky",
    )
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_modes", lambda: ["needs_confirmation"])

    verifier_input = build_verifier_input("Deploy app", risky_plan, document_context=None)
    result = run_llm_check(risky_plan, verifier_input, complete_prompt_fn=fake_complete_prompt)

    assert result.verdict == Verdict.APPROVED
    assert seen["model"] is not None


def test_run_llm_check_uses_task_loop_mode_for_multistep_plan(monkeypatch):
    seen = {}

    async def fake_complete_prompt(**kwargs):
        seen["timeout_s"] = kwargs.get("timeout_s")
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    task_plan = ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Inspect", goal="Inspect", tool="workspace_get")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Multi-step execution.",
        plan_id="verify-plan-loop",
    )
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_modes", lambda: ["task_loop"])

    verifier_input = build_verifier_input("Run tools", task_plan, document_context=None)
    result = run_llm_check(task_plan, verifier_input, complete_prompt_fn=fake_complete_prompt)

    assert result.verdict == Verdict.APPROVED
    assert seen["timeout_s"] is not None


def test_run_llm_check_extra_modes_can_enable_task_loop_when_config_is_off(monkeypatch):
    seen = {}

    async def fake_complete_prompt(**kwargs):
        seen["called"] = True
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    task_plan = ThinkingPlan(
        intent="run_tools",
        steps=[PlanStep(step_id="s1", title="Inspect", goal="Inspect", tool="workspace_get")],
        needs_task_loop=True,
        risk_level=RiskLevel.SAFE,
        reasoning="Multi-step execution.",
        plan_id="verify-plan-loop-extra-mode",
    )
    monkeypatch.setattr("core.verifier.llm_check.get_control_llm_check_modes", lambda: ["off"])

    verifier_input = build_verifier_input("Run tools", task_plan, document_context=None)
    result = run_llm_check(
        task_plan,
        verifier_input,
        complete_prompt_fn=fake_complete_prompt,
        extra_modes={"task_loop"},
    )

    assert result.verdict == Verdict.APPROVED
    assert seen["called"] is True


def test_run_llm_check_maps_rejection_payload_to_verifier_result():
    async def fake_complete_prompt(**kwargs):
        return """
        {"approved": false, "hard_block": false, "warnings": ["missing validation"], "final_instruction": "Fuege erst eine Validierung ein."}
        """

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.REJECTED
    assert result.hint == "Fuege erst eine Validierung ein."
    assert result.warnings == ["missing validation"]


def test_run_llm_check_drops_structure_drift_for_semantic_focus():
    async def fake_complete_prompt(**kwargs):
        return """
        {
          "approved": true,
          "hard_block": false,
          "warnings": [
            "Der Plan kritisiert Kapitelanzahl relevant waere, falls der User nach Struktur statt Inhalt fragt.",
            "{'type': 'semantic_focus', 'message': 'Der Plan konzentriert sich primär auf die Abdeckung der chapter_candidate_entry_ids, was zwar die Strukturabdeckung sicherstellt, aber die semantische Abdeckung nicht direkt erfasst.', 'suggestion': 'Nutze semantic_keys als primäre Quelle.'}"
          ],
          "final_instruction": "ok"
        }
        """

    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="",
        context_hints={"document_retrieval_mode": "semantic_first"},
        plan_id="verify-plan-semantic",
    )
    verifier_input = build_verifier_input("Was passiert in PREGO!?", plan, document_context=_document())

    result = run_llm_check(plan, verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.APPROVED
    assert len(result.warnings) == 1
    assert "Navigation unterstuetzt" in result.warnings[0]


def test_run_llm_check_drops_semantic_drift_for_structure_focus():
    async def fake_complete_prompt(**kwargs):
        return """
        {
          "approved": true,
          "hard_block": false,
          "warnings": [
            "Der Plan priorisiert semantische Inhaltsfragen, obwohl die Kapitelanzahl geprüft werden soll."
          ],
          "final_instruction": "ok"
        }
        """

    plan = ThinkingPlan(
        intent="inspect_document",
        steps=[],
        needs_task_loop=False,
        risk_level=RiskLevel.SAFE,
        reasoning="",
        context_hints={"document_retrieval_mode": "structure_first"},
        plan_id="verify-plan-structure",
    )
    verifier_input = build_verifier_input("Wie viele Kapitel hat diese Geschichte?", plan, document_context=_document())

    result = run_llm_check(plan, verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.APPROVED
    assert result.warnings == []


def test_run_llm_check_maps_hard_block_payload_to_verifier_result():
    async def fake_complete_prompt(**kwargs):
        return """
        {"approved": false, "hard_block": true, "block_reason_code": "malicious_intent", "warnings": []}
        """

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.HARD_BLOCK
    assert result.reason == "malicious_intent"


def test_run_llm_check_rejects_invalid_json_instead_of_failing_open():
    async def fake_complete_prompt(**kwargs):
        return "approved: yes"

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.REJECTED
    assert result.reason == "control_llm_invalid_json"
    assert "control_llm_invalid_json" in result.warnings


def test_run_llm_check_rejects_payload_without_explicit_decision():
    async def fake_complete_prompt(**kwargs):
        return '{"final_instruction": "ok", "warnings": []}'

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.REJECTED
    assert result.reason == "control_llm_invalid_decision"
    assert "eindeutiges approved/hard_block" in str(result.hint or "")


def test_run_llm_check_rejects_conflicting_payload():
    async def fake_complete_prompt(**kwargs):
        return '{"approved": true, "hard_block": true, "final_instruction": "conflict"}'

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.REJECTED
    assert result.reason == "control_llm_conflicting_decision"


def test_run_llm_check_uses_ollama_base_when_no_override(monkeypatch):
    seen = {}

    async def fake_complete_prompt(**kwargs):
        seen["ollama_endpoint"] = kwargs.get("ollama_endpoint")
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    monkeypatch.setattr("core.verifier.llm_check.get_control_provider", lambda: "ollama")
    monkeypatch.setattr("core.verifier.llm_check.get_control_model", lambda: "ministral-3:8b")
    monkeypatch.setattr("core.verifier.llm_check.get_control_timeout_interactive_s", lambda: 30)
    monkeypatch.setattr("core.verifier.llm_check.get_control_endpoint_override", lambda mode="interactive": "")
    monkeypatch.setattr("core.verifier.llm_check.OLLAMA_BASE", "http://127.0.0.1:11434")

    verifier_input = build_verifier_input("Hallo", _plan(), document_context=None)
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.APPROVED
    assert seen["ollama_endpoint"] == "http://127.0.0.1:11434"


def test_run_llm_check_uses_deep_timeout_model_and_endpoint_for_long_document(monkeypatch):
    seen = {}

    async def fake_complete_prompt(**kwargs):
        seen["model"] = kwargs.get("model")
        seen["timeout_s"] = kwargs.get("timeout_s")
        seen["ollama_endpoint"] = kwargs.get("ollama_endpoint")
        return '{"approved": true, "hard_block": false, "warnings": [], "final_instruction": "ok"}'

    monkeypatch.setattr("core.verifier.llm_check.get_control_provider", lambda: "ollama")
    monkeypatch.setattr("core.verifier.llm_check.get_control_model", lambda: "ministral-3:8b")
    monkeypatch.setattr("core.verifier.llm_check.get_control_model_deep", lambda: "ministral-3:14b")
    monkeypatch.setattr("core.verifier.llm_check.get_control_timeout_interactive_s", lambda: 30)
    monkeypatch.setattr("core.verifier.llm_check.get_control_timeout_deep_s", lambda: 60)
    monkeypatch.setattr("core.verifier.llm_check.get_control_endpoint_override", lambda mode="interactive": "http://127.0.0.1:22434" if mode == "deep" else "")
    monkeypatch.setattr("core.verifier.llm_check.OLLAMA_BASE", "http://127.0.0.1:11434")

    verifier_input = build_verifier_input("Dokumentfrage", _plan(), document_context=_document())
    result = run_llm_check(_plan(), verifier_input, complete_prompt_fn=fake_complete_prompt, llm_enabled=True)

    assert result.verdict == Verdict.APPROVED
    assert seen["model"] == "ministral-3:14b"
    assert seen["timeout_s"] == 60
    assert seen["ollama_endpoint"] == "http://127.0.0.1:22434"
