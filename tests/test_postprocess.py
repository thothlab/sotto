from sotto.config import DEFAULTS
from sotto.postprocess import postprocess


def _cfg(enabled=True):
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    cfg["postprocess"]["enabled"] = enabled
    return cfg


def test_disabled_returns_raw():
    assert postprocess("сырой текст", _cfg(enabled=False), "sk-x") == "сырой текст"


def test_no_api_key_returns_raw():
    assert postprocess("raw", _cfg(), "") == "raw"


def test_api_error_returns_raw(monkeypatch):
    cfg = _cfg()
    cfg["postprocess"]["base_url"] = "http://127.0.0.1:1"  # заведомо недоступен
    cfg["postprocess"]["timeout"] = 0.2
    assert postprocess("raw text", cfg, "sk-x") == "raw text"
