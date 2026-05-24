"""P2-11 key_utils 单元测试。"""

from __future__ import annotations

from nzfz_executor.core.actions.key_utils import is_supported_key, normalize_key


class TestNormalizeKey:
    def test_single_letter_lowercase(self) -> None:
        assert normalize_key("O") == "o"
        assert normalize_key("1") == "1"

    def test_named_keys(self) -> None:
        assert normalize_key("ENTER") == "enter"
        assert normalize_key("Escape") == "esc"

    def test_empty(self) -> None:
        assert normalize_key("") == ""
        assert normalize_key("   ") == ""


class TestIsSupportedKey:
    def test_digits_and_letters(self) -> None:
        assert is_supported_key("1")
        assert is_supported_key("a")

    def test_named_keys(self) -> None:
        assert is_supported_key("esc")
        assert is_supported_key("space")
        assert is_supported_key("enter")

    def test_unsupported(self) -> None:
        assert is_supported_key("f1") is False
        assert is_supported_key("") is False
