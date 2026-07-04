#!/bin/zsh
# Собирает standalone dist/Sotto.app и dist/Sotto-<version>-arm64.zip.
set -e
cd "$(dirname "$0")/.."

PYBIN=./.venv/bin
VERSION=$(grep '__version__' sotto/__init__.py | cut -d'"' -f2)

echo "==> Sotto v$VERSION: иконка…"
$PYBIN/python scripts/make_icon.py

echo "==> PyInstaller…"
$PYBIN/pip install -q pyinstaller
$PYBIN/pyinstaller --noconfirm --clean packaging/sotto.spec

echo "==> Подпись (ad-hoc)…"
codesign --force --deep --sign - dist/Sotto.app

echo "==> Архив…"
ZIP="dist/Sotto-$VERSION-arm64.zip"
rm -f "$ZIP"
ditto -c -k --keepParent dist/Sotto.app "$ZIP"

echo ""
echo "Готово:"
du -sh dist/Sotto.app "$ZIP"
