"""Опциональная LLM-пост-обработка по OpenAI-совместимому API.

Пунктуация, капитализация, исправление доменных терминов по словарю.
При любой ошибке (сеть, ключ, таймаут) молча возвращает сырой текст.
Содержимое диктовок не логируется.
"""

import json
import urllib.request

SYSTEM_PROMPT = (
    "You clean up dictated speech-to-text transcripts. Fix punctuation and "
    "capitalization. Keep the original language(s) and wording — do not "
    "paraphrase, translate, answer questions or add anything. If a word "
    "sounds like a term from the glossary below, replace it with the exact "
    "glossary spelling. Return only the cleaned text.\nGlossary: {glossary}"
)


def postprocess(text: str, cfg: dict, api_key: str) -> str:
    pp = cfg["postprocess"]
    if not pp["enabled"] or not api_key or not text:
        return text
    glossary = ", ".join(cfg.get("vocabulary", [])) or "(empty)"
    payload = {
        "model": pp["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT.format(glossary=glossary)},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
    }
    req = urllib.request.Request(
        pp["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=float(pp["timeout"])) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        cleaned = data["choices"][0]["message"]["content"].strip()
        return cleaned or text
    except Exception:
        return text  # API недоступен — молча вставляем сырой текст
