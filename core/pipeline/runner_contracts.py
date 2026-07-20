"""Callable-Typaliase fuer core/pipeline/runner.py.

Reine Typdefinitionen, keine Logik, kein LLM-Call. Bewusst lokal zu
run_chat() gehalten (Parameter-Defaults/Signatur) — NICHT konsolidiert mit
gleichnamigen Aliasen in core/pipeline/orchestrator_stage.py,
core/pipeline/task_loop_stage.py, core/output/stream.py und
core/input_processor/storage.py. Diese Konsolidierung waere eine eigene
Entscheidung (Doc36 Regel 1) und ist nicht Teil dieses verhaltensneutralen
Datei-Splits (P11 SP0).
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Optional

from core.task_loop.executor import TaskToolCall, TaskToolResult

OutputFn = Callable[..., Awaitable[Any]]
TaskLoopFn = Callable[..., Any]
ToolRunner = Callable[[TaskToolCall], TaskToolResult]
OrchestratorFn = Callable[..., Any]
WorkspaceSaveFn = Callable[[str, str, str, str], int]
SemanticSaveFn = Callable[[str, str, str, Optional[str], Optional[str]], object]
TaskLoopObserver = Callable[..., None]
TaskEventSink = Callable[[Dict[str, Any]], None]
ChunkSink = Callable[[str], None]
