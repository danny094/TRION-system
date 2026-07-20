from dataclasses import dataclass
from typing import Optional

from core.classifier.classifier import classify
from core.classifier.contracts import ClassifierResult
from core.input_processor.contracts import DocumentContext
from core.input_processor.processor import SemanticSaveFn, WorkspaceSaveFn, process_long_input


@dataclass(frozen=True)
class PreprocessResult:
    classifier_result: ClassifierResult
    document_context: DocumentContext | None
    planning_user_text: str
    raw_user_text: str


def preprocess_request(
    user_text: str,
    *,
    conversation_id: str = "",
    classify_fn=classify,
    workspace_save_fn: WorkspaceSaveFn | None = None,
    semantic_save_fn: SemanticSaveFn | None = None,
) -> PreprocessResult:
    raw_user_text = str(user_text or "")
    classifier_result = classify_fn(raw_user_text)
    document_context = _build_document_context(
        raw_user_text,
        classifier_result,
        conversation_id=conversation_id,
        workspace_save_fn=workspace_save_fn,
        semantic_save_fn=semantic_save_fn,
    )
    planning_user_text = _planning_user_text(raw_user_text, document_context)
    return PreprocessResult(
        classifier_result=classifier_result,
        document_context=document_context,
        planning_user_text=planning_user_text,
        raw_user_text=raw_user_text,
    )


def _build_document_context(
    user_text: str,
    classifier_result: ClassifierResult,
    *,
    conversation_id: str,
    workspace_save_fn: WorkspaceSaveFn | None,
    semantic_save_fn: SemanticSaveFn | None,
) -> DocumentContext | None:
    if not classifier_result.is_long_document:
        return None
    return process_long_input(
        user_text,
        conversation_id=conversation_id,
        workspace_save_fn=workspace_save_fn,
        semantic_save_fn=semantic_save_fn,
    )


def _planning_user_text(user_text: str, document_context: Optional[DocumentContext]) -> str:
    if document_context and document_context.summary:
        return document_context.summary
    return user_text
