"""Локальное распознавание через mlx-whisper (Apple Silicon, офлайн после загрузки).

WAV декодируется своими силами (wave + numpy) и передаётся массивом —
системный ffmpeg не нужен, что важно для standalone Sotto.app.
mlx-whisper кэширует модель в памяти между вызовами (ModelHolder), поэтому
после прогрева транскрипция короткой фразы занимает ~1 сек на M-серии.
"""

import wave

import mlx_whisper
import numpy as np

SAMPLE_RATE = 16000  # mlx-whisper ждёт 16 kHz float32 mono


def _load_wav(wav_path: str) -> np.ndarray:
    with wave.open(wav_path, "rb") as w:
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, "ожидается 16-bit mono WAV"
        assert w.getframerate() == SAMPLE_RATE, f"ожидается {SAMPLE_RATE} Hz"
        data = w.readframes(w.getnframes())
    return np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0


def transcribe(wav_path: str, model_repo: str, language: str = "", vocabulary: list[str] | None = None) -> str:
    """WAV 16kHz mono -> текст. Словарь подсказывается модели через initial_prompt."""
    kwargs = {}
    if language:
        kwargs["language"] = language
    if vocabulary:
        # initial_prompt воспринимается как «предыдущий текст» — просто термины,
        # без метки вроде "Glossary:", иначе она просачивается в транскрипт
        kwargs["initial_prompt"] = ", ".join(vocabulary) + "."
    result = mlx_whisper.transcribe(
        _load_wav(wav_path),
        path_or_hf_repo=model_repo,
        verbose=None,  # ничего не печатать: содержимое диктовок не логируем
        **kwargs,
    )
    return result["text"].strip()


def warmup(model_repo: str) -> None:
    """Скачивает (при первом запуске) и загружает модель в память: транскрибирует
    полсекунды тишины, чтобы первая реальная фраза не ждала загрузку весов."""
    silence = np.zeros(SAMPLE_RATE // 2, dtype=np.float32)
    mlx_whisper.transcribe(silence, path_or_hf_repo=model_repo, verbose=None)
