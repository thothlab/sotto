import pytest
from pynput import keyboard

from sotto.hotkey import HotkeyListener, parse_trigger


def test_parse_default_alt_r():
    assert parse_trigger("alt_r") == frozenset({keyboard.Key.alt_r})


def test_parse_combo():
    keys = parse_trigger("cmd+shift+d")
    assert keyboard.Key.cmd in keys
    assert keyboard.Key.shift in keys
    assert keyboard.KeyCode.from_char("d") in keys


def test_parse_unknown_key_raises():
    with pytest.raises(ValueError):
        parse_trigger("no_such_key")


def test_press_release_cycle_without_os_listener():
    events = []
    hl = HotkeyListener("alt_r", lambda: events.append("on"), lambda: events.append("off"))
    # эмулируем колбэки pynput напрямую, без реального Input Monitoring
    hl._handle_press(keyboard.Key.alt_r)
    hl._handle_press(keyboard.Key.alt_r)  # автоповтор не активирует второй раз
    hl._handle_release(keyboard.Key.alt_r)
    hl._handle_release(keyboard.Key.alt_r)
    assert events == ["on", "off"]


def test_combo_requires_all_keys():
    events = []
    hl = HotkeyListener("cmd+d", lambda: events.append("on"), lambda: events.append("off"))
    hl._handle_press(keyboard.Key.cmd)
    assert events == []
    hl._handle_press(keyboard.KeyCode.from_char("d"))
    assert events == ["on"]
    hl._handle_release(keyboard.Key.cmd)
    assert events == ["on", "off"]
