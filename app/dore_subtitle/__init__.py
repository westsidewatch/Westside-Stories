"""Doré Subtitle Pack v2 safety boundary.

The package is optional. Westside Stories must remain fully functional when
this package is absent, disabled, outdated, or rejected by its regression gate.
"""
from .evidence_packet import EvidencePacket, WordEvidence
from .correction_ledger import CorrectionRecord
from .regression_gate import RegressionResult, release_allowed

__all__ = ["EvidencePacket", "WordEvidence", "CorrectionRecord", "RegressionResult", "release_allowed"]
