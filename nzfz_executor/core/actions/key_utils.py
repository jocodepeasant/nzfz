"""键盘键名归一化（P2-11）。"""

from __future__ import annotations

_NAMED_KEYS = {
    "esc": "esc",
    "escape": "esc",
    "space": "space",
    "enter": "enter",
    "return": "enter",
}


def normalize_key(key: str) -> str:
    key = key.strip()
    if not key:
        return ""
    if len(key) == 1:
        return key.lower()
    lowered = key.lower()
    return _NAMED_KEYS.get(lowered, lowered)


def is_supported_key(key: str) -> bool:
    normalized = normalize_key(key)
    if not normalized:
        return False
    if len(normalized) == 1 and normalized.isalnum():
        return True
    return normalized in _NAMED_KEYS.values()
