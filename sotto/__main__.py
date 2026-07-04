"""CLI: python -m sotto [run|check|install-autostart|uninstall-autostart]."""

import argparse
import sys


def cmd_check() -> int:
    import shutil

    from . import permissions

    statuses, missing = permissions.report()
    names = {
        "microphone": "Microphone",
        "input_monitoring": "Input Monitoring",
        "accessibility": "Accessibility",
    }
    marks = {"granted": "✅", "denied": "❌", "unknown": "❓"}
    print(f"Права macOS (выдаются: {permissions.GRANTEE}):")
    for key, st in statuses.items():
        print(f"  {marks[st]} {names[key]}: {st}")
    if missing:
        print("\nЧто сделать:")
        for line in missing:
            print(f"  • {line}")
        print("\nПосле изменения галочек перезапустите Sotto (и терминал, если запуск из него).")
    else:
        print("\nВсе права на месте.")
    if shutil.which("ffmpeg") is None:
        print(
            "\nℹ️  ffmpeg не найден — для работы Sotto он не нужен, но пригодится "
            "для тестов и распознавания аудиофайлов не-WAV форматов: brew install ffmpeg"
        )
    return 0


def cmd_transcribe(path: str) -> int:
    """Распознать готовый аудиофайл. 16kHz mono WAV — напрямую; прочие форматы —
    через ffmpeg, если он установлен."""
    import os
    import shutil
    import subprocess
    import tempfile

    from . import config as config_mod
    from .transcriber import _load_wav, transcribe

    cfg = config_mod.load_config()
    wav, tmp = path, None
    try:
        _load_wav(path)
    except Exception:
        if shutil.which("ffmpeg") is None:
            print(
                "Файл не является 16kHz mono WAV. Установите ffmpeg — тогда Sotto "
                "будет конвертировать любые аудиоформаты сам: brew install ffmpeg",
                file=sys.stderr,
            )
            return 1
        tmp = tempfile.NamedTemporaryFile(prefix="sotto_", suffix=".wav", delete=False).name
        conv = subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-ar", "16000", "-ac", "1", tmp],
            capture_output=True,
            text=True,
        )
        if conv.returncode != 0:
            print(f"ffmpeg не смог сконвертировать файл: {conv.stderr.strip()}", file=sys.stderr)
            os.unlink(tmp)
            return 1
        wav = tmp
    try:
        print(
            transcribe(
                wav,
                model_repo=cfg["model"]["name"],
                language=cfg["model"]["language"],
                vocabulary=cfg["vocabulary"],
            )
        )
    finally:
        if tmp:
            os.unlink(tmp)
    return 0


def cmd_probe_menu() -> int:
    """Диагностика: поднимает menu bar app на 3 сек и печатает состояние меню."""
    import rumps

    from . import config as config_mod
    from .app import Orchestrator
    from .menubar import SottoApp

    app = SottoApp(Orchestrator(config_mod.load_config()))

    def probe(_):
        try:
            item = app._nsapp.nsstatusitem
            menu = item.menu()
            print("STATUSITEM title:", item.title())
            print("MENU attached:", menu is not None)
            if menu is not None:
                print("MENU items:", menu.numberOfItems())
                for i in range(menu.numberOfItems()):
                    print("  -", menu.itemAtIndex_(i).title() or "(separator)")
        except Exception as e:
            print("PROBE ERROR:", type(e).__name__, e)
        finally:
            sys.stdout.flush()
            rumps.quit_application()

    timer = rumps.Timer(probe, 3)
    timer.start()
    app.run()
    return 0


def cmd_run() -> int:
    from . import config as config_mod
    from . import permissions
    from .app import Orchestrator
    from .menubar import SottoApp

    try:
        cfg = config_mod.load_config()
    except Exception as e:
        print(f"Ошибка в конфиге {config_mod.CONFIG_PATH}: {e}", file=sys.stderr)
        return 1

    _, missing = permissions.report()
    if missing:
        print("⚠️  Не все права macOS выданы — Sotto может не работать полностью:")
        for line in missing:
            print(f"  • {line}")
        print("Подробнее: python -m sotto check")

    orch = Orchestrator(cfg)
    try:
        orch.start()
    except ValueError as e:
        print(f"Ошибка конфига: {e}", file=sys.stderr)
        return 1

    print(f"Sotto запущен. Триггер: {cfg['trigger_key']} (зажать — говорить — отпустить).")
    SottoApp(orch).run()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="sotto", description="Локальная push-to-talk диктовка")
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "check", "transcribe", "probe-menu", "install-autostart", "uninstall-autostart"],
    )
    parser.add_argument("path", nargs="?", help="аудиофайл для команды transcribe")
    args = parser.parse_args()

    if args.command == "check":
        return cmd_check()
    if args.command == "probe-menu":
        return cmd_probe_menu()
    if args.command == "transcribe":
        if not args.path:
            parser.error("transcribe требует путь к аудиофайлу")
        return cmd_transcribe(args.path)
    if args.command == "install-autostart":
        from . import launchagent

        print(launchagent.install())
        return 0
    if args.command == "uninstall-autostart":
        from . import launchagent

        print(launchagent.uninstall())
        return 0
    return cmd_run()


if __name__ == "__main__":
    sys.exit(main())
