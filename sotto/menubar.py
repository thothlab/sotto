"""Menu bar приложение (rumps). Иконка-статус: idle / recording / transcribing.

Все обновления UI идут из таймера на главном потоке; фоновые потоки
оркестратора только пишут state/history/version.
"""

import rumps

from .app import IDLE, RECORDING, TRANSCRIBING, Orchestrator
from .recorder import input_devices

MODELS = [
    ("large-v3-turbo · 1.6 ГБ (дефолт)", "mlx-community/whisper-large-v3-turbo"),
    ("medium · 1.5 ГБ", "mlx-community/whisper-medium-mlx"),
    ("small · 0.5 ГБ", "mlx-community/whisper-small-mlx"),
    ("tiny · 0.15 ГБ", "mlx-community/whisper-tiny"),
]
CLOUD_ITEM = "Облако (OpenAI / Groq API)"

ICONS = {IDLE: "🎙", RECORDING: "🔴", TRANSCRIBING: "⏳"}
LEVEL_BARS = "▁▂▃▅▆█"


class SottoApp(rumps.App):
    def __init__(self, orch: Orchestrator):
        super().__init__("Sotto", title=ICONS[IDLE], quit_button=None)
        self.orch = orch
        self._shown_version = -1

        self.status_item = rumps.MenuItem("Статус: запуск…")
        self.status_item.set_callback(None)

        self.enabled_item = rumps.MenuItem("Включено", callback=self._toggle_enabled)
        self.enabled_item.state = 1

        is_cloud = orch.cfg["stt"]["backend"] == "cloud"
        self.model_menu = rumps.MenuItem("Модель")
        for label, repo in MODELS:
            item = rumps.MenuItem(label, callback=self._pick_model)
            item.state = 1 if (not is_cloud and repo == orch.cfg["model"]["name"]) else 0
            self.model_menu.add(item)
        cloud_item = rumps.MenuItem(CLOUD_ITEM, callback=self._pick_model)
        cloud_item.state = 1 if is_cloud else 0
        self.model_menu.add(cloud_item)

        self.mic_menu = rumps.MenuItem("Микрофон")
        current_dev = orch.cfg["audio"]["device"]
        default_item = rumps.MenuItem("Системный по умолчанию", callback=self._pick_mic)
        default_item.state = 0 if current_dev else 1
        self.mic_menu.add(default_item)
        try:
            for name in input_devices():
                item = rumps.MenuItem(name, callback=self._pick_mic)
                item.state = 1 if name == current_dev else 0
                self.mic_menu.add(item)
        except Exception:
            pass  # без PortAudio-устройств меню остаётся с одним пунктом

        self.pp_item = rumps.MenuItem("Пост-обработка (LLM)", callback=self._toggle_pp)
        self.pp_item.state = 1 if orch.cfg["postprocess"]["enabled"] else 0

        self.history_menu = rumps.MenuItem("Последние транскрипты")
        self.history_menu.add(rumps.MenuItem("(пусто)"))

        self.menu = [
            self.status_item,
            None,
            self.enabled_item,
            self.model_menu,
            self.mic_menu,
            self.pp_item,
            self.history_menu,
            None,
            rumps.MenuItem("Выход", callback=self._quit),
        ]

        self._timer = rumps.Timer(self._tick, 0.25)
        self._timer.start()

    # --- синхронизация UI из состояния оркестратора --------------------------

    def _tick(self, _timer):
        orch = self.orch
        icon = ICONS[orch.state]
        if orch.state == RECORDING:
            icon += LEVEL_BARS[min(len(LEVEL_BARS) - 1, int(orch.level * len(LEVEL_BARS)))]
        if not orch.enabled:
            icon = "🎙💤"
        elif orch.state == IDLE and orch.last_error:
            icon = "🎙⚠️"  # проблема видна даже не открывая меню
        self.title = icon

        if orch.cfg["stt"]["backend"] == "cloud":
            model_short = f"облако · {orch.cfg['stt']['cloud_model']}"
        else:
            model_short = orch.cfg["model"]["name"].rsplit("/", 1)[-1]
        if orch.last_error:
            status = f"⚠️ {orch.last_error}"
        elif not orch.model_ready:
            status = f"Загрузка модели {model_short}…"
        else:
            status = f"Готов · {model_short}"
        if self.status_item.title != status:
            self.status_item.title = status

        if orch.version != self._shown_version:
            self._shown_version = orch.version
            self._rebuild_history()

    def _rebuild_history(self):
        self.history_menu.clear()
        items = list(self.orch.history)
        if not items:
            self.history_menu.add(rumps.MenuItem("(пусто)"))
            return
        for i, text in enumerate(items):
            label = text if len(text) <= 60 else text[:57] + "…"
            item = rumps.MenuItem(label, callback=self._make_copy_cb(i))
            self.history_menu.add(item)

    def _make_copy_cb(self, index):
        def cb(_item):
            self.orch.copy_history_item(index)

        return cb

    # --- обработчики меню -----------------------------------------------------

    def _toggle_enabled(self, item):
        self.orch.enabled = not self.orch.enabled
        item.state = 1 if self.orch.enabled else 0

    def _pick_model(self, item):
        if item.title == CLOUD_ITEM:
            from . import config as config_mod

            if not config_mod.stt_api_key(self.orch.cfg):
                rumps.alert(
                    "Нужен API-ключ",
                    "Добавьте ключ в ~/.config/sotto/config.toml → [stt] cloud_api_key\n"
                    "(или env OPENAI_API_KEY / GROQ_API_KEY).\n\n"
                    "OpenAI: cloud_model = \"whisper-1\"\n"
                    "Groq:   cloud_base_url = \"https://api.groq.com/openai/v1\",\n"
                    "        cloud_model = \"whisper-large-v3-turbo\"",
                )
                return
            self.orch.set_cloud_backend()
        else:
            self.orch.set_model(dict(MODELS)[item.title])
        for child in self.model_menu.values():
            child.state = 0
        item.state = 1

    def _pick_mic(self, item):
        for child in self.mic_menu.values():
            child.state = 0
        item.state = 1
        name = "" if item.title == "Системный по умолчанию" else item.title
        self.orch.set_device(name)

    def _toggle_pp(self, item):
        item.state = 1 if self.orch.toggle_postprocess() else 0

    def _quit(self, _item):
        self.orch.stop()
        rumps.quit_application()
