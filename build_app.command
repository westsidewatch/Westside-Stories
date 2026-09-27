#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Westside Stories 1.2 — Build macOS App ==="
echo
echo "Production pipeline: media/URL → Chinese ASR → Church Corrector → SRT → optional burn-in"
echo

if [ -x "/opt/homebrew/bin/python3" ]; then PY="/opt/homebrew/bin/python3"; else PY="$(command -v python3 || true)"; fi
if [ -z "$PY" ]; then echo "找不到 Python 3。請先執行：brew install python"; exit 1; fi

VENV=".build-venv"
if [ ! -x "$VENV/bin/python" ]; then "$PY" -m venv "$VENV"; fi
VPY="$VENV/bin/python"

"$VPY" -m pip install --upgrade pip pyinstaller pyside6 pypinyin rapidfuzz
if ! command -v yt-dlp >/dev/null 2>&1; then
  echo "正在安裝 URL 音軌工具 yt-dlp…"
  if command -v brew >/dev/null 2>&1; then brew install yt-dlp; else "$VPY" -m pip install -U "yt-dlp[default]"; fi
fi

PYTHONPATH="app" "$VPY" -c "import main_v2, media_url, subtitle_style, church_corrector, asr.church_context, dore_subtitle.dynamic_context, dore_subtitle.context_retriever, dore_subtitle.contextual_paraformer, dore_subtitle.local_memory; print('release imports: ok')"
PYTHONPATH="app" "$VPY" tests/test_church_corrector.py
PYTHONPATH="app" "$VPY" tests/test_asr_v2_release.py

rm -rf build dist "Westside Stories.spec"
"$VPY" -m PyInstaller \
  --noconfirm --clean --windowed --onedir \
  --name "Westside Stories" \
  --add-data "app/assets:assets" \
  --add-data "app/context:context" \
  --paths "app" \
  --hidden-import "media_url" \
  --hidden-import "subtitle_style" \
  --hidden-import "church_corrector" \
  --hidden-import "asr.church_context" \
  --hidden-import "dore_subtitle.dynamic_context" \
  --hidden-import "dore_subtitle.context_retriever" \
  --hidden-import "dore_subtitle.contextual_paraformer" \
  --hidden-import "dore_subtitle.local_memory" \
  "app/main_v2.py"

echo "完成：$(pwd)/dist/Westside Stories.app"
open "dist"
