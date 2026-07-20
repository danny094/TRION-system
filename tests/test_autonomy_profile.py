import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "adapters" / "admin-api" / "autonomy_profile_routes.py"
SPEC = importlib.util.spec_from_file_location("autonomy_profile_routes", MODULE_PATH)
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


def test_autonomy_profile_defaults(monkeypatch):
    monkeypatch.setattr(module, "settings", _StubSettings())

    profile = module._effective_profile()

    assert profile == {
        "mode": "halbautomatisch",
        "planning_depth": "normal",
        "wait_behavior": "30sek",
        "safety_level": "standard",
        "error_behavior": "retry",
        "loop_detection_enabled": True,
        "loop_detection_sensitivity": 3,
    }


def test_autonomy_profile_reads_overrides(monkeypatch):
    stub = _StubSettings()
    stub.set("AUTONOMY_PROFILE_MODE", "autonom")
    stub.set("AUTONOMY_PROFILE_PLANNING_DEPTH", "gründlich")
    stub.set("AUTONOMY_PROFILE_LOOP_DETECTION_ENABLED", False)
    stub.set("AUTONOMY_PROFILE_LOOP_DETECTION_SENSITIVITY", 10)
    monkeypatch.setattr(module, "settings", stub)

    profile = module._effective_profile()
    sources = module._effective_sources()

    assert profile["mode"] == "autonom"
    assert profile["planning_depth"] == "gründlich"
    assert profile["loop_detection_enabled"] is False
    assert profile["loop_detection_sensitivity"] == 10
    assert sources["mode"] == "override"
    assert sources["planning_depth"] == "override"


def test_autonomy_profile_reads_env_when_no_persisted_override(monkeypatch):
    stub = _StubSettings()
    monkeypatch.setattr(module, "settings", stub)
    monkeypatch.setenv("AUTONOMY_PROFILE_MODE", "autonom")
    monkeypatch.setenv("AUTONOMY_PROFILE_WAIT_BEHAVIOR", "2min")

    profile = module._effective_profile()
    sources = module._effective_sources()

    assert profile["mode"] == "autonom"
    assert profile["wait_behavior"] == "2min"
    assert sources["mode"] == "env"
    assert sources["wait_behavior"] == "env"


def test_autonomy_profile_invalid_values_fall_back_to_defaults(monkeypatch):
    stub = _StubSettings()
    stub.set("AUTONOMY_PROFILE_MODE", "kaputt")
    stub.set("AUTONOMY_PROFILE_LOOP_DETECTION_SENSITIVITY", 999)
    monkeypatch.setattr(module, "settings", stub)

    profile = module._effective_profile()

    assert profile["mode"] == "halbautomatisch"
    assert profile["loop_detection_sensitivity"] == 3


def test_autonomy_profile_builds_runtime_overrides():
    overrides = module.build_runtime_overrides(
        {
            "mode": "autonom",
            "planning_depth": "gründlich",
            "wait_behavior": "2min",
            "safety_level": "erhöht",
            "error_behavior": "ask",
            "loop_detection_enabled": True,
            "loop_detection_sensitivity": 5,
        }
    )

    assert overrides["TASK_LOOP_MAX_STEPS"] == 25
    assert overrides["LOOP_ENGINE_MAX_PREDICT"] == 1400
    assert overrides["SEQUENTIAL_TIMEOUT_S"] == 120
    assert overrides["QUERY_BUDGET_SKIP_THINKING_ENABLE"] is False
    assert overrides["QUERY_BUDGET_MAX_TOOLS_FACTUAL_LOW"] == 0
    assert overrides["TASK_LOOP_MAX_RETRIES_PER_STEP"] == 0
    assert overrides["TASK_LOOP_FAILURE_ESCALATION"] == "ask"
    assert overrides["QUERY_BUDGET_ENABLE"] is True
    assert overrides["TASK_LOOP_LOOP_DETECTION_ENABLE"] is True
    assert overrides["TASK_LOOP_NO_PROGRESS_THRESHOLD"] == 5
    assert overrides["TASK_LOOP_APPROVAL_MODE"] == "permissive"
