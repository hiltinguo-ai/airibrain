"""Stage 3 - Evidence engine: audit every claim.

Verifier order (first one that can rule, rules):
  1. RECOMPUTE  - if the claim states a figure we can recompute from raw data
                  (e.g. MoM growth vs. the revenue.csv series), recompute it.
  2. CROSS-DOC  - compare stated figures against the founder's own metrics file.
  3. EXTERNAL   - market/competition claims checked against a reference table
                  (mock) or a web-search pass (live).
  4. Otherwise  - UNSUPPORTED.

This is the accounting-firm move: numbers are checked, not believed.
"""

from __future__ import annotations

import logging
import re

from .models import Claim, ClaimType, Evidence, EvidenceStatus, Submission

logger = logging.getLogger("vcbrain.evidence")

# Tolerance for "matches" when comparing stated vs computed figures.
REL_TOL = 0.10  # within 10% → verified; beyond 25% → contradicted
CONTRADICTION_TOL = 0.25

# Mock-mode external reference table (live mode swaps in web search).
EXTERNAL_REFERENCE: dict[str, dict] = {
    "smb accounting software market": {
        "value_usd_b": 28.4,
        "source": "Grand View Research 2025 (curated ref table)",
    },
    "us smb count": {
        "value_m": 33.2,
        "source": "SBA Office of Advocacy 2024 (curated ref table)",
    },
}


def _first_number(text: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def _number_near(text: str, words: list[str]) -> float | None:
    """The number closest to any of the keywords - so in
    'Top 50 firms use us, retention 95%' the retention check picks 95, not 50."""
    low = text.lower().replace(",", "")
    nums = [(m.start(), float(m.group(1)))
            for m in re.finditer(r"(\d+(?:\.\d+)?)", low)]
    if not nums:
        return None
    best_val, best_dist = None, float("inf")
    for w in words:
        for m in re.finditer(re.escape(w.lower()), low):
            anchor = (m.start() + m.end()) / 2
            for pos, val in nums:
                d = abs(pos - anchor)
                if d < best_dist:
                    best_dist, best_val = d, val
    return best_val if best_val is not None else nums[0][1]


def _rel_diff(stated: float, actual: float) -> float:
    if actual == 0:
        return float("inf")
    return abs(stated - actual) / abs(actual)


def _avg_mom_growth(series: list[dict]) -> float | None:
    revs = [p["revenue"] for p in series]
    if len(revs) < 2 or revs[0] <= 0:
        return None
    n = len(revs) - 1
    return ((revs[-1] / revs[0]) ** (1 / n) - 1) * 100


def _verify_growth(claim: Claim, sub: Submission) -> Evidence | None:
    """Recompute MoM growth claims against the raw revenue series."""
    low = claim.text.lower()
    if "mom" not in low and "month-over-month" not in low and "monthly growth" not in low:
        return None
    stated = _number_near(claim.text, ["mom", "month-over-month", "monthly growth", "%"])
    computed = _avg_mom_growth(sub.revenue_series)
    if stated is None or computed is None:
        return None
    diff = _rel_diff(stated, computed)
    if diff <= REL_TOL:
        status, verdict = EvidenceStatus.VERIFIED, "matches the raw revenue series"
    elif diff >= CONTRADICTION_TOL:
        status, verdict = EvidenceStatus.CONTRADICTED, "disagrees with the founder's own revenue series"
    else:
        status, verdict = EvidenceStatus.CORROBORATED, "roughly consistent with the revenue series"
    return Evidence(
        claim_id=claim.id,
        status=status,
        method="recomputed from revenue.csv",
        detail=(
            f"Deck states {stated:.0f}% MoM; geometric mean of the submitted "
            f"{len(sub.revenue_series)}-month revenue series computes to "
            f"{computed:.1f}% MoM - {verdict}."
        ),
        stated_value=f"{stated:.0f}% MoM",
        computed_value=f"{computed:.1f}% MoM",
        confidence=0.97,
    )


# metric-file keys → keywords that signal the claim is about that metric
_METRIC_KEYS: list[tuple[str, list[str], str]] = [
    ("mrr_usd", ["mrr"], "MRR"),
    ("paying_customers", ["paying customers", "customers"], "paying customers"),
    ("logo_retention_pct", ["retention"], "logo retention"),
    ("gross_margin_pct", ["gross margin", "margin"], "gross margin"),
    ("cac_usd", ["cac"], "CAC"),
    ("runway_months", ["runway"], "runway (months)"),
    ("pilots", ["pilots"], "pilots"),
]


def _verify_cross_doc(claim: Claim, sub: Submission) -> Evidence | None:
    low = claim.text.lower()
    for key, words, label in _METRIC_KEYS:
        if key not in sub.metrics or not any(w in low for w in words):
            continue
        if key == "gross_margin_pct" and "net margin" in low:
            continue  # don't score a net-margin claim against the gross figure
        stated = _number_near(claim.text, words)
        if stated is None:
            return None
        actual = float(sub.metrics[key])
        diff = _rel_diff(stated, actual)
        if diff <= REL_TOL:
            status = EvidenceStatus.VERIFIED
            verdict = "matches the metrics file"
        elif diff >= CONTRADICTION_TOL:
            status = EvidenceStatus.CONTRADICTED
            verdict = "disagrees with the metrics file"
        else:
            status = EvidenceStatus.CORROBORATED
            verdict = "close to the metrics file"
        return Evidence(
            claim_id=claim.id,
            status=status,
            method="cross-checked vs metrics.json",
            detail=(
                f"Deck states {label} ≈ {stated:g}; submitted metrics file reports "
                f"{actual:g} - {verdict}."
            ),
            stated_value=f"{stated:g}",
            computed_value=f"{actual:g}",
            confidence=0.9,
        )
    return None


def _verify_external(claim: Claim, sub: Submission) -> Evidence | None:
    if claim.claim_type not in (ClaimType.MARKET, ClaimType.COMPETITION):
        return None
    low = claim.text.lower()
    if claim.claim_type == ClaimType.MARKET:
        stated = _number_near(claim.text, ["tam", "market", "sam", "som"])
        ref = EXTERNAL_REFERENCE["smb accounting software market"]
        if stated is not None and ("tam" in low or "market" in low):
            diff = _rel_diff(stated, ref["value_usd_b"])
            if diff <= 0.2:
                status, verdict = EvidenceStatus.CORROBORATED, "in line with third-party estimates"
            elif diff >= 0.6:
                status, verdict = EvidenceStatus.CONTRADICTED, "far above third-party estimates"
            else:
                status, verdict = EvidenceStatus.UNSUPPORTED, "higher than third-party estimates; needs sourcing"
            return Evidence(
                claim_id=claim.id,
                status=status,
                method=f"external reference - {ref['source']}",
                detail=(
                    f"Claimed market size ${stated:g}B vs reference ${ref['value_usd_b']}B - {verdict}."
                ),
                stated_value=f"${stated:g}B",
                computed_value=f"${ref['value_usd_b']}B",
                confidence=0.7,
            )
    # Competition absolutes ("only", "first", "no one") are unverifiable in-window.
    if any(w in low for w in ("only", "first", "no one", "no direct")):
        return Evidence(
            claim_id=claim.id,
            status=EvidenceStatus.UNSUPPORTED,
            method="external scan",
            detail=(
                "Absolute competitive claim; a quick landscape scan cannot prove a "
                "negative. Flagged for the founder-question list."
            ),
            confidence=0.6,
        )
    return None


def _default(claim: Claim) -> Evidence:
    detail = (
        "Qualitative or externally-held claim; no in-window verification path. "
        "Routed to human follow-up (reference call / document request)."
    )
    return Evidence(
        claim_id=claim.id,
        status=EvidenceStatus.UNSUPPORTED,
        method="no automated verifier applicable",
        detail=detail,
        confidence=0.5,
    )


VERIFIERS = (_verify_growth, _verify_cross_doc, _verify_external)


def run_deterministic(claims: list[Claim], sub: Submission,
                      use_reference_table: bool = True) -> list[Evidence]:
    """First line: recompute → cross-doc → (mock only) curated reference.

    The curated EXTERNAL_REFERENCE table is sample-specific demo data; in live
    mode it is skipped so market/competition claims flow to the web-search
    adjudicator instead of being scored against an irrelevant reference.
    Claims nothing can rule on exit as UNSUPPORTED.
    """
    verifiers = (VERIFIERS if use_reference_table
                 else (_verify_growth, _verify_cross_doc))
    table: list[Evidence] = []
    for claim in claims:
        ev: Evidence | None = None
        for verifier in verifiers:
            ev = verifier(claim, sub)
            if ev is not None:
                break
        table.append(ev or _default(claim))
    return table


def run_evidence(claims: list[Claim], sub: Submission, mock: bool = False,
                 on_adjudicate=None, on_note=None) -> list[Evidence]:
    """Audit every claim.

    Deterministic verifiers rule first and are never overturned. In live mode,
    claims they left UNSUPPORTED are batch-adjudicated by Claude with web
    search (real judgments with citations). In mock mode - or if the LLM call
    fails - the heuristic evidence stands, so the pipeline never dies mid-demo,
    and the reason is logged and surfaced via `on_note(msg)`.

    `on_adjudicate(n_pending)` is an optional progress callback for UIs.
    """
    from . import llm

    if not mock and not llm.live_available():
        logger.warning("live evidence requested but no API key - mock path used")
        mock = True

    table = run_deterministic(claims, sub, use_reference_table=mock)
    if mock:
        return table

    by_id = {c.id: c for c in claims}
    pending = [by_id[e.claim_id] for e in table
               if e.status == EvidenceStatus.UNSUPPORTED]
    if not pending:
        return table
    if on_adjudicate:
        on_adjudicate(len(pending))
    try:
        from .adjudicate import adjudicate
        verdicts = adjudicate(pending, sub)
    except Exception as exc:
        msg = f"adjudication skipped ({type(exc).__name__}: {exc}) - heuristic evidence stands"
        logger.exception("adjudication failed")
        if on_note:
            on_note(msg)
        return table  # graceful degradation, now with a diagnosis
    missing = {c.id for c in pending} - set(verdicts)
    if missing:
        msg = f"adjudicator returned no verdict for {len(missing)} claim(s); they stay unsupported"
        logger.warning(msg)
        if on_note:
            on_note(msg)
    return [verdicts.get(e.claim_id, e) if e.status == EvidenceStatus.UNSUPPORTED
            else e for e in table]
