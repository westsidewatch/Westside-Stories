"""Auditable minimal-patch ledger for Doré subtitle corrections."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Literal

Decision = Literal["KEEP", "CORRECT", "UNCERTAIN"]
Mode = Literal["SHADOW", "SUGGEST", "TRUSTED_AUTO"]

@dataclass(frozen=True)
class CorrectionRecord:
    segment_id: str
    decision: Decision
    original: str
    candidate: str = ""
    start_offset: int | None = None
    end_offset: int | None = None
    correction_class: str = ""
    evidence: tuple[str, ...] = ()
    negative_evidence: tuple[str, ...] = ()
    confidence: float = 0.0
    pack_version: str = ""
    mode: Mode = "SHADOW"
    created_at: str = ""

    def normalized(self) -> "CorrectionRecord":
        stamp = self.created_at or datetime.now(timezone.utc).isoformat()
        return CorrectionRecord(**{**asdict(self), "created_at": stamp})

    def may_apply(self) -> bool:
        return (
            self.decision == "CORRECT"
            and self.mode == "TRUSTED_AUTO"
            and bool(self.candidate)
            and self.start_offset is not None
            and self.end_offset is not None
            and self.end_offset > self.start_offset
            and bool(self.evidence)
            and not self.negative_evidence
        )
