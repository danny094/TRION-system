from __future__ import annotations

import re

_OPEN = "<think>"
_CLOSE = "</think>"
_WHOLE_BLOCK_RE = re.compile(r"<think>.*?</think>", re.IGNORECASE | re.DOTALL)


def sanitize_reasoning_text(text: str) -> str:
    value = str(text or "")
    if not value:
        return ""
    sanitized = _WHOLE_BLOCK_RE.sub("", value)
    sanitized = sanitized.replace(_OPEN, "").replace(_CLOSE, "")
    return sanitized.strip()


class StreamingReasoningSanitizer:
    def __init__(self) -> None:
        self._buffer = ""
        self._inside_think = False

    def feed(self, chunk: str) -> list[str]:
        if not chunk:
            return []
        self._buffer += str(chunk)
        out: list[str] = []
        while self._buffer:
            if self._inside_think:
                close_index = self._buffer.lower().find(_CLOSE)
                if close_index < 0:
                    self._buffer = _keep_possible_prefix(self._buffer, _CLOSE)
                    return out
                self._buffer = self._buffer[close_index + len(_CLOSE) :]
                self._inside_think = False
                continue

            open_index = self._buffer.lower().find(_OPEN)
            if open_index < 0:
                emit, rest = _split_safe_prefix(self._buffer, _OPEN)
                if emit:
                    out.append(emit)
                self._buffer = rest
                return out

            if open_index > 0:
                out.append(self._buffer[:open_index])
            self._buffer = self._buffer[open_index + len(_OPEN) :]
            self._inside_think = True
        return out

    def flush(self) -> list[str]:
        if self._inside_think:
            self._buffer = ""
            return []
        emit, rest = _split_safe_prefix(self._buffer, _OPEN)
        self._buffer = rest
        return [emit] if emit else []


def _split_safe_prefix(text: str, marker: str) -> tuple[str, str]:
    keep = _longest_marker_prefix_suffix(text, marker)
    if keep <= 0:
        return text, ""
    return text[:-keep], text[-keep:]


def _keep_possible_prefix(text: str, marker: str) -> str:
    keep = _longest_marker_prefix_suffix(text, marker)
    return text[-keep:] if keep > 0 else ""


def _longest_marker_prefix_suffix(text: str, marker: str) -> int:
    lower_text = text.lower()
    lower_marker = marker.lower()
    max_keep = min(len(lower_text), len(lower_marker) - 1)
    for size in range(max_keep, 0, -1):
        if lower_text.endswith(lower_marker[:size]):
            return size
    return 0
