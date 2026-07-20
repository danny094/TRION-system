# Core Pipeline

Adapter-facing entry point for the TRION core flow.

## Target Path

```
CoreChatRequest
    ↓
classifier.classify()
    ↓
thinking.build_plan()
    ↓
verifier.verify_plan()
    ↓
output.generate_output()
    ↓
CoreChatResponse
```

Complex path:

```
CoreChatRequest
    ↓
pipeline.preprocess.preprocess_request()
    ↓
orchestrator_stage.build_orchestrator_stage()   # optional
    ↓
thinking.build_plan()
    ↓
verifier.verify_plan()
    ↓
task_loop_stage.build_task_loop_stage()         # optional
    ↓
output.generate_output()
    ↓
CoreChatResponse
```

## Files

| File | Responsibility |
|------|----------------|
| `runner.py` | Wire the pipeline stages and expose the adapter boundary |
| `grounding_stage.py` | Resolve/persist grounding state and inject it into the orchestrator context (Shadow Mode) |
| `task_loop_budget.py` | Bundle task-loop budget config getters; excludes `max_steps`/`max_retries_per_step`/`max_replans`, which stay inline in `runner.py` so existing tests can keep monkeypatching them directly |
| `runner_contracts.py` | Callable type aliases for the `run_chat()` signature |
| `preprocess.py` | Classifier + long-input preprocessing |
| `document_tools_stage.py` | Document-specific tool availability for Thinking |
| `orchestrator_stage.py` | Optional orchestrator stage and thinking-context packaging |
| `task_loop_stage.py` | Optional task-loop execution and output-context packaging |
| `thinking_stage.py` | Build-plan call compatibility and Thinking-stage packaging |
| `output_stage.py` | Rejected/approved response mapping and OutputRequest packaging |
| `common.py` | Shared pipeline serialization helpers |

## Current Vertical Slice

`runner.py` now implements both the simple path and the first staged complex path:

- Classifier returns `information/safe/direct_to_thinking`.
- Long-document inputs can be preprocessed into a compact `DocumentContext`.
- Document-specific tools such as `workspace_get` and `memory_semantic_search` can be injected for the document path.
- Document tool order can be refined by request intent before Thinking plans retrieval steps.
- Orchestrator context is passed into Thinking on the complex path.
- Verifier receives long-document-aware input preparation instead of only raw short-text assumptions.
- Verifier now runs deterministic safety first and can optionally run a control LLM check behind `CONTROL_LLM_CHECK_ENABLE`.
- Task Loop can be started and its result is forwarded to Output.
- Output request/response mapping is staged instead of living directly in the runner.
- Output calls the selected chat model through `core/output/stream.py`.

## Rules

- `runner.py` contains wiring only.
- Branching into preprocess, document tools, orchestrator, and task loop stays explicit.
- Thinking call compatibility and output mapping live in dedicated stage files.
- No LLM calls live in this package.
- No prompt text lives in this package.
