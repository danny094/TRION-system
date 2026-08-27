from core.output.contracts import OutputRequest


TOOL_MARKUP_MARKER = "[TOOL_CALL]"
TOOL_MARKUP_REJECTION = (
    "Die Antwort enthielt unzulässiges Tool-Markup und wurde verworfen. "
    "Bitte wiederhole die Anfrage."
)


def apply_tool_markup_guard(output_request: OutputRequest, content: str) -> str:
    del output_request
    if TOOL_MARKUP_MARKER not in str(content or ""):
        return content
    return TOOL_MARKUP_REJECTION
