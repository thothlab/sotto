"""Оркестратор: idle -> recording -> transcribing -> вставка -> idle.

Работает в фоновых потоках (pynput listener + worker), UI (rumps) читает
state/history через таймер — AppKit из чужих потоков не трогаем.
"""

import os
import threading
from collections import deque

from . import config as config_mod
from .cloud_stt import transcribe_cloud
from .hotkey import HotkeyListener
from .paste import paste_text, set_clipboard
from .postprocess import postprocess
from .recorder import Recorder
from .transcriber import transcribe, warmup

IDLE, RECORDING, TRANSCRIBING = "idle", "recording", "transcribing"


def _notify(title: str, message: str) -> None:
    try:
        import rumps

        rumps.notification("Sotto", title, message)
    except Exception:
        pass  # вне app-бандла уведомления могут быть недоступны


class Orchestrator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.state = IDLE
        self.enabled = True
        self.history: deque[str] = deque(maxlen=5)
        self.version = 0  # растёт при каждом изменении history/last_error
        self.last_error: str | None = None
        self.model_ready = False
        self._recorder: Recorder | None = None
        self._listener: HotkeyListener | None = None
        self._lock = threading.Lock()

    # --- жизненный цикл -----------------------------------------------------

    def start(self):
        self._listener = HotkeyListener(
            self.cfg["trigger_key"], self._on_trigger_press, self._on_trigger_release
        )
        self._listener.start()
        self.warmup_async()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def warmup_async(self):
        if self.cfg["stt"]["backend"] == "cloud":
            self.model_ready = True  # локальная модель не нужна и не скачивается
            return
        self.model_ready = False

        def _warm():
            try:
                warmup(self.cfg["model"]["name"])
                self.model_ready = True
            except Exception as e:
                self._set_error(f"Модель не загрузилась: {e.__class__.__name__}")

        threading.Thread(target=_warm, daemon=True).start()

    # --- push-to-talk --------------------------------------------------------

    def _on_trigger_press(self):
        with self._lock:
            if not self.enabled or self.state != IDLE:
                return
            try:
                self._recorder = Recorder(
                    sample_rate=self.cfg["audio"]["sample_rate"],
                    device=self.cfg["audio"]["device"],
                )
                self._recorder.start()
                self.state = RECORDING
            except Exception as e:
                self._recorder = None
                self._set_error(f"Микрофон недоступен: {e.__class__.__name__}")

    def _on_trigger_release(self):
        with self._lock:
            if self.state != RECORDING or self._recorder is None:
                return
            recorder, self._recorder = self._recorder, None
            self.state = TRANSCRIBING
        threading.Thread(target=self._process, args=(recorder,), daemon=True).start()

    @property
    def level(self) -> float:
        rec = self._recorder
        return rec.level if rec else 0.0

    def _process(self, recorder: Recorder):
        wav_path = None
        try:
            wav_path, duration = recorder.stop()
            if duration < self.cfg["audio"]["min_duration"]:
                return  # случайный тап
            if self.cfg["stt"]["backend"] == "cloud":
                text = transcribe_cloud(
                    wav_path,
                    self.cfg,
                    config_mod.stt_api_key(self.cfg),
                    vocabulary=self.cfg["vocabulary"],
                )
            else:
                text = transcribe(
                    wav_path,
                    model_repo=self.cfg["model"]["name"],
                    language=self.cfg["model"]["language"],
                    vocabulary=self.cfg["vocabulary"],
                )
            if not text:
                return
            text = postprocess(text, self.cfg, config_mod.api_key(self.cfg))
            method = paste_text(
                text,
                restore_clipboard=self.cfg["paste"]["restore_clipboard"],
                restore_delay=self.cfg["paste"]["restore_delay"],
            )
            with self._lock:
                self.history.appendleft(text)
                self.last_error = (
                    "Нет права Accessibility — текст скопирован в буфер, вставьте Cmd+V. "
                    "После выдачи права перезапустите Sotto."
                    if method == "clipboard"
                    else None
                )
                self.version += 1
            if method == "clipboard":
                _notify("Текст в буфере обмена — вставьте Cmd+V",
                        "Выдайте Sotto право Accessibility и перезапустите приложение.")
        except Exception as e:
            detail = str(e) if isinstance(e, RuntimeError) else e.__class__.__name__
            self._set_error(f"Ошибка распознавания: {detail}")
        finally:
            if wav_path:
                try:
                    os.unlink(wav_path)  # диктовки на диске не храним
                except OSError:
                    pass
            with self._lock:
                self.state = IDLE

    def _set_error(self, msg: str):
        with self._lock:
            self.last_error = msg
            self.version += 1

    # --- действия из меню ----------------------------------------------------

    def set_model(self, repo: str):
        self.cfg["model"]["name"] = repo
        self.cfg["stt"]["backend"] = "local"
        config_mod.save_config(self.cfg)
        self.warmup_async()

    def set_cloud_backend(self):
        self.cfg["stt"]["backend"] = "cloud"
        config_mod.save_config(self.cfg)
        self.warmup_async()

    def set_device(self, name: str):
        self.cfg["audio"]["device"] = name
        config_mod.save_config(self.cfg)

    def toggle_postprocess(self) -> bool:
        self.cfg["postprocess"]["enabled"] = not self.cfg["postprocess"]["enabled"]
        config_mod.save_config(self.cfg)
        return self.cfg["postprocess"]["enabled"]

    def copy_history_item(self, index: int):
        items = list(self.history)
        if 0 <= index < len(items):
            set_clipboard(items[index])
