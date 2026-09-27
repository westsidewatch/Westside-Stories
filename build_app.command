#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Westside Stories 1.1 — Build macOS App ==="
echo
echo "Production pipeline: Local ASR → dynamic context → phonetic evidence → Doré ambiguity resolution → local memory → shadow evidence → optional burn-in"
echo

if [ -x "/opt/homebrew/bin/python3" ]; then PY="/opt/homebrew/bin/python3"; else PY="$(command -v python3 || true)"; fi
if [ -z "$PY" ]; then echo "找不到 Python 3。請先執行：brew install python"; exit 1; fi

VENV=".build-venv"
if [ ! -x "$VENV/bin/python" ]; then "$PY" -m venv "$VENV"; fi
VPY="$VENV/bin/python"

"$VPY" -m pip install --upgrade pip pyinstaller pyside6 pypinyin

PYTHONPATH="app" "$VPY" -c "import main_v2, dore_proofreader, subtitle_style, dore_subtitle.dynamic_context, dore_subtitle.context_retriever, dore_subtitle.phonetic_rescorer, dore_subtitle.ambiguity_resolver, dore_subtitle.asr_benchmark, dore_subtitle.runtime_ab, dore_subtitle.contextual_paraformer, dore_subtitle.local_context_adapter, dore_subtitle.local_memory, dore_subtitle.pipeline_bridge, dore_subtitle.shadow_archive, dore_subtitle.suspicion_gate; print('release imports: ok')"
PYTHONPATH="app" "$VPY" tests/test_dore_output_contract.py
PYTHONPATH="app" "$VPY" tests/test_regression_corpus.py
PYTHONPATH="app" "$VPY" tests/test_local_context_adapter.py
PYTHONPATH="app" "$VPY" tests/test_context_retriever.py
PYTHONPATH="app" "$VPY" tests/test_phonetic_rescorer.py
PYTHONPATH="app" "$VPY" tests/test_ambiguity_resolver.py
PYTHONPATH="app" "$VPY" tests/test_asr_benchmark_gate.py
PYTHONPATH="app" "$VPY" tests/test_runtime_ab.py

rm -rf build dist "Westside Stories.spec"
"$VPY" -m PyInstaller \
  --noconfirm --clean --windowed --onedir \
  --name "Westside Stories" \
  --add-data "app/assets:assets" \
  --paths "app" \
  --hidden-import "dore_proofreader" \
  --hidden-import "subtitle_style" \
  --hidden-import "dore_subtitle.dynamic_context" \
  --hidden-import "dore_subtitle.context_retriever" \
  --hidden-import "dore_subtitle.phonetic_rescorer" \
  --hidden-import "dore_subtitle.ambiguity_resolver" \
  --hidden-import "dore_subtitle.asr_benchmark" \
  --hidden-import "dore_subtitle.runtime_ab" \
  --hidden-import "dore_subtitle.contextual_paraformer" \
  --hidden-import "dore_subtitle.local_context_adapter" \
  --hidden-import "dore_subtitle.local_memory" \
  --hidden-import "dore_subtitle.pipeline_bridge" \
  --hidden-import "dore_subtitle.shadow_archive" \
  --hidden-import "dore_subtitle.suspicion_gate" \
  "app/main_v2.py"

echo "完成：$(pwd)/dist/Westside Stories.app"
open "dist"
