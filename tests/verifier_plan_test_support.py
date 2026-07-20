from core.verifier.input_prepare import VerifierInput


def build_verifier_input(*, focus: str = "") -> VerifierInput:
    meta = {"question_focus": focus} if focus else {}
    return VerifierInput(
        user_text="Bitte hilf beim Plan.",
        document_mode="long_document" if focus else "normal",
        document_summary="",
        document_meta=meta,
        user_excerpt="Bitte hilf beim Plan.",
    )
