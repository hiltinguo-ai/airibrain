"""Stage 4 — Deterministic scoring model. Pure Python, zero LLM.

Given the claim/evidence table plus the metrics file, produce six dimension
scores, an integrity multiplier, a composite, and a decision band. Every
adjustment is recorded as a rationale line so the memo can show its work.
"""

from __future__ import annotations

from .models import (
    Claim,
    ClaimType,
    Decision,
    DimensionScore,
    Evidence,
    EvidenceStatus,
    Submission,
)

WEIGHTS = {
    "team": 0.20,
    "traction": 0.25,
    "market": 0.15,
    "product": 0.10,
    "economics": 0.20,
    "integrity": 0.10,
}

_STATUS_POINTS = {
    EvidenceStatus.VERIFIED: 100.0,
    EvidenceStatus.CORROBORATED: 75.0,
    EvidenceStatus.UNSUPPORTED: 45.0,
    EvidenceStatus.CONTRADICTED: 0.0,
}

_DIM_FOR_TYPE = {
    ClaimType.TEAM: "team",
    ClaimType.TRACTION: "traction",
    ClaimType.MARKET: "market",
    ClaimType.PRODUCT: "product",
    ClaimType.FINANCIAL: "economics",
    ClaimType.COMPETITION: "market",
}


def _evidence_base(dim: str, claims: list[Claim], table: dict[str, Evidence]) -> tuple[float, list[str]]:
    """Average evidence points for claims mapped to this dimension."""
    pts, rat = [], []
    for c in claims:
        if _DIM_FOR_TYPE[c.claim_type] != dim:
            continue
        ev = table[c.id]
        p = _STATUS_POINTS[ev.status]
        pts.append(p)
        rat.append(f"{c.id.split('-')[0]} {ev.status.value} ({p:.0f} pts): {c.text[:80]}")
    if not pts:
        return 50.0, [f"No checkable {dim} claims — neutral 50."]
    return sum(pts) / len(pts), rat


def _economics_adjustments(sub: Submission) -> tuple[float, list[str]]:
    """Rule-based adjustments from hard metrics (points delta, rationale)."""
    delta, rat = 0.0, []
    m = sub.metrics
    gm = m.get("gross_margin_pct")
    if gm is not None:
        if gm >= 70:
            delta += 10
            rat.append(f"Gross margin {gm}% ≥ 70% (software-grade): +10.")
        elif gm < 50:
            delta -= 10
            rat.append(f"Gross margin {gm}% < 50%: −10.")
    ltv, cac = m.get("ltv_usd"), m.get("cac_usd")
    if ltv and cac:
        ratio = ltv / cac
        if ratio >= 3:
            delta += 10
            rat.append(f"LTV/CAC {ratio:.1f}x ≥ 3x: +10.")
        elif ratio < 1.5:
            delta -= 10
            rat.append(f"LTV/CAC {ratio:.1f}x < 1.5x: −10.")
    runway = m.get("runway_months")
    if runway is not None and runway < 6:
        delta -= 10
        rat.append(f"Runway {runway} months < 6: −10 (bridge risk).")
    return delta, rat


def _traction_adjustments(sub: Submission) -> tuple[float, list[str]]:
    delta, rat = 0.0, []
    revs = [p["revenue"] for p in sub.revenue_series]
    if len(revs) >= 2 and revs[0] > 0:
        n = len(revs) - 1
        mom = ((revs[-1] / revs[0]) ** (1 / n) - 1) * 100
        if mom >= 15:
            delta += 10
            rat.append(f"Recomputed MoM growth {mom:.1f}% ≥ 15%: +10.")
        elif mom < 5:
            delta -= 10
            rat.append(f"Recomputed MoM growth {mom:.1f}% < 5%: −10.")
    ret = sub.metrics.get("logo_retention_pct")
    if ret is not None:
        if ret >= 90:
            delta += 5
            rat.append(f"Logo retention {ret}% ≥ 90%: +5.")
        elif ret < 80:
            delta -= 10
            rat.append(f"Logo retention {ret}% < 80%: −10.")
    return delta, rat


def _integrity(claims: list[Claim], table: dict[str, Evidence]) -> tuple[float, list[str]]:
    """Contradictions are a per-incident penalty (a caught lie is a caught lie).
    The unsupported penalty is normalized by claim count, so a chattier
    extractor that surfaces more unverifiable claims doesn't mechanically
    change the verdict — only the *fraction* of unverifiable claims does."""
    n = max(1, len(claims))
    contradicted = [c for c in claims if table[c.id].status == EvidenceStatus.CONTRADICTED]
    unsupported = [c for c in claims if table[c.id].status == EvidenceStatus.UNSUPPORTED]
    unsupported_penalty = 50.0 * (len(unsupported) / n)
    score = max(0.0, 100.0 - 35.0 * len(contradicted) - unsupported_penalty)
    rat = [
        f"{n} claims audited: {len(contradicted)} contradicted (−35 each), "
        f"{len(unsupported)}/{n} unsupported (−{unsupported_penalty:.1f}, "
        f"normalized by claim count)."
    ]
    for c in contradicted:
        rat.append(f"Contradicted: {c.id.split('-')[0]} — {table[c.id].detail}")
    return score, rat


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def score(sub: Submission, claims: list[Claim], evidence: list[Evidence]) -> Decision:
    table = {e.claim_id: e for e in evidence}
    dims: list[DimensionScore] = []

    for dim in ("team", "traction", "market", "product", "economics"):
        base, rat = _evidence_base(dim, claims, table)
        if dim == "economics":
            d, r2 = _economics_adjustments(sub)
            base, rat = base + d, rat + r2
        if dim == "traction":
            d, r2 = _traction_adjustments(sub)
            base, rat = base + d, rat + r2
        dims.append(DimensionScore(dim, _clamp(base), WEIGHTS[dim], rat))

    integ, integ_rat = _integrity(claims, table)
    dims.append(DimensionScore("integrity", _clamp(integ), WEIGHTS["integrity"], integ_rat))

    weighted = sum(d.score * d.weight for d in dims)
    # Integrity also acts as a trust multiplier on everything else:
    # a founder who inflates one number inflates others.
    multiplier = 0.70 + 0.30 * (integ / 100.0)
    composite = round(weighted * multiplier, 1)

    # Bands: ≥70 invest · 50–70 invest with conditions · <50 DECLINE (no check).
    if composite >= 70:
        decision, check = "INVEST", 100_000
    elif composite >= 50:
        decision, check = "INVEST_WITH_CONDITIONS", 100_000
    else:
        decision, check = "DECLINE", 0

    def _sid(cid: str) -> str:  # display form: "C01-70a5" → "C01"
        return cid.split("-")[0]

    conditions = [
        f"[{_sid(c.id)}] Resolve: {c.text} — {table[c.id].detail}"
        for c in claims
        if table[c.id].status in (EvidenceStatus.CONTRADICTED, EvidenceStatus.UNSUPPORTED)
    ]
    risks = [
        f"{_sid(c.id)} contradicted by evidence: {table[c.id].detail}"
        for c in claims
        if table[c.id].status == EvidenceStatus.CONTRADICTED
    ]
    if sub.metrics.get("runway_months", 99) < 9:
        risks.append(f"Short runway: {sub.metrics['runway_months']} months.")

    verified = sum(1 for e in evidence if e.status == EvidenceStatus.VERIFIED)
    corr = sum(1 for e in evidence if e.status == EvidenceStatus.CORROBORATED)
    summary = (
        f"{len(claims)} claims audited — {verified} verified, {corr} corroborated, "
        f"{len(conditions)} open items. Composite {composite}/100 after a "
        f"{multiplier:.2f}x integrity multiplier → {decision.replace('_', ' ')}."
    )

    return Decision(
        company=sub.company,
        composite=composite,
        integrity_multiplier=round(multiplier, 2),
        decision=decision,
        check_size=check,
        dimensions=dims,
        conditions=conditions,
        key_risks=risks,
        summary=summary,
    )
