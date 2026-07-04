"""Точка входа PyInstaller-бандла: Sotto.app без аргументов = `sotto run`."""

import multiprocessing
import sys

# Обязательно до любых импортов sotto: multiprocessing (resource_tracker из
# huggingface_hub и т.п.) перезапускает frozen-бинарь со своими аргументами —
# без freeze_support() они падают в наш argparse.
multiprocessing.freeze_support()

from sotto.__main__ import main  # noqa: E402

if len(sys.argv) == 1:
    sys.argv.append("run")
sys.exit(main())
