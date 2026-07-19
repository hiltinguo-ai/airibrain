"""Stage 4 - Scoring model.

Live mode: Claude acts as the investment-committee partner - reads the full
evidence table + hard metrics and returns weighted dimension scores, an integrity
multiplier, a composite, and a decision band with written rationale.

Mock mode (or LLM failure): falls back to a deterministic pure-Python scorer so
demos and tests never die mid-run. Same Decision shape either way.
"""

from __future__ import annotations

import json
import logging

from .models import (
    Claim,
    ClaimType,
    Decision,
    DimensionScore,
    Evidence,
    EvidenceStatus,
    Submission,
)

logger = logging.getLogger("vcbrain.scoring")

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

_DIM_ORDER = ("team", "traction", "market", "product", "economics", "integrity")

SCORING_PROMPT = """You are the investment-committee partner inside AiriBrain, an \
evidence-backed diligence engine. A deterministic layer has already audited every \
founder claim (recompute / cross-doc / web search). Your job is to SCORE the deal \
like a skeptical early-stage IC - using the evidence table as ground truth, not the \
founder's marketing.

Rules:
- Contradicted claims are severe: a founder who inflates one number likely inflates others.
- Unsupported claims are open diligence items, not free passes.
- Hard metrics (margin, LTV/CAC, runway, recomputed growth) matter.
- Be concrete. Every rationale line must name a claim ID or a metric.
- Decision bands (mandatory):
    composite ≥ 70 → INVEST (check_size 100000)
    50 ≤ composite < 70 → INVEST_WITH_CONDITIONS (check_size 100000)
    composite < 50 → DECLINE (check_size 0)
- integrity_multiplier must be between 0.70 and 1.00 inclusive.
- Return exactly these six dimensions with the given weights: team 0.20, traction 0.25, \
market 0.15, product 0.10, economics 0.20, integrity 0.10.
- composite should equal (approximately) Σ(dimension_score × weight) × integrity_multiplier.

=== COMPANY ===
{company} - {one_liner}
Ask: {ask}

=== HEADLINE METRICS ===
{metrics}

=== REVENUE SERIES ===
{revenue}

=== EVIDENCE TABLE ===
{evidence_block}

Return ONLY JSON:
{{"dimensions": [{{"dimension": "team|traction|market|product|economics|integrity",
  "score": 0-100,
  "rationale": ["...", "..."]}}],
 "integrity_multiplier": 0.70-1.00,
 "composite": 0-100,
 "decision": "INVEST|INVEST_WITH_CONDITIONS|DECLINE",
 "check_size": 0|100000,
 "conditions": ["founder questions / open items"],
 "key_risks": ["..."],
 "summary": "2-3 sentence IC memo summary"}}
Every dimension listed above must appear exactly once.
"""


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
        return 50.0, [f"No checkable {dim} claims - neutral 50."]
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
    change the verdict - only the *fraction* of unverifiable claims does."""
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
        rat.append(f"Contradicted: {c.id.split('-')[0]} - {table[c.id].detail}")
    return score, rat


def _clamp(x: float) -> float:
    return max(0.0, min(100.0, x))


def _sid(cid: str) -> str:
    return cid.split("-")[0]


def _band(composite: float) -> tuple[str, int]:
    if composite >= 70:
        return "INVEST", 100_000
    if composite >= 50:
        return "INVEST_WITH_CONDITIONS", 100_000
    return "DECLINE", 0


def score_deterministic(sub: Submission, claims: list[Claim],
                        evidence: list[Evidence]) -> Decision:
    """Rule-based scorer - used in mock mode and as live-mode fallback."""
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
    decision, check = _band(composite)

    conditions = [
        f"[{_sid(c.id)}] Resolve: {c.text} - {table[c.id].detail}"
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
        f"{len(claims)} claims audited - {verified} verified, {corr} corroborated, "
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


def _evidence_block(claims: list[Claim], evidence: list[Evidence]) -> str:
    by_id = {e.claim_id: e for e in evidence}
    lines = []
    for c in claims:
        e = by_id[c.id]
        stated = f" | stated={e.stated_value} found={e.computed_value}" if e.stated_value else ""
        cites = ""
        if e.citations:
            cites = " | sources=" + "; ".join(
                (x.get("url") or "") for x in e.citations[:3] if x.get("url"))
        lines.append(
            f"{c.id} [{c.claim_type.value}] {e.status.value.upper()} "
            f"(conf {e.confidence:.2f}) via {e.method}\n"
            f"  claim: {c.text}\n"
            f"  evidence: {e.detail}{stated}{cites}"
        )
    return "\n".join(lines)


def _score_live(sub: Submission, claims: list[Claim],
                evidence: list[Evidence]) -> Decision:
    from .llm import complete_json

    revenue = "\n".join(
        f"{p['month']}: ${p['revenue']:,.0f}" for p in sub.revenue_series
    ) or "(none)"
    payload, _ = complete_json(
        SCORING_PROMPT.format(
            company=sub.company,
            one_liner=sub.one_liner,
            ask=sub.ask,
            metrics=json.dumps(sub.metrics, indent=2),
            revenue=revenue,
            evidence_block=_evidence_block(claims, evidence),
        ),
        web_search=False,
        max_tokens=4000,
    )

    by_dim = {}
    for d in payload.get("dimensions") or []:
        name = str(d.get("dimension", "")).lower().strip()
        if name not in WEIGHTS:
            continue
        rats = d.get("rationale") or []
        if isinstance(rats, str):
            rats = [rats]
        by_dim[name] = DimensionScore(
            dimension=name,
            score=_clamp(float(d.get("score", 50))),
            weight=WEIGHTS[name],
            rationale=[str(r) for r in rats] or [f"LLM score for {name}."],
        )
    missing = [n for n in _DIM_ORDER if n not in by_dim]
    if missing:
        raise RuntimeError(f"LLM scorer omitted dimensions: {missing}")

    dims = [by_dim[n] for n in _DIM_ORDER]
    integ = by_dim["integrity"].score
    multiplier = float(payload.get("integrity_multiplier",
                                   0.70 + 0.30 * (integ / 100.0)))
    multiplier = max(0.70, min(1.00, multiplier))

    composite = payload.get("composite")
    if composite is None:
        composite = sum(d.score * d.weight for d in dims) * multiplier
    composite = round(_clamp(float(composite)), 1)

    # Bands are enforced in code so the model can't invent a fourth outcome.
    decision, check = _band(composite)
    raw_decision = str(payload.get("decision", "")).upper().replace(" ", "_")
    if raw_decision in ("INVEST", "INVEST_WITH_CONDITIONS", "DECLINE") and raw_decision != decision:
        logger.info("LLM decision %s overridden by band rules → %s (composite %.1f)",
                    raw_decision, decision, composite)

    conditions = [str(x) for x in (payload.get("conditions") or []) if str(x).strip()]
    risks = [str(x) for x in (payload.get("key_risks") or []) if str(x).strip()]
    summary = str(payload.get("summary") or "").strip() or (
        f"LLM IC score {composite}/100 (integrity ×{multiplier:.2f}) → "
        f"{decision.replace('_', ' ')}."
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


def score(sub: Submission, claims: list[Claim], evidence: list[Evidence],
          mock: bool = False) -> Decision:
    """Score the deal. Live → Claude IC partner; mock / no key / failure → deterministic."""
    from .llm import live_available

    if mock or not live_available():
        return score_deterministic(sub, claims, evidence)
    try:
        return _score_live(sub, claims, evidence)
    except Exception as exc:
        logger.warning("LLM scoring failed (%s) - falling back to deterministic scorer", exc)
        return score_deterministic(sub, claims, evidence)
