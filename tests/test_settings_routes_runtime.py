import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "adapters" / "admin-api" / "settings_routes.py"
SPEC = importlib.util.spec_from_file_location("settings_routes", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(module)


class _StubSettings:
    def __init__(self):
        self.settings = {}

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value


def test_sequential_runtime_effective_includes_output_evidence_controls(monkeypatch):
    stub = _StubSettings()
    monkeypatch.setattr(module, "settings", stub)

    result = module.get_sequential_runtime_policy.__wrapped__() if hasattr(module.get_sequential_runtime_policy, "__wrapped__") else None
    if result is None:
        import asyncio
        result = asyncio.run(module.get_sequential_runtime_policy())

    effective = result["effective"]
    assert "QUERY_BUDGET_MAX_TOOLS_FACTUAL_LOW" in effective
    assert "OUTPUT_MULTI_TOOL_SYNTHESIS_ENABLE" in effective
    assert "OUTPUT_RENDERABLE_EVIDENCE_MAX_ITEMS" in effective
    assert "OUTPUT_RENDERABLE_EVIDENCE_MAX_BULLETS_PER_ITEM" in effective


def test_sequential_runtime_update_accepts_output_evidence_controls(monkeypatch):
    stub = _StubSettings()
    monkeypatch.setattr(module, "settings", stub)

    update = module.SequentialRuntimeUpdate(
        OUTPUT_MULTI_TOOL_SYNTHESIS_ENABLE=False,
        OUTPUT_RENDERABLE_EVIDENCE_MAX_ITEMS=6,
        OUTPUT_RENDERABLE_EVIDENCE_MAX_BULLETS_PER_ITEM=2,
    )

    import asyncio
    result = asyncio.run(module.update_sequential_runtime_policy(update))

    assert result["saved"]["OUTPUT_MULTI_TOOL_SYNTHESIS_ENABLE"] is False
    assert result["saved"]["OUTPUT_RENDERABLE_EVIDENCE_MAX_ITEMS"] == 6
    assert result["saved"]["OUTPUT_RENDERABLE_EVIDENCE_MAX_BULLETS_PER_ITEM"] == 2
