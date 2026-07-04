"""Запись с микрофона: 16 kHz mono int16 -> временный WAV.

Содержимое диктовок никуда не логируется; WAV удаляется вызывающей стороной
сразу после распознавания.
"""

import tempfile
import threading
import wave

import numpy as np
import sounddevice as sd


def input_devices() -> list[str]:
    """Имена доступных микрофонов."""
    names = []
    for dev in sd.query_devices():
        if dev["max_input_channels"] > 0:
            names.append(dev["name"])
    return names


class Recorder:
    def __init__(self, sample_rate: int = 16000, device: str = ""):
        self._sample_rate = sample_rate
        self._device = device or None
        self._stream: sd.InputStream | None = None
        self._frames: list[bytes] = []
        self._lock = threading.Lock()
        self.level: float = 0.0  # RMS 0..1 последнего блока, для индикации

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            self._frames.append(bytes(indata))
        samples = np.frombuffer(indata, dtype=np.int16)
        if samples.size:
            rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
            self.level = min(1.0, rms / 32768.0 * 4)

    def start(self):
        self._frames = []
        self.level = 0.0
        self._stream = sd.RawInputStream(
            samplerate=self._sample_rate,
            channels=1,
            dtype="int16",
            device=self._device,
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> tuple[str, float]:
        """Останавливает запись. Возвращает (путь к tmp WAV, длительность в сек)."""
        assert self._stream is not None, "start() не вызывался"
        self._stream.stop()
        self._stream.close()
        self._stream = None
        with self._lock:
            data = b"".join(self._frames)
            self._frames = []
        duration = len(data) / 2 / self._sample_rate
        f = tempfile.NamedTemporaryFile(prefix="sotto_", suffix=".wav", delete=False)
        with wave.open(f, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self._sample_rate)
            w.writeframes(data)
        return f.name, duration
