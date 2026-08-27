from core.output.evidence_contracts import ClaimType, EvidenceClaim, GuardDecision
from core.pipeline.output_evidence_contracts import OutputEvidenceHandoff, OutputEvidenceState


def decide_guard(claim: EvidenceClaim, output_evidence: OutputEvidenceHandoff) -> GuardDecision:
    if not isinstance(claim, EvidenceClaim):
        raise TypeError("claim must be EvidenceClaim")
    if not isinstance(output_evidence, OutputEvidenceHandoff):
        raise TypeError("output_evidence must be OutputEvidenceHandoff")
    if claim.claim_type == ClaimType.CONCEPTUAL_ANALYSIS:
        return GuardDecision.ALLOW
    if output_evidence.state is OutputEvidenceState.COMPLETE_WITH_VALIDATED_EVIDENCE:
        return GuardDecision.LIMIT_TO_VERIFIED
    return GuardDecision.EXPLICIT_UNKNOWN
