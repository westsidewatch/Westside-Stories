"""Conservative local recovery for common Chinese church/Bible ASR confusions.

This is a domain layer, not a general spelling rewriter. Rules require a known
church/Bible target and operate before remote Doré proofreading, so the app does
not depend on the endpoint noticing every homophone error.
"""
from __future__ import annotations

from church_language_context import vocabulary

# Seeded from observed ASR failure families. Keep this table conservative: each
# source must be a plausible speech-recognition confusion for a canonical domain
# target. Real failures become regression cases before release.
CONFUSION_TO_DOMAIN = {
    "西安堂": "錫安堂",
    "恩趙": "恩召",
}


def recover_domain_text(text: str) -> tuple[str, list[dict]]:
    corrected = text
    changes: list[dict] = []
    known = set(vocabulary())
    for source, target in CONFUSION_TO_DOMAIN.items():
        if source not in corrected or target not in known:
            continue
        corrected = corrected.replace(source, target)
        changes.append({"from": source, "to": target, "reason": "church-domain-asr-recovery"})
    return corrected, changes
