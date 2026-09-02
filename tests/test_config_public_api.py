from importlib import import_module

import config


DOMAIN_NAMES = (
    "infra",
    "models",
    "pipeline",
    "output",
    "autonomy",
    "context",
    "features",
    "digest",
    "skills",
)
ROOT_ONLY_OWNERS = {
    "get_custom_mcps_dir": "config.infra.paths",
    "get_grounding_state_ttl_turns": "config.pipeline.grounding",
    "get_grounding_state_ttl_s": "config.pipeline.grounding",
}


def _domain_exports() -> dict[str, object]:
    exports: dict[str, object] = {}
    for domain_name in DOMAIN_NAMES:
        domain = import_module(f"config.{domain_name}")
        for export_name in domain.__all__:
            assert export_name not in exports
            exports[export_name] = getattr(domain, export_name)
    return exports


def test_root_config_preserves_domain_api_identity() -> None:
    expected = _domain_exports()
    for export_name, owner_name in ROOT_ONLY_OWNERS.items():
        owner = import_module(owner_name)
        expected[export_name] = getattr(owner, export_name)

    assert len(expected) == 249
    for export_name, expected_object in expected.items():
        assert getattr(config, export_name) is expected_object


def test_legacy_no_evidence_fallback_config_is_removed() -> None:
    assert not hasattr(config, "get_grounding_no_evidence_fallback_mode")
    assert not hasattr(
        import_module("config.pipeline"),
        "get_grounding_no_evidence_fallback_mode",
    )
    assert not hasattr(
        import_module("config.pipeline.grounding"),
        "get_grounding_no_evidence_fallback_mode",
    )
