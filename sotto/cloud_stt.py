"""Облачное распознавание: OpenAI-совместимый endpoint /audio/transcriptions.

Работает с OpenAI (whisper-1, gpt-4o-mini-transcribe) и Groq
(whisper-large-v3-turbo). Содержимое диктовок не логируется. При ошибке
бросает исключение — решает вызывающий (у STT нет «сырого текста» для
молчаливого фолбэка, в отличие от пост-обработки).
"""

import json
import urllib.request
import uuid
from pathlib import Path


def _multipart(fields: dict[str, str], file_field: str, file_path: str) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    lines: list[bytes] = []
    for name, value in fields.items():
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{name}"'.encode(),
            b"",
            str(value).encode("utf-8"),
        ]
    lines += [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="{file_field}"; filename="{Path(file_path).name}"'.encode(),
        b"Content-Type: audio/wav",
        b"",
        Path(file_path).read_bytes(),
        f"--{boundary}--".encode(),
        b"",
    ]
    return b"\r\n".join(lines), f"multipart/form-data; boundary={boundary}"


def transcribe_cloud(
    wav_path: str, cfg: dict, api_key: str, vocabulary: list[str] | None = None
) -> str:
    stt = cfg["stt"]
    if not api_key:
        raise RuntimeError("не задан API-ключ облачного распознавания (stt.cloud_api_key)")
    fields = {"model": stt["cloud_model"], "response_format": "json"}
    if cfg["model"]["language"]:
        fields["language"] = cfg["model"]["language"]
    if vocabulary:
        # как и initial_prompt локального Whisper: голые термины, без меток
        fields["prompt"] = ", ".join(vocabulary) + "."
    body, content_type = _multipart(fields, "file", wav_path)
    req = urllib.request.Request(
        stt["cloud_base_url"].rstrip("/") + "/audio/transcriptions",
        data=body,
        headers={"Content-Type": content_type, "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=float(stt["cloud_timeout"])) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data.get("text", "")).strip()
