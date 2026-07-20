"""Fail-closed public projections for P11 pipeline decisions."""

from typing import Any

from core.classifier.contracts import Category, ClassifierResult, Route, SafetyLevel
from core.verifier.contracts import Verdict, VerifierResult


PLAN_CONTRACT_ERROR_CODE = "plan_contract_rejected"
PLAN_CONTRACT_MESSAGE = "Der Plan konnte nicht freigegeben werden."
REJECTION_ERROR_CODE = "request_rejected"
REJECTION_MESSAGE = "Die Anfrage konnte nicht freigegeben werden."
INTERNAL_ERROR_CODE = "internal_error"
INTERNAL_ERROR_MESSAGE = "Ein interner Fehler ist aufgetreten."


def public_plan_contract_error() -> dict[str, str]:
    return {
        "error_code": PLAN_CONTRACT_ERROR_CODE,
        "message": PLAN_CONTRACT_MESSAGE,
    }


def public_internal_error() -> dict[str, str]:
    return {"error_code": INTERNAL_ERROR_CODE, "message": INTERNAL_ERROR_MESSAGE}


def public_classifier_fields(result: Any) -> dict[str, Any]:
    if not isinstance(result, ClassifierResult):
        return {}
    public: dict[str, Any] = {}
    _put_bool(public, "needs_orchestrator", result.needs_orchestrator)
    _put_bool(public, "is_long_document", result.is_long_document)
    _put_enum(public, "category", result.category, Category)
    _put_enum(public, "safety_level", result.safety_level, SafetyLevel)
    _put_enum(public, "route", result.route, Route)
    return public


def public_verifier_fields(result: Any) -> dict[str, Any]:
    if not isinstance(result, VerifierResult):
        return {}
    public: dict[str, Any] = {}
    _put_enum(public, "verdict", result.verdict, Verdict)
    return public


def _put_enum(public: dict[str, Any], key: str, value: Any, enum_type: type) -> None:
    if isinstance(value, enum_type):
        public[key] = value.value


def _put_bool(public: dict[str, Any], key: str, value: Any) -> None:
    if type(value) is bool:
        public[key] = value
