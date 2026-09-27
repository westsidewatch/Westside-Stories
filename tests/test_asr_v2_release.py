from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


main_v2 = (ROOT / "app" / "main_v2.py").read_text(encoding="utf-8")
build = (ROOT / "build_app.command").read_text(encoding="utf-8")
corrector = (ROOT / "app" / "church_corrector.py").read_text(encoding="utf-8")

for name, source in (("main_v2", main_v2), ("corrector", corrector)):
    ast.parse(source, filename=name)

# Production must use the already-working recognizer, then correct text locally.
require("return _original_transcribe(self, vpy, result_json)" in main_v2,
        "stable production ASR delegation missing")
require("apply_to_srt_text" in main_v2,
        "Church Corrector is not applied after SRT generation")
require("transcribe_challenger" not in main_v2 and "funasr" not in main_v2.lower(),
        "broken FunASR runtime is still on the production path")

# First-use local correction gate.
for token in ("慕道", "恩召"):
    require(token in corrector, f"missing shipped church correction target: {token}")
require("load_terms" in corrector and "rapidfuzz" in corrector and "pypinyin" in corrector,
        "local glossary/fuzzy correction stack missing")

# Packaging gate.
require("Westside Stories 1.2" in build, "build is not marked 1.2")
require("church_corrector" in build, "Church Corrector is not packaged")
require("test_church_corrector.py" in build, "Church Corrector first-use gate is not run")
require("rapidfuzz" in build and "pypinyin" in build, "Church Corrector fuzzy dependencies are not installed")

print("ASR + Church Corrector release gate: PASS")
