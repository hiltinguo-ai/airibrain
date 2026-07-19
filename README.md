# AiriBrain — Evidence-Backed $100K Decisions in 24 Hours

**Our entry for Hackathon Challenge 2, "The VC Brain" (sponsored by Maschmeyer Group)**

Logo & brand assets live in `branding/` (SVG + PNG, icon and full wordmark).

AiriBrain compresses weeks of early-stage diligence into a repeatable, auditable pipeline.
A founder submits their materials; the system extracts every checkable claim, hunts for
evidence, scores the deal across the dimensions a real IC debates, and produces a signed
invest/pass memo — with every number traced back to a source.

The core thesis (and our unfair advantage as an accounting & tax AI team): **the reason
VC decisions take weeks isn't reasoning speed — it's verification.** So VC Brain is built
like an audit engine, not a chatbot.

## Why this wins

Most "AI VC" demos are an LLM summarizing a pitch deck. That's a vibes machine — it
inherits every exaggeration in the deck. AiriBrain treats the deck as a set of **assertions
to be audited**:

1. Every quantitative claim is extracted and typed (revenue, growth, retention, market size, team).
2. Each claim gets an **evidence status**: `verified`, `corroborated`, `unsupported`, or `contradicted`.
3. Scoring is an **LLM IC partner** grounded in the evidence table — Claude weighs the audited
   but the final score comes from a transparent weighted model anyone can inspect.
4. The output memo shows its work: claim → evidence → adjustment. An associate (or the
   founder) can challenge any single line.

That's what "evidence-backed" actually means, and it's the difference between a demo and
an underwriting system.

## Pipeline architecture

```
 founder materials (deck text, metrics CSV, data room docs, URLs)
        │
        ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1. INGEST    │ → │ 2. CLAIMS    │ → │ 3. EVIDENCE  │ → │ 4. SCORING   │ → │ 5. MEMO      │
 │ normalize    │   │ extract &    │   │ verify each  │   │ deterministic│   │ decision +   │
 │ all inputs   │   │ type claims  │   │ claim, grade │   │ weighted     │   │ audit trail  │
 │ to one doc   │   │ (LLM)        │   │ (LLM + web + │   │ (LLM IC      │   │ (JSON + HTML │
 │ bundle       │   │              │   │ financial    │   │ partner;     │   │ dashboard)   │
 │              │   │              │   │ recompute)   │   │ mock=rules)  │   │              │
 └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

### Stage details

**1. Ingest** (`vcbrain/ingest.py`) — Accepts a submission folder: `deck.md` (or extracted
deck text), `metrics.json`/`metrics.csv`, optional `financials.csv`, founder Q&A. Normalizes
into a single `Submission` object. In a production build this stage also pulls Crunchbase /
LinkedIn / app-store / GitHub signals.

**2. Claim extraction** (`vcbrain/claims.py`) — LLM pass that pulls out every *checkable*
assertion and types it: `traction`, `market`, `team`, `product`, `financial`, `competition`.
Each claim records where it came from (provenance).

**3. Evidence engine** (`vcbrain/evidence.py` + `vcbrain/adjudicate.py`) — The heart of
the system, two lines of defense:
   - **Deterministic first** (never overturned): recompute what's recomputable — if the
     deck says "40% MoM growth" and the data room has the monthly revenue series, we
     recompute the CAGR ourselves (accounting-firm move: numbers are checked, not
     believed) — and cross-check every stated figure against the founder's own metrics.
   - **LLM adjudication second** (live mode): every claim the deterministic layer can't
     rule on goes to Claude in one batched call with the full data room and **live web
     search** — market sizes, competitor claims, team backgrounds, certifications. Each
     verdict comes back with a status, reasoning, and **source citations** that render
     in the memo. A skeptical-analyst prompt makes "unsupported" a legitimate answer, so
     the model doesn't bless what it can't check. If the call fails, heuristic evidence
     stands — the pipeline never dies mid-demo.
   Each claim exits with a status, a confidence grade, and (live) citations.

**4. Scoring model** (`vcbrain/scoring.py`) — **Claude as the IC partner** in live mode.
Given the audited evidence table + hard metrics, the model returns six weighted dimension
scores (team 20%, traction 25%, market 15%, product 10%, economics 20%, integrity 10%),
an integrity multiplier (0.70–1.00), a composite, conditions, key risks, and a written
summary. Decision bands are enforced in code (≥70 INVEST / 50–70 INVEST-WITH-CONDITIONS /
&lt;50 DECLINE) so the LLM cannot invent a fourth outcome. Mock mode (and LLM failure)
falls back to the original deterministic rule scorer — same `Decision` shape, so demos
and tests never die mid-run.

**5. Memo generator** (`vcbrain/memo.py`) — Emits `decision.json` (machine-readable, with the
full audit trail) and `dashboard.html` (single-file IC memo: decision, score breakdown,
claim-by-claim evidence table, risks, conditions).

## The 24-hour promise

The pipeline itself runs in **minutes**. The 24-hour window in the challenge is for the
human-in-the-loop layer: automated follow-up questions to the founder (generated in the memo
as "conditions"), reference calls, and partner sign-off. AiriBrain's job is to make the human
hours count by doing the 100% of mechanical verification up front.

## Running it

```bash
pip install -r requirements.txt

# Web UI (the demo): submit materials, watch the audit stream, get the memo inline.
python -m vcbrain.webapp          # → http://localhost:5001
# "Load sample — Parsely AI" pre-fills the form; "Run audit" does the rest.

# CLI, mock mode — full pipeline on the bundled sample startup, no API key needed:
python -m vcbrain.pipeline samples/parsely_ai --mock -o output/

# Live mode — set ANTHROPIC_API_KEY: Claude extracts the claims, and adjudicates
# everything the deterministic layer can't rule on, with live web search + citations:
export ANTHROPIC_API_KEY=sk-ant-...
python -m vcbrain.pipeline samples/parsely_ai -o output/

# Tests (includes a stubbed-client suite proving the live LLM path end-to-end):
pytest tests/ -q
```

Outputs land in `output/`: `decision.json` + `dashboard.html`.
