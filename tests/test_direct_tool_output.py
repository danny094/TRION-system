import asyncio

from core.models import CoreChatRequest, Message, MessageRole
from core.output.contracts import OutputRequest
from core.output.direct_tool_output import render_direct_tool_output
from core.output.output import generate_output
from core.thinking.contracts import PlanStep, RiskLevel, ThinkingPlan


def test_render_direct_tool_output_formats_single_tool_result_artifact():
    content = render_direct_tool_output(
        OutputRequest(
            user_text="Wie viel Uhr ist es?",
            thinking_plan=None,
            context={
                "task_loop": {
                    "artifacts": [
                        {
                            "artifact_type": "tool_result",
                            "tool": "time_now",
                            "result": '{"utc_iso":"2026-05-12T13:58:28Z","time":"13:58:28"}',
                        }
                    ]
                }
            },
        )
    )

    assert content == "Es ist 13:58:28."


def test_render_direct_tool_output_formats_container_list_naturally():
    content = render_direct_tool_output(
        OutputRequest(
            user_text="Welche Container laufen gerade?",
            thinking_plan=None,
            context={
                "task_loop": {
                    "artifacts": [
                        {
                            "artifact_type": "tool_result",
                            "tool": "container_list",
                            "result": '{"containers":[{"name":"trion-webui","status":"running","image":"trion-webui:latest"},{"name":"trion-memory","status":"running","image":"trion-memory:latest"}]}',
                        }
                    ]
                }
            },
        )
    )

    assert content == "Aktuell laufen 2 Container: trion-webui und trion-memory."


def test_render_direct_tool_output_formats_memory_graph_search_naturally():
    content = render_direct_tool_output(
        OutputRequest(
            user_text="Suche in deinen Memorys nach billigobige.",
            thinking_plan=None,
            context={
                "task_loop": {
                    "artifacts": [
                        {
                            "artifact_type": "tool_result",
                            "tool": "memory_graph_search",
                            "result": (
                                '{"count":1,"results":[{"content":"billigobige ist als Teststichwort im Memory gespeichert.",'
                                '"type":"fact","depth":0,"node_id":7}],"source":"graph_walk"}'
                            ),
                        }
                    ]
                }
            },
        )
    )

    assert content == (
        "Ich habe 1 passenden Memory-Treffer gefunden.\n"
        "- Fact: billigobige ist als Teststichwort im Memory gespeichert."
    )


def test_render_direct_tool_output_formats_memory_graph_search_with_zero_hits():
    content = render_direct_tool_output(
        OutputRequest(
            user_text="Suche in deinen Memorys nach foobarbaz.",
            thinking_plan=None,
            context={
                "task_loop": {
                    "artifacts": [
                        {
                            "artifact_type": "tool_result",
                            "tool": "memory_graph_search",
                            "result": '{"count":0,"results":[],"source":"graph_walk"}',
                        }
                    ]
                }
            },
        )
    )

    assert content == "Ich habe keinen passenden Memory-Treffer gefunden."


def test_generate_output_keeps_llm_path_when_grounded_tool_output_is_available():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Es ist 13:58:28 UTC.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel Uhr ist es?",
                thinking_plan=None,
                context={
                    "grounded_tool_results": [
                        {
                            "tool_name": "time_now",
                            "step_id": "tool_1",
                            "facts": {"utc_iso": "2026-05-12T13:58:28Z"},
                        }
                    ],
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "time_now",
                                "result": '{"utc_iso":"2026-05-12T13:58:28Z"}',
                            }
                        ]
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie viel Uhr ist es?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Es ist 13:58:28 UTC."


def test_generate_output_does_not_short_circuit_when_task_loop_is_not_complete():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Verifizierte Home-Metadaten.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.",
                thinking_plan=None,
                context={
                    "grounded_tool_results": [
                        {
                            "tool_name": "container_inspect",
                            "step_id": "tool_1",
                            "facts": {"home_scope": {"is_home": True, "home_root": "/home/trion"}},
                        }
                    ],
                    "task_loop": {
                        "completion_status": "needs_more_evidence",
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": '{"home_scope":{"is_home":true,"home_root":"/home/trion"}}',
                            }
                        ],
                    },
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Verifizierte Home-Metadaten."


def test_generate_output_keeps_llm_path_for_completed_container_inspect_result():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Der Container ist als verifiziertes Home markiert.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.",
                thinking_plan=None,
                context={
                    "grounded_tool_results": [
                        {
                            "tool_name": "container_inspect",
                            "step_id": "tool_1",
                            "facts": {"home_scope": {"is_home": True, "home_root": "/home/trion"}},
                        }
                    ],
                    "task_loop": {
                        "completion_status": "complete",
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": '{"home_scope":{"is_home":true,"home_root":"/home/trion"}}',
                            }
                        ],
                    },
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe den Container trion-home und zeige mir nur verifizierte Home-Metadaten.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Der Container ist als verifiziertes Home markiert."


def test_generate_output_keeps_llm_path_for_multiple_grounded_results():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Zusammenfassung.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Fasse beide Ergebnisse zusammen.",
                thinking_plan=None,
                context={
                    "grounded_tool_results": [
                        {"tool_name": "time_now", "step_id": "tool_1", "facts": {"time": "13:58:28"}},
                        {"tool_name": "home_read", "step_id": "tool_2", "facts": {"value": "Systemstatus: OK"}},
                    ]
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Fasse beide Ergebnisse zusammen.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Zusammenfassung."


def test_generate_output_does_not_use_multi_tool_direct_fallback_when_llm_returns_empty():
    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe Uhrzeit und Container.",
                thinking_plan=None,
                context={
                    "grounded_tool_results": [
                        {"tool_name": "time_now", "step_id": "tool_1", "facts": {"time": "13:58:28", "timezone": "UTC"}},
                        {
                            "tool_name": "container_list",
                            "step_id": "tool_2",
                            "facts": {"containers": [{"name": "trion-webui", "status": "running"}]},
                        },
                    ],
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe Uhrzeit und Container.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == ""


def test_generate_output_allows_verified_home_scope_capability_answer_without_tool_result():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type(
            "Result",
            (),
            {
                "content": "Ich kann den Container inspizieren und seinen Laufzeitstatus lesen, aber aktuell weder Dateien schreiben noch Befehle darin ausführen.",
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Was kannst du in dem Container alles machen?",
                thinking_plan=None,
                context={
                    "orchestrator": {
                        "context": {
                            "home_context": {
                                "verified": True,
                                "container_name": "trion-home",
                                "available_capability_classes": ["container_inspect", "container_inventory"],
                                "missing_capability_classes": ["file_write", "local_exec"],
                            }
                        }
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Was kannst du in dem Container alles machen?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert "Ich kann den Container inspizieren" in result.content


def test_generate_output_allows_system_capability_answer_from_verified_self_context():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type(
            "Result",
            (),
            {
                "content": "Ich kann aktuell kuratierten Memory-Kontext lesen, Container inspizieren und Logs lesen. Globales Langzeit-Schreiben ist in diesem Kontext deaktiviert.",
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Was kannst du gerade insgesamt im System tun?",
                thinking_plan=None,
                context={
                    "orchestrator": {
                        "context": {
                            "self_context": {
                                "identity": {
                                    "name": "TRION",
                                    "status": "verified",
                                },
                                "capabilities": [
                                    {"name": "memory_read", "status": "verified", "source": "conversation_policy"},
                                    {"name": "container_inspect", "status": "verified", "source": "home_context"},
                                ],
                                "memory_visibility": {
                                    "memory_mode": "conversation_only",
                                    "allow_long_term_write": False,
                                },
                            }
                        }
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Was kannst du gerade insgesamt im System tun?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert "Memory-Kontext lesen" in result.content


def test_generate_output_blocks_positive_execution_claims_without_execution_evidence():
    async def fake_complete_output(output_request, chat_request, **kwargs):
        return type(
            "Result",
            (),
            {
                "content": 'Ich habe 5 Stichwoerter getestet. Ergebnisse: 1. "Name" 2. "Deutsch" 3. "Interesse" 4. "Hobby" 5. "Arbeit".',
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Pruef mal die Stichwortsuche 5x.",
                thinking_plan=None,
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Pruef mal die Stichwortsuche 5x.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert "keine positiven Ausfuehrungsbelege" in result.content


def test_generate_output_allows_honest_non_execution_message_without_step_evidence():
    async def fake_complete_output(output_request, chat_request, **kwargs):
        return type(
            "Result",
            (),
            {
                "content": "Ich konnte die Stichwortsuche nicht ausfuehren, weil mir dafuer aktuell kein passendes Tool vorliegt.",
                "truncated": False,
                "postcheck_applied": False,
            },
        )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Pruef mal die Stichwortsuche.",
                thinking_plan=None,
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Pruef mal die Stichwortsuche.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert "kein passendes Tool" in result.content


def test_generate_output_keeps_llm_path_with_fresh_grounding_state_when_current_turn_has_no_grounded_results():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Freier Text.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel Uhr ist es?",
                thinking_plan=None,
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 5.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T13:58:28Z"}}
                        ],
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie viel Uhr ist es?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "Freier Text."


def test_generate_output_does_not_reuse_unrelated_grounding_state_for_new_prompt():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "Antwort über eine Datei.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Lies die Datei /trion-home/status.txt. Nutze dafür nur ein Datei-Lese-Tool.",
                thinking_plan=None,
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 5.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T13:58:28Z"}}
                        ],
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Lies die Datei /trion-home/status.txt.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert "Ergebnis von `time_now`:" not in result.content


def test_generate_output_keeps_llm_path_for_time_followup_with_grounding_state():
    seen = {"called": False}

    async def fake_complete_output(output_request, chat_request, **kwargs):
        seen["called"] = True
        return type("Result", (), {"content": "In einer Stunde ist es 04:26:51 UTC.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Und in einer Stunde?",
                thinking_plan=None,
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 5.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T03:26:51Z"}}
                        ],
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Und in einer Stunde?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert seen["called"] is True
    assert result.content == "In einer Stunde ist es 04:26:51 UTC."


def test_generate_output_downgrades_to_unknown_when_artifacts_exist_without_grounded_evidence(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Die VRAM-Nutzung beträgt 75%.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Prüfe den Status.",
                thinking_plan=None,
                context={
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": "placeholder text without structured evidence",
                            }
                        ]
                    }
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Prüfe den Status.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_generate_output_downgrades_to_unknown_when_carryover_is_unrelated(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Erfundene Dateiausgabe.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Lies die Datei /trion-home/status.txt.",
                thinking_plan=None,
                context={
                    "grounding_state": {
                        "updated_at": 100.0,
                        "age_s": 2.0,
                        "age_turns": 0,
                        "grounded_results": [
                            {"tool_name": "time_now", "step_id": "tool_1", "facts": {"utc_iso": "2026-05-12T13:58:28Z"}}
                        ],
                    },
                    "task_loop": {
                        "artifacts": [
                            {
                                "artifact_type": "tool_result",
                                "tool": "container_inspect",
                                "result": "placeholder text without structured evidence",
                            }
                        ]
                    },
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Lies die Datei /trion-home/status.txt.")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_generate_output_downgrades_runtime_hardware_claim_without_hardware_evidence(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "RAM: 12 GB, VRAM: 16 GB.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel RAM oder VRAM hast du gerade?",
                thinking_plan=None,
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie viel RAM oder VRAM hast du gerade?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Unbekannt. Es liegen keine verifizierten Tool-Fakten vor."


def test_generate_output_keeps_conceptual_analysis_without_runtime_evidence(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Ich würde das als typisierte Evidence-Firewall im Core bauen.", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie würdest du einen Anti-Halluzinationsguard architektonisch aufbauen?",
                thinking_plan=None,
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie würdest du einen Anti-Halluzinationsguard architektonisch aufbauen?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Ich würde das als typisierte Evidence-Firewall im Core bauen."


def test_generate_output_keeps_reflective_container_question_when_dialogue_act_is_smalltalk(monkeypatch):
    monkeypatch.setenv("GROUNDING_NO_EVIDENCE_FALLBACK_MODE", "explicit_unknown")

    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "Als Design finde ich einen verifizierten Home-Scope sinnvoll, weil er Grenzen und Capabilities klar macht.", "truncated": False, "postcheck_applied": False})()

    thinking_plan = type(
        "Plan",
        (),
        {"context_hints": {"dialogue_act": "smalltalk"}},
    )()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie ist es für dich, dass wir dir einen Container als Zuhause erstellt haben?",
                thinking_plan=thinking_plan,
                context={},
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie ist es für dich, dass wir dir einen Container als Zuhause erstellt haben?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == "Als Design finde ich einen verifizierten Home-Scope sinnvoll, weil er Grenzen und Capabilities klar macht."


def test_generate_output_keeps_empty_result_when_llm_returns_empty_and_no_guard_applies():
    async def fake_complete_output(*args, **kwargs):
        return type("Result", (), {"content": "", "truncated": False, "postcheck_applied": False})()

    result = asyncio.run(
        generate_output(
            OutputRequest(
                user_text="Wie viel Uhr ist es?",
                thinking_plan=None,
                context={
                    "grounded_tool_results": [
                        {
                            "tool_name": "time_now",
                            "step_id": "tool_1",
                            "facts": {"utc_iso": "2026-05-12T13:58:28Z"},
                        }
                    ]
                },
            ),
            CoreChatRequest(
                model="default",
                messages=[Message(role=MessageRole.USER, content="Wie viel Uhr ist es?")],
                conversation_id="test",
            ),
            complete_output_fn=fake_complete_output,
        )
    )

    assert result.content == ""


def test_generate_output_replaces_pseudo_tool_markup_with_task_loop_summary():
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

    assert result.content == '**Ausgeführte Suchen:**\n- "Python" -> 0 Treffer\n- "Projekt" -> 2 Treffer\n- "Name" -> 1 Treffer'


def test_generate_output_replaces_memory_tool_markup_with_grounded_single_search_result():
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
        "Ich habe 1 passenden Memory-Treffer gefunden.\n"
        "- Fact: billigobige ist als Teststichwort im Memory gespeichert."
    )
