"""Глобальный push-to-talk слушатель на pynput.

Триггер настраивается строкой: "alt_r" (дефолт), "f19", "cmd+shift+d",
одиночный символ "d". События не подавляются — модификатор сам по себе
ничего не печатает, левый Option и раскладки не затрагиваются.
"""

from pynput import keyboard


def parse_trigger(spec: str) -> frozenset:
    keys = set()
    for part in spec.split("+"):
        part = part.strip().lower()
        if not part:
            continue
        if len(part) == 1:
            keys.add(keyboard.KeyCode.from_char(part))
        else:
            try:
                keys.add(getattr(keyboard.Key, part))
            except AttributeError:
                raise ValueError(
                    f"Неизвестная клавиша в trigger_key: {part!r} "
                    "(имена — как в pynput.keyboard.Key, например alt_r, f19, cmd)"
                ) from None
    if not keys:
        raise ValueError("Пустой trigger_key")
    return frozenset(keys)


class HotkeyListener:
    """Зажатие всех клавиш триггера -> on_activate; отпускание любой -> on_deactivate."""

    def __init__(self, trigger_spec: str, on_activate, on_deactivate):
        self._trigger = parse_trigger(trigger_spec)
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._pressed: set = set()
        self._active = False
        self._listener: keyboard.Listener | None = None

    def _norm(self, key):
        if isinstance(key, keyboard.KeyCode) and self._listener is not None:
            return self._listener.canonical(key)
        return key

    def _handle_press(self, key):
        key = self._norm(key)
        self._pressed.add(key)
        if not self._active and self._trigger <= self._pressed:
            self._active = True
            self._on_activate()

    def _handle_release(self, key):
        key = self._norm(key)
        self._pressed.discard(key)
        if self._active and key in self._trigger:
            self._active = False
            self._on_deactivate()

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._handle_press, on_release=self._handle_release
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
