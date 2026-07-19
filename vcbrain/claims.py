"""Stage 2 - Claim extraction.

Live mode: Claude extracts and types every checkable assertion in the materials.
Mock mode: a deterministic rule-based extractor (keyword + number heuristics) so the
full pipeline demos with zero API calls. Same output shape either way.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re

from .models import Claim, ClaimType, Submission

logger = logging.getLogger("vcbrain.claims")


def _cid(index: int, text: str) -> str:
    """Stable claim ID: position + content hash, so the same claim keeps the
    same ID across runs even when neighbors shift."""
    h = hashlib.sha1(text.strip().lower().encode()).hexdigest()[:4]
    return f"C{index:02d}-{h}"

EXTRACTION_PROMPT = """You are the claim-extraction stage of an investment diligence engine.

Below are a startup's raw materials. Extract every CHECKABLE assertion the founder makes.
A checkable assertion is one that evidence could confirm or refute (numbers, rankings,
customer counts, credentials, market sizes, competitive statements). Skip pure vision
statements.

For each claim return JSON: {{"claims": [{{"text": "...verbatim or tightly paraphrased...",
"claim_type": "traction|market|team|product|financial|competition",
"provenance": "which document/section it came from",
"quantitative": true|false}}]}}

Return ONLY the JSON object.

=== MATERIALS ===
{materials}
"""

_TYPE_KEYWORDS: list[tuple[ClaimType, list[str]]] = [
    (ClaimType.TEAM, ["founder", "ex-", "phd", "cpa", "previously", "team", "years at"]),
    (ClaimType.MARKET, ["tam", "market", "$b", "billion", "sam", "som"]),
    (ClaimType.COMPETITION, ["competitor", "only", "first", "no one else", "alternative"]),
    (ClaimType.FINANCIAL, ["margin", "burn", "runway", "cac", "ltv", "arpa", "gross"]),
    (ClaimType.PRODUCT, ["accuracy", "latency", "uptime", "integration", "soc 2", "patent"]),
    (ClaimType.TRACTION, ["mrr", "arr", "customers", "growth", "retention", "churn",
                          "pilots", "waitlist", "logos", "revenue"]),
]


def _classify(line: str) -> ClaimType:
    low = line.lower()
    for ctype, words in _TYPE_KEYWORDS:
        if any(w in low for w in words):
            return ctype
    return ClaimType.PRODUCT


def _candidate_lines(deck_text: str):
    """Yield (section, line) candidates. Markdown bullets are preferred; for
    non-bullet text (e.g. extracted from a PDF deck) fall back to any short
    line that carries a figure or strong assertion."""
    section = "deck"
    bullets = []
    plain = []
    for raw in deck_text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            section = line.lstrip("# ").strip() or section
            continue
        if line.startswith(("- ", "* ", "• ")):
            bullets.append((section, line.lstrip("-*• ").strip()))
        elif 15 <= len(line) <= 200:
            # PDF extraction often glues the bullet glyph to the text
            plain.append((section, line.lstrip("-–—•*· ").rstrip(".") + "."))
    return bullets if bullets else plain


def _mock_extract(sub: Submission) -> list[Claim]:
    """Deterministic extractor: any deck bullet (or, for PDF-extracted text,
    any short assertive line) containing a figure or a strong keyword becomes
    a claim; Q&A answers with figures too."""
    claims: list[Claim] = []
    for section, text in _candidate_lines(sub.deck_text):
        has_number = bool(re.search(r"\d", text))
        strong = any(w in text.lower() for w in ("only", "first", "no ", "never", "every"))
        if not (has_number or strong):
            continue
        claims.append(
            Claim(
                id=_cid(len(claims) + 1, text),
                text=text,
                claim_type=_classify(text),
                provenance=f"deck · {section}",
                quantitative=has_number,
            )
        )
    for q, a in sub.qa.items():
        if re.search(r"\d", a):
            claims.append(
                Claim(
                    id=_cid(len(claims) + 1, a),
                    text=a.strip(),
                    claim_type=_classify(a),
                    provenance=f"founder Q&A · “{q}”",
                    quantitative=True,
                )
            )
    return claims


def _live_extract(sub: Submission) -> list[Claim]:
    from .llm import complete_json

    materials = (
        f"Company: {sub.company} - {sub.one_liner}\nAsk: {sub.ask}\n\n"
        f"--- DECK ---\n{sub.deck_text}\n\n"
        f"--- HEADLINE METRICS ---\n{json.dumps(sub.metrics, indent=2)}\n\n"
        f"--- FOUNDER Q&A ---\n{json.dumps(sub.qa, indent=2)}"
    )
    payload, _ = complete_json(EXTRACTION_PROMPT.format(materials=materials))
    claims: list[Claim] = []
    for c in payload.get("claims") or []:
        if not isinstance(c, dict):
            continue
        text = str(c.get("text") or "").strip()
        if not text:
            continue
        try:
            ctype = ClaimType(str(c.get("claim_type", "")).strip().lower())
        except ValueError:
            ctype = _classify(text)  # off-enum value from the model → heuristic
            logger.warning("off-enum claim_type %r - classified as %s",
                           c.get("claim_type"), ctype.value)
        claims.append(
            Claim(
                id=_cid(len(claims) + 1, text),
                text=text,
                claim_type=ctype,
                provenance=str(c.get("provenance") or "materials"),
                quantitative=bool(c.get("quantitative", True)),
            )
        )
    if not claims:
        logger.warning("live extraction returned no usable claims - "
                       "falling back to deterministic extractor")
        return _mock_extract(sub)
    return claims


def extract_claims(sub: Submission, mock: bool = False) -> list[Claim]:
    from .llm import live_available

    if mock or not live_available():
        return _mock_extract(sub)
    return _live_extract(sub)
