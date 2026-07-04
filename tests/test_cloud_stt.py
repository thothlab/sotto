import io
import json
import urllib.request

import pytest

from sotto.cloud_stt import _multipart, transcribe_cloud
from sotto.config import DEFAULTS


def _cfg():
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    cfg["stt"]["backend"] = "cloud"
    return cfg


def test_multipart_contains_fields_and_file(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFFxxxx")
    body, content_type = _multipart({"model": "whisper-1", "prompt": "MCP."}, "file", str(wav))
    boundary = content_type.split("boundary=")[1]
    assert boundary.encode() in body
    assert b'name="model"' in body and b"whisper-1" in body
    assert b'name="prompt"' in body and "MCP.".encode() in body
    assert b'filename="a.wav"' in body and b"RIFFxxxx" in body
    assert body.endswith(f"--{boundary}--".encode() + b"\r\n")


def test_no_api_key_raises(tmp_path):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    with pytest.raises(RuntimeError, match="API-ключ"):
        transcribe_cloud(str(wav), _cfg(), api_key="")


def test_request_and_response_parsing(tmp_path, monkeypatch):
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFF")
    captured = {}

    class FakeResp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        captured["body"] = req.data
        return FakeResp(json.dumps({"text": " привет мир "}).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    cfg = _cfg()
    text = transcribe_cloud(str(wav), cfg, api_key="sk-x", vocabulary=["Claude Code"])
    assert text == "привет мир"
    assert captured["url"] == "https://api.openai.com/v1/audio/transcriptions"
    assert captured["auth"] == "Bearer sk-x"
    assert b"Claude Code." in captured["body"]
    assert b"Glossary" not in captured["body"]
