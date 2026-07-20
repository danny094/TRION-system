from core.task_loop.contracts import EvidenceArtifact


def test_from_dict_reads_flat_metadata():
    artifact = EvidenceArtifact.from_dict(
        {
            "source_step_id": "s1",
            "artifact_type": "runtime_status",
            "content": "ok",
            "metadata": {"validated_evidence": True},
        }
    )

    assert artifact.step_id == "s1"
    assert artifact.artifact_type == "runtime_status"
    assert artifact.content == "ok"
    assert artifact.metadata["validated_evidence"] is True


def test_from_dict_reads_legacy_nested_metadata_as_flat():
    artifact = EvidenceArtifact.from_dict(
        {
            "source_step_id": "s1",
            "artifact_type": "runtime_status",
            "metadata": {"metadata": {"validated_evidence": True}},
        }
    )

    assert artifact.metadata == {"validated_evidence": True}


def test_from_dict_prefers_flat_metadata_when_nested_also_exists():
    artifact = EvidenceArtifact.from_dict(
        {
            "source_step_id": "s1",
            "artifact_type": "runtime_status",
            "metadata": {
                "validated_evidence": False,
                "metadata": {"validated_evidence": True},
            },
        }
    )

    assert artifact.metadata == {"validated_evidence": False}


def test_from_dict_without_metadata_is_stable_empty():
    artifact = EvidenceArtifact.from_dict(
        {
            "source_step_id": "s1",
            "artifact_type": "runtime_status",
        }
    )

    assert artifact.metadata == {}
