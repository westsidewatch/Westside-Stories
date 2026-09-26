"""Release gate for local Doré Subtitle Packs.

A pack may grow in shadow mode freely. Automatic correction is promoted only
when verified corpus results show no destructive corrections.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class RegressionResult:
    verified_items: int
    proposed_corrections: int
    true_corrections: int
    destructive_corrections: int
    missed_known_errors: int = 0

    @property
    def precision(self) -> float:
        return self.true_corrections / self.proposed_corrections if self.proposed_corrections else 1.0

    @property
    def destructive_rate(self) -> float:
        return self.destructive_corrections / self.proposed_corrections if self.proposed_corrections else 0.0


def release_allowed(result: RegressionResult, *, minimum_verified: int = 100, minimum_precision: float = .995) -> bool:
    """Conservative v2 contract: destructive auto-corrections block release."""
    return (
        result.verified_items >= minimum_verified
        and result.destructive_corrections == 0
        and result.precision >= minimum_precision
    )
