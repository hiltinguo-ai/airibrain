"""Shared data models for the VC Brain pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class ClaimType(str, Enum):
    TRACTION = "traction"
    MARKET = "market"
    TEAM = "team"
    PRODUCT = "product"
    FINANCIAL = "financial"
    COMPETITION = "competition"


class EvidenceStatus(str, Enum):
    VERIFIED = "verified"          # independently recomputed / confirmed
    CORROBORATED = "corroborated"  # supported by a second source, not recomputed
    UNSUPPORTED = "unsupported"    # no evidence either way
    CONTRADICTED = "contradicted"  # evidence disagrees with the claim


@dataclass
class Submission:
    """Normalized founder submission."""
    company: str
    one_liner: str
    ask: str
    deck_text: str
    metrics: dict[str, Any] = field(default_factory=dict)
    revenue_series: list[dict[str, Any]] = field(default_factory=list)  # [{month, revenue}]
    qa: dict[str, str] = field(default_factory=dict)
    source_files: list[str] = field(default_factory=list)


@dataclass
class Claim:
    id: str
    text: str                      # the assertion as stated by the founder
    claim_type: ClaimType
    provenance: str                # where in the materials it came from
    quantitative: bool = True

    def to_dict(self) -> dict:
        d = asdict(self)
        d["claim_type"] = self.claim_type.value
        return d


@dataclass
class Evidence:
    claim_id: str
    status: EvidenceStatus
    method: str                    # how it was checked (recomputed / cross-doc / external)
    detail: str                    # human-readable explanation
    stated_value: str | None = None
    computed_value: str | None = None
    confidence: float = 0.8        # verifier's own confidence 0..1
    citations: list[dict] = field(default_factory=list)  # [{url, title}]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["status"] = self.status.value
        return d


@dataclass
class DimensionScore:
    dimension: str
    score: float                   # 0..100
    weight: float
    rationale: list[str] = field(default_factory=list)


@dataclass
class Decision:
    company: str
    composite: float
    integrity_multiplier: float
    decision: str                  # INVEST / INVEST_WITH_CONDITIONS / PASS
    check_size: int
    dimensions: list[DimensionScore] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    key_risks: list[str] = field(default_factory=list)
    summary: str = ""
