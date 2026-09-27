from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


main_v2 = (ROOT / "app" / "main_v2.py").read_text(encoding="utf-8")
adapter = (ROOT / "app" / "asr" / "funasr_paraformer_adapter.py").read_text(encoding="utf-8")
context = (ROOT / "app" / "asr" / "church_context.py").read_text(encoding="utf-8")
build = (ROOT / "build_app.command").read_text(encoding="utf-8")

# Syntax gate.
for name, source in (("main_v2", main_v2), ("adapter", adapter), ("context", context)):
    ast.parse(source, filename=name)

# Production routing gate: contextual Chinese ASR must be primary and Whisper fallback only.
require('if self.language in ("zh", "auto")' in main_v2, "Chinese/auto production routing missing")
require("transcribe_challenger" in main_v2, "contextual Paraformer not called by production")
require("result_json.write_text" in main_v2 and '"segments": segments' in main_v2, "Paraformer segments do not reach production result")
require("_original_transcribe(self, vpy, result_json)" in main_v2, "safe fallback missing")

# Mature upstream stack gate.
for token in ('model="paraformer-zh"', 'vad_model="fsmn-vad"', 'punc_model="ct-punc"'):
    require(token in adapter, f"missing upstream component: {token}")
require('kwargs["hotword"] = hotword' in adapter, "context is not passed into upstream recognition")

# Expandable corpus gate.
require('glob("*.txt")' in context, "expandable context corpus discovery missing")
require("load_context_terms" in main_v2, "production does not load context corpus")
require("corpus_terms=corpus" in main_v2, "corpus does not reach context retrieval")

# Packaging gate.
require("Westside Stories 1.2" in build, "build is not marked 1.2")
require('asr.church_context' in build, "ASR v2 context module is not packaged")

print("ASR v2 release gate: PASS")
