"""Автозапуск: LaunchAgent ~/Library/LaunchAgents/com.sotto.app.plist."""

import os
import plistlib
import subprocess
import sys
from pathlib import Path

from . import BUNDLE_ID

PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{BUNDLE_ID}.plist"


def _plist() -> dict:
    return {
        "Label": BUNDLE_ID,
        "ProgramArguments": [sys.executable, "-m", "sotto", "run"],
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
        "StandardOutPath": "/tmp/sotto.out.log",
        "StandardErrorPath": "/tmp/sotto.err.log",
    }


def install() -> str:
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PLIST_PATH, "wb") as f:
        plistlib.dump(_plist(), f)
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(PLIST_PATH)],
        capture_output=True,  # мог быть загружен раньше — игнорируем ошибку
    )
    res = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        return f"plist записан в {PLIST_PATH}, но launchctl bootstrap не удался: {res.stderr.strip()}"
    return f"Автозапуск установлен: {PLIST_PATH}"


def uninstall() -> str:
    uid = os.getuid()
    subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}", str(PLIST_PATH)], capture_output=True
    )
    if PLIST_PATH.exists():
        PLIST_PATH.unlink()
        return f"Автозапуск удалён: {PLIST_PATH}"
    return "LaunchAgent не был установлен."
