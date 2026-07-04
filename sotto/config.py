"""Конфиг: один TOML в ~/.config/sotto/, создаётся с дефолтами при первом запуске."""

import os
import tomllib
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("SOTTO_CONFIG_DIR", str(Path.home() / ".config" / "sotto")))
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULTS: dict = {
    "trigger_key": "alt_r",
    "vocabulary": ["Claude Code", "MCP"],
    "audio": {
        "device": "",  # пусто = системный микрофон по умолчанию
        "sample_rate": 16000,
        "min_duration": 0.25,
    },
    "model": {
        "name": "mlx-community/whisper-large-v3-turbo",
        "language": "",  # пусто = автоопределение
    },
    "stt": {
        "backend": "local",  # local (mlx-whisper, офлайн) | cloud (OpenAI-совместимый API)
        "cloud_base_url": "https://api.openai.com/v1",
        "cloud_api_key": "",  # или env SOTTO_STT_API_KEY / OPENAI_API_KEY / GROQ_API_KEY
        "cloud_model": "whisper-1",
        "cloud_timeout": 15.0,
    },
    "paste": {
        "restore_clipboard": True,
        "restore_delay": 0.3,
    },
    "postprocess": {
        "enabled": False,
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "",  # или env SOTTO_API_KEY / OPENROUTER_API_KEY
        "model": "openai/gpt-4o-mini",
        "timeout": 10.0,
    },
}

DEFAULT_TOML = '''# Sotto — конфигурация. Создан автоматически при первом запуске.

# Клавиша-триггер push-to-talk. Примеры: "alt_r" (правая Option, дефолт),
# "f19", "cmd+shift+d". Имена клавиш — как в pynput.keyboard.Key.
trigger_key = "alt_r"

# Пользовательский словарь: термины подсказываются Whisper (initial_prompt)
# и передаются LLM при пост-обработке.
vocabulary = ["Claude Code", "MCP"]

[audio]
device = ""            # имя микрофона; пусто = системный по умолчанию
sample_rate = 16000
min_duration = 0.25    # записи короче (сек) игнорируются как случайный тап

[model]
name = "mlx-community/whisper-large-v3-turbo"
language = ""          # "" = авто (русский/английский вперемешку — ок)

[stt]
# Распознавание: "local" — mlx-whisper на этом Mac (офлайн, модель качается
# при первом запуске); "cloud" — OpenAI-совместимый API /audio/transcriptions
# (OpenAI: whisper-1 / gpt-4o-mini-transcribe; Groq: whisper-large-v3-turbo).
# OpenRouter распознавание речи не предоставляет — он подходит только для
# секции [postprocess].
backend = "local"
cloud_base_url = "https://api.openai.com/v1"
cloud_api_key = ""     # или env SOTTO_STT_API_KEY / OPENAI_API_KEY / GROQ_API_KEY
cloud_model = "whisper-1"
cloud_timeout = 15.0

[paste]
restore_clipboard = true
restore_delay = 0.3    # сек до восстановления прежнего буфера

[postprocess]
enabled = false
base_url = "https://openrouter.ai/api/v1"
api_key = ""           # ключ здесь или в env SOTTO_API_KEY / OPENROUTER_API_KEY
model = "openai/gpt-4o-mini"
timeout = 10.0
'''


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(DEFAULT_TOML, encoding="utf-8")
    with open(CONFIG_PATH, "rb") as f:
        user = tomllib.load(f)
    return _merge(DEFAULTS, user)


def _toml_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def save_config(cfg: dict) -> None:
    """Сериализует плоскую схему Sotto (скаляры/списки сверху, потом таблицы)."""
    lines = []
    for k, v in cfg.items():
        if not isinstance(v, dict):
            lines.append(f"{k} = {_toml_value(v)}")
    for k, v in cfg.items():
        if isinstance(v, dict):
            lines.append(f"\n[{k}]")
            for k2, v2 in v.items():
                lines.append(f"{k2} = {_toml_value(v2)}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def api_key(cfg: dict) -> str:
    return (
        cfg["postprocess"]["api_key"]
        or os.environ.get("SOTTO_API_KEY", "")
        or os.environ.get("OPENROUTER_API_KEY", "")
    )


def stt_api_key(cfg: dict) -> str:
    return (
        cfg["stt"]["cloud_api_key"]
        or os.environ.get("SOTTO_STT_API_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
        or os.environ.get("GROQ_API_KEY", "")
    )
