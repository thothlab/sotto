import importlib


def _fresh_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SOTTO_CONFIG_DIR", str(tmp_path / "sotto"))
    from sotto import config

    return importlib.reload(config)


def test_creates_defaults_on_first_load(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    cfg = config.load_config()
    assert config.CONFIG_PATH.exists()
    assert cfg["trigger_key"] == "alt_r"
    assert cfg["model"]["name"] == "mlx-community/whisper-large-v3-turbo"
    assert cfg["postprocess"]["enabled"] is False


def test_save_load_roundtrip(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    cfg = config.load_config()
    cfg["trigger_key"] = "f19"
    cfg["postprocess"]["enabled"] = True
    cfg["vocabulary"] = ["Fable", 'with "quotes"']
    config.save_config(cfg)

    cfg2 = config.load_config()
    assert cfg2["trigger_key"] == "f19"
    assert cfg2["postprocess"]["enabled"] is True
    assert cfg2["vocabulary"] == ["Fable", 'with "quotes"']


def test_user_config_merged_over_defaults(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    config.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config.CONFIG_PATH.write_text('trigger_key = "f18"\n[model]\nname = "x/y"\n')
    cfg = config.load_config()
    assert cfg["trigger_key"] == "f18"
    assert cfg["model"]["name"] == "x/y"
    # незаданные секции берутся из дефолтов
    assert cfg["audio"]["sample_rate"] == 16000


def test_api_key_from_env(tmp_path, monkeypatch):
    config = _fresh_config(tmp_path, monkeypatch)
    cfg = config.load_config()
    monkeypatch.setenv("SOTTO_API_KEY", "sk-test")
    assert config.api_key(cfg) == "sk-test"
