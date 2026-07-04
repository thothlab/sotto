"""CLI: python -m sotto [run|check|install-autostart|uninstall-autostart]."""

import argparse
import sys


def cmd_check() -> int:
    from . import permissions

    statuses, missing = permissions.report()
    names = {
        "microphone": "Microphone",
        "input_monitoring": "Input Monitoring",
        "accessibility": "Accessibility",
    }
    marks = {"granted": "✅", "denied": "❌", "unknown": "❓"}
    print("Права macOS (выдаются терминалу, из которого запущен Sotto):")
    for key, st in statuses.items():
        print(f"  {marks[st]} {names[key]}: {st}")
    if missing:
        print("\nЧто сделать:")
        for line in missing:
            print(f"  • {line}")
        print("\nПосле изменения галочек перезапустите терминал.")
    else:
        print("\nВсе права на месте.")
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
        choices=["run", "check", "install-autostart", "uninstall-autostart"],
    )
    args = parser.parse_args()

    if args.command == "check":
        return cmd_check()
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
