"""Цикл «WAV -> транскрипт» без микрофона: say -> aiff -> ffmpeg -> wav -> whisper.

По умолчанию используется маленькая модель (быстрый тест, тот же код-путь).
Прогнать на боевой: SOTTO_TEST_MODEL=mlx-community/whisper-large-v3-turbo pytest
"""

import os
import re
import shutil
import subprocess

import pytest

MODEL = os.environ.get("SOTTO_TEST_MODEL", "mlx-community/whisper-tiny")
PHRASE = "Hello world. Testing dictation one two three."


PREFERRED_VOICES = ["Samantha", "Alex", "Eddy", "Flo", "Fred", "Kathy"]


def _english_voice() -> str | None:
    """Нормальный en_US голос; первый попавшийся может быть novelty (Albert, Bells…)."""
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True).stdout
    names = [
        re.split(r"\s{2,}", line)[0].strip()
        for line in out.splitlines()
        if "en_US" in line
    ]
    for pref in PREFERRED_VOICES:
        for name in names:
            if name == pref or name.startswith(pref + " "):
                return name
    return names[0] if names else None


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="нужен ffmpeg")
def test_wav_to_transcript(tmp_path):
    aiff = tmp_path / "t.aiff"
    wav = tmp_path / "t.wav"

    voice = _english_voice()
    cmd = ["say", "-o", str(aiff), PHRASE]
    if voice:
        cmd[1:1] = ["-v", voice]
    subprocess.run(cmd, check=True)
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), "-ar", "16000", "-ac", "1", str(wav)],
        check=True,
    )

    from sotto.transcriber import transcribe

    text = transcribe(str(wav), model_repo=MODEL).lower()
    expected = [("hello",), ("world",), ("testing", "test"), ("one", "1"), ("two", "2"), ("three", "3")]
    hits = sum(any(v in text for v in variants) for variants in expected)
    assert hits >= 3, f"слишком мало совпадений в транскрипте: {text!r}"


def test_vocabulary_becomes_initial_prompt(monkeypatch, tmp_path):
    import sotto.transcriber as tr

    captured = {}

    def fake_transcribe(path, **kwargs):
        captured.update(kwargs)
        return {"text": " ok "}

    monkeypatch.setattr(tr.mlx_whisper, "transcribe", fake_transcribe)
    out = tr.transcribe("x.wav", model_repo="m", language="ru", vocabulary=["Claude Code", "MCP"])
    assert out == "ok"
    assert captured["language"] == "ru"
    assert "Claude Code" in captured["initial_prompt"]
    assert "Glossary" not in captured["initial_prompt"]  # метки просачиваются в вывод
    assert captured["verbose"] is None
