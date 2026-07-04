#!/bin/zsh
# Установка Sotto: venv + зависимости + проверка прав.
set -e
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
echo "==> Python: $($PY --version) ($(which $PY))"

if [ ! -d .venv ]; then
  echo "==> Создаю venv…"
  "$PY" -m venv .venv
fi

echo "==> Ставлю зависимости…"
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt

echo "==> Проверяю права macOS…"
./.venv/bin/python -m sotto check || true

echo ""
echo "Готово. Запуск:          ./run.sh"
echo "Автозапуск:              ./.venv/bin/python -m sotto install-autostart"
echo "Модель (~1.6 ГБ) скачается при первом запуске, дальше полный офлайн."
