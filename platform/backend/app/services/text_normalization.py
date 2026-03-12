from __future__ import annotations

import re

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_MOJIBAKE_HINT_RE = re.compile(
    r"[\u00C3\u00C2\u00E2\u00E6\u00E5\u00E7\u00E8\u00E9\u00EA\u00EB\u00EC\u00ED"
    r"\u00EE\u00EF\u00F0\u00F1\u00F2\u00F3\u00F4\u00F5\u00F6\u00F8\u00F9\u00FA"
    r"\u00FB\u00FC\u00FD\u00FE\u00FF]"
)


def repair_mojibake_text(value: str) -> str:
    text = str(value or "")
    # Fast path: no suspicious mojibake markers means no repair attempt.
    if not _MOJIBAKE_HINT_RE.search(text):
        return text

    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        return text

    if repaired == text:
        return text

    # Only accept conversion when confidence is high to avoid corrupting valid non-CJK text.
    original_hint_count = len(_MOJIBAKE_HINT_RE.findall(text))
    repaired_hint_count = len(_MOJIBAKE_HINT_RE.findall(repaired))
    if _CJK_RE.search(repaired) and repaired_hint_count < original_hint_count:
        return repaired
    if repaired_hint_count == 0 and original_hint_count > 0:
        return repaired
    return text
