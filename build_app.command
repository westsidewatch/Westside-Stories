#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Westside Stories 1.1 — Build macOS App ==="
echo
echo "Production pipeline: Local ASR → Chinese church context → Doré proofreading → shadow evidence → optional burn-in"
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
echo "驗證 1.1 release imports..."
PYTHONPATH="app" "$VPY" -c "import main_v2, dore_proofreader, church_language_context, subtitle_style, dore_subtitle.pipeline_bridge, dore_subtitle.shadow_archive, dore_subtitle.suspicion_gate; print('release imports: ok')"

echo
echo "執行中文教會語境 release gate..."
PYTHONPATH="app" "$VPY" tests/test_church_language_release_gate.py

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
  --hidden-import "dore_proofreader" \
  --hidden-import "church_language_context" \
  --hidden-import "subtitle_style" \
  --hidden-import "dore_subtitle.pipeline_bridge" \
  --hidden-import "dore_subtitle.shadow_archive" \
  --hidden-import "dore_subtitle.suspicion_gate" \
  "app/main_v2.py"

echo
echo "完成："
echo "$(pwd)/dist/Westside Stories.app"
open "dist"
echo
read -n 1 -s -r -p "按任意鍵關閉..."
echo
