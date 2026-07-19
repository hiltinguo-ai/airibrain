"""LLM adjudication - the second line of the evidence engine.

The deterministic verifiers rule on everything they can recompute or cross-check.
Whatever exits that stage as UNSUPPORTED goes to Claude for real judgment: the
full data room plus live web search, a skeptical-analyst prompt, and a verdict
per claim with citations. Deterministic findings are never overturned here -
recomputed numbers outrank model opinion by design.
"""

from __future__ import annotations

import json
import logging

from .llm import complete_json

logger = logging.getLogger("vcbrain.adjudicate")
from .models import Claim, Evidence, EvidenceStatus, Submission

ADJUDICATION_PROMPT = """You are the evidence adjudicator inside an investment \
diligence engine. A deterministic layer has already recomputed every number it \
could from the founder's raw data; the claims below are the ones it could NOT \
rule on. Your job is to judge each one like a skeptical diligence analyst.

Rules:
- Use web search for claims checkable against the outside world (market sizes, \
competitors, team backgrounds, certifications, app-store presence). Search \
before judging; cite what you find.
- "verified" = independent evidence confirms it. "corroborated" = partial or \
secondary support. "contradicted" = evidence disagrees. "unsupported" = you \
genuinely found nothing either way - this is a legitimate answer; do NOT guess.
- Founder materials are marketing. Absence of evidence for a bold claim is a \
finding, not an inconvenience.
- Keep each detail to 1-3 sentences, concrete, naming what you checked.

=== FOUNDER DATA ROOM ===
{data_room}

=== CLAIMS TO ADJUDICATE ===
{claims_block}

Return ONLY a JSON object:
{{"verdicts": [{{"claim_id": "C01",
  "status": "verified|corroborated|unsupported|contradicted",
  "detail": "what you checked and what you found",
  "confidence": 0.0-1.0,
  "sources": ["url", ...]}}]}}
Every claim listed above must appear exactly once in verdicts."""


def _data_room(sub: Submission) -> str:
    return (
        f"Company: {sub.company} - {sub.one_liner}\nAsk: {sub.ask}\n\n"
        f"--- DECK ---\n{sub.deck_text}\n\n"
        f"--- HEADLINE METRICS ---\n{json.dumps(sub.metrics, indent=2)}\n\n"
        f"--- REVENUE SERIES ---\n"
        + "\n".join(f"{p['month']}: ${p['revenue']:,.0f}" for p in sub.revenue_series)
        + f"\n\n--- FOUNDER Q&A ---\n{json.dumps(sub.qa, indent=2)}"
    )


def adjudicate(pending: list[Claim], sub: Submission) -> dict[str, Evidence]:
    """Batch-judge the claims deterministic verifiers couldn't rule on.

    Returns {claim_id: Evidence} - partial acceptance: whatever valid verdicts
    came back are kept, missing ones are the caller's problem (they stay
    unsupported). Raises only on transport/parse failure of the whole call.
    """
    if not pending:
        return {}

    claims_block = "\n".join(
        f"{c.id} [{c.claim_type.value}] ({c.provenance}): {c.text}" for c in pending
    )
    payload, all_citations = complete_json(
        ADJUDICATION_PROMPT.format(data_room=_data_room(sub), claims_block=claims_block),
        web_search=True,
    )
    title_by_url = {c["url"]: c["title"] for c in all_citations}

    out: dict[str, Evidence] = {}
    wanted = {c.id for c in pending}
    for v in payload.get("verdicts", []):
        cid = v.get("claim_id")
        if cid not in wanted:
            continue
        try:
            status = EvidenceStatus(v["status"])
        except (KeyError, ValueError):
            status = EvidenceStatus.UNSUPPORTED
        sources = v.get("sources") or []
        citations = [{"url": u, "title": title_by_url.get(u, u)} for u in sources]
        out[cid] = Evidence(
            claim_id=cid,
            status=status,
            method="adjudicated by Claude + web search",
            detail=str(v.get("detail", "")).strip() or "No detail returned.",
            confidence=max(0.0, min(1.0, float(v.get("confidence", 0.6)))),
            citations=citations,
        )
    missing = wanted - set(out)
    if missing:
        logger.warning("adjudicator omitted verdicts for: %s", sorted(missing))
    return out
