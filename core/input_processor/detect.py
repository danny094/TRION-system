from config import CHUNKING_THRESHOLD, ENABLE_CHUNKING


def estimate_input_tokens(user_text: str) -> int:
    text = str(user_text or "").strip()
    if not text:
        return 0
    return max(1, (len(text) + 3) // 4)


def is_long_document(user_text: str) -> bool:
    if not ENABLE_CHUNKING:
        return False
    return estimate_input_tokens(user_text) >= CHUNKING_THRESHOLD
