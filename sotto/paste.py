"""Вставка текста в активное поле ввода.

Основной путь: сохранить буфер -> положить текст -> Cmd+V (CGEvent) ->
восстановить буфер. Fallback: посимвольный ввод через CGEvent (pynput
Controller.type использует CGEventKeyboardSetUnicodeString). Если нет права
Accessibility — оставить текст в буфере и сообщить об этом вызывающему.
"""

import time

import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString

KEY_V = 9  # kVK_ANSI_V


def get_clipboard() -> str | None:
    pb = NSPasteboard.generalPasteboard()
    return pb.stringForType_(NSPasteboardTypeString)


def set_clipboard(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)


def _press_cmd_v() -> None:
    src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for down in (True, False):
        ev = Quartz.CGEventCreateKeyboardEvent(src, KEY_V, down)
        Quartz.CGEventSetFlags(ev, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def _type_fallback(text: str) -> None:
    from pynput.keyboard import Controller

    Controller().type(text)


def paste_text(text: str, restore_clipboard: bool = True, restore_delay: float = 0.3) -> str:
    """Вставляет текст. Возвращает способ: 'paste' | 'type' | 'clipboard'.

    'clipboard' означает, что эмуляция клавиш недоступна (нет Accessibility) —
    текст оставлен в буфере, пользователь вставит вручную.
    """
    old = get_clipboard() if restore_clipboard else None
    set_clipboard(text)
    time.sleep(0.05)  # дать pasteboard-серверу применить изменение

    method = "paste"
    try:
        _press_cmd_v()
    except Exception:
        try:
            _type_fallback(text)
            method = "type"
        except Exception:
            return "clipboard"  # буфер не восстанавливаем — текст должен остаться

    if restore_clipboard and old is not None:
        time.sleep(restore_delay)  # Cmd+V должен успеть прочитать буфер
        set_clipboard(old)
    return method
