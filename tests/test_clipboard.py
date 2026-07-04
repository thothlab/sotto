"""Сохранение/восстановление буфера обмена. Требует GUI-сессию macOS."""

import time

from sotto.paste import get_clipboard, set_clipboard


def test_clipboard_set_get_restore():
    original = get_clipboard()
    try:
        set_clipboard("sotto-test-первый ✓")
        time.sleep(0.05)
        assert get_clipboard() == "sotto-test-первый ✓"

        saved = get_clipboard()
        set_clipboard("sotto-test-второй")
        time.sleep(0.05)
        assert get_clipboard() == "sotto-test-второй"

        set_clipboard(saved)  # восстановление, как делает paste_text
        time.sleep(0.05)
        assert get_clipboard() == "sotto-test-первый ✓"
    finally:
        if original is not None:
            set_clipboard(original)
