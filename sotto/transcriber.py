"""Локальное распознавание через mlx-whisper (Apple Silicon, офлайн после загрузки).

mlx-whisper кэширует модель в памяти между вызовами (ModelHolder), поэтому
после прогрева транскрипция короткой фразы занимает ~1 сек на M-серии.
"""

import tempfile
import wave

import mlx_whisper


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
        wav_path,
        path_or_hf_repo=model_repo,
        verbose=None,  # ничего не печатать: содержимое диктовок не логируем
        **kwargs,
    )
    return result["text"].strip()


def warmup(model_repo: str) -> None:
    """Скачивает (при первом запуске) и загружает модель в память: транскрибирует
    полсекунды тишины, чтобы первая реальная фраза не ждала загрузку весов."""
    f = tempfile.NamedTemporaryFile(prefix="sotto_warmup_", suffix=".wav", delete=False)
    with wave.open(f, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 8000)
    try:
        mlx_whisper.transcribe(f.name, path_or_hf_repo=model_repo, verbose=None)
    finally:
        import os

        os.unlink(f.name)
