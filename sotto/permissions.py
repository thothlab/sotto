"""Проверка macOS-разрешений и понятные инструкции вместо молчаливого падения.

Права выдаются приложению-родителю (Terminal / iTerm2 — тому, из чего запущен
Python), поэтому в System Settings галочки ставятся на терминал.
"""

import ctypes
import ctypes.util
import sys

GRANTED, DENIED, UNKNOWN = "granted", "denied", "unknown"

# кому выдаются права: standalone Sotto.app или терминал-родитель
GRANTEE = "Sotto" if getattr(sys, "frozen", False) else "ваш терминал (Terminal / iTerm2)"


def check_accessibility() -> str:
    try:
        from ApplicationServices import AXIsProcessTrusted

        return GRANTED if AXIsProcessTrusted() else DENIED
    except Exception:
        return UNKNOWN


def check_input_monitoring() -> str:
    """IOHIDCheckAccess(kIOHIDRequestTypeListenEvent): 0=granted 1=denied 2=unknown."""
    try:
        iokit = ctypes.CDLL(ctypes.util.find_library("IOKit"))
        iokit.IOHIDCheckAccess.restype = ctypes.c_uint32
        iokit.IOHIDCheckAccess.argtypes = [ctypes.c_uint32]
        status = iokit.IOHIDCheckAccess(1)  # kIOHIDRequestTypeListenEvent
        return {0: GRANTED, 1: DENIED}.get(status, UNKNOWN)
    except Exception:
        return UNKNOWN


def check_microphone() -> str:
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio

        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        # 0 notDetermined, 1 restricted, 2 denied, 3 authorized
        return {3: GRANTED, 2: DENIED, 1: DENIED}.get(status, UNKNOWN)
    except Exception:
        return UNKNOWN


INSTRUCTIONS = {
    "microphone": (
        f"Микрофон: System Settings → Privacy & Security → Microphone → "
        f"включите {GRANTEE}. Запрос появится при первой записи."
    ),
    "input_monitoring": (
        f"Input Monitoring (перехват клавиши-триггера): System Settings → "
        f"Privacy & Security → Input Monitoring → добавьте и включите {GRANTEE}. "
        f"Без этого зажатие правой Option не будет замечено."
    ),
    "accessibility": (
        f"Accessibility (эмуляция Cmd+V для вставки): System Settings → "
        f"Privacy & Security → Accessibility → добавьте и включите {GRANTEE}. "
        f"Без этого текст будет только копироваться в буфер."
    ),
}


def report() -> tuple[dict, list[str]]:
    """(статусы, список инструкций по недостающим правам)."""
    statuses = {
        "microphone": check_microphone(),
        "input_monitoring": check_input_monitoring(),
        "accessibility": check_accessibility(),
    }
    missing = [INSTRUCTIONS[name] for name, st in statuses.items() if st != GRANTED]
    return statuses, missing
