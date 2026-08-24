#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Westside Stories 1.0 — Build macOS App ==="
echo
echo "Production pipeline: Whisper → Doré proofreader → SRT → optional burn-in"
echo

if [ -x "/opt/homebrew/bin/python3" ]; then
  PY="/opt/homebrew/bin/python3"
else
  PY="$(command -v python3 || true)"
fi

if [ -z "$PY" ]; then
  echo "找不到 Python 3。請先執行：brew install python"
  read -n 1 -s -r -p "按任意鍵結束..."
  exit 1
fi

VENV=".build-venv"
if [ ! -x "$VENV/bin/python" ]; then
  "$PY" -m venv "$VENV"
fi

VPY="$VENV/bin/python"

echo "安裝 / 更新 PyInstaller 與 PySide6..."
"$VPY" -m pip install --upgrade pip pyinstaller pyside6

echo
echo "開始打包..."
rm -rf build dist "Westside Stories.spec"

"$VPY" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onedir \
  --name "Westside Stories" \
  --add-data "app/assets:assets" \
  --paths "app" \
  "app/main_dore.py"

echo
echo "完成："
echo "$(pwd)/dist/Westside Stories.app"
open "dist"
echo
read -n 1 -s -r -p "按任意鍵關閉..."
echo
