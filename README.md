# AiriBrain — Evidence-Backed $100K Decisions in 24 Hours

**Hackathon Challenge 2: “The VC Brain” (Maschmeyer Group)**

AiriBrain turns early-stage diligence into a fast, auditable workflow. A founder
uploads their data room; the system extracts every checkable claim, verifies it
against the numbers and the open web, scores the deal the way an investment
committee would, and produces a memo where every conclusion traces back to a
source.

Our starting point as an accounting and tax AI team: **slow VC decisions are
usually a verification problem, not a reasoning problem.** AiriBrain is built
like an audit engine — not a deck summarizer.

Brand assets: [`branding/`](branding/) (icon + wordmark, SVG and PNG).

## What makes it different

Most AI investment tools summarize the pitch. The pitch is marketing, so the
summary inherits every exaggeration. AiriBrain treats the materials as
**claims to verify**:

1. Pull out every checkable assertion — revenue, growth, retention, market size, team.
2. Grade each one: verified, corroborated, unsupported, or contradicted.
3. Score the deal with Claude as an IC partner, grounded in that evidence table —
   with clear decision bands (invest / invest with conditions / decline).
4. Ship a memo you can challenge line by line: claim → evidence → impact on the score.

That’s what “evidence-backed” means in practice.

## How it works

```
 founder data room (deck, financials, Q&A)
        │
        ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1. INGEST    │ → │ 2. CLAIMS    │ → │ 3. EVIDENCE  │ → │ 4. SCORING   │ → │ 5. MEMO      │
 │ load the     │   │ extract      │   │ verify each  │   │ IC score     │   │ decision +   │
 │ data room    │   │ checkable    │   │ claim        │   │ + rationale  │   │ audit trail  │
 │              │   │ assertions   │   │              │   │              │   │              │
 └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘   └──────────────┘
```

**1. Ingest** — Accepts a data room: pitch deck (PDF or text), financials
(Excel / CSV), headline metrics, and optional founder Q&A. Everything is
normalized into one working set for the rest of the pipeline.

**2. Claim extraction** — Identifies every assertion that evidence could confirm
or refute, and tags it by theme (traction, market, team, product, financials,
competition), including where it came from in the materials.

**3. Evidence engine** — Two layers:
- **Numbers first:** recompute what’s recomputable (e.g. claimed MoM growth vs. the
  submitted revenue series) and cross-check stated figures against the founder’s
  own metrics. Arithmetic is never overturned later.
- **Open-world second (live mode):** claims the rules can’t settle — market size,
  competitors, credentials — go to Claude with live web search. Each verdict
  includes reasoning and citations. “Unsupported” is a valid answer.

**4. Scoring** — Claude scores the deal as an investment-committee partner using
the audited evidence and hard metrics across six dimensions (team, traction,
market, product, economics, integrity). Decision bands are fixed in product
logic: ≥70 invest, 50–70 invest with conditions, &lt;50 decline. Offline / mock
mode uses a rule-based fallback so the product still runs without an API key.

**5. Memo** — Produces a machine-readable decision record and a single-file
dashboard: verdict, score breakdown, claim-by-claim evidence, risks, and
follow-up questions for the founder.

## The 24-hour promise

The automated pass runs in minutes. The challenge’s 24-hour window is for the
human layer — founder follow-ups, reference calls, and partner sign-off.
AiriBrain’s job is to finish the mechanical verification first so those hours
are spent on judgment, not spreadsheet archaeology.

## Run it

```bash
pip install -r requirements.txt

# Web app (recommended for demo)
python -m vcbrain.webapp          # → http://localhost:5001

# CLI — offline / mock (no API key)
python -m vcbrain.pipeline samples/parsely_ai --mock -o output/

# CLI — live (Claude + web search + IC scoring)
export ANTHROPIC_API_KEY=sk-ant-...
python -m vcbrain.pipeline samples/parsely_ai -o output/

# Tests
pytest tests/ -q
```

Outputs: `output/decision.json` and `output/dashboard.html`.
Sample data rooms live under [`samples/`](samples/).
