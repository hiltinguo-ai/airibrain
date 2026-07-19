# VC Brain — Live Run Findings & Engineering Review

**Date:** 2026-07-18
**Scope:** First live (non-mock) end-to-end run of the pipeline against the Anthropic API, plus a code review of all modules. Intended as a handoff for design/engineering improvements.

---

## 1. What was run

```bash
python3 -m vcbrain.pipeline samples/parsely_ai -o output/
```

- **Live run:** completed in 58.5s. Claude extracted **20 claims** (vs 15 from the mock extractor); 7 went to LLM adjudication with web search. Result: **composite 43.1/100, integrity ×0.70 → PASS**.
- **Mock run (baseline):** 15 claims, 1 contradiction, composite 56.4 → INVEST_WITH_CONDITIONS.
- The live run is *stricter* than the mock: web search refuted a competitive claim the mock could only flag as unverifiable, and more unsupported claims dragged the integrity multiplier from 0.82 to 0.70. This flipped the decision from INVEST_WITH_CONDITIONS to PASS — a good demo story (the engine gets tougher when it can actually check).

### Contradictions found (live)

| ID | Claim | How caught |
|----|-------|-----------|
| C06 | "Revenue growing 40% MoM since launch" | Deterministic recompute: geometric mean of the submitted 8-month `revenue.csv` is **21.0% MoM** |
| C12 | "The only platform that automates both bookkeeping and tax filing end-to-end for SMB firms" | Web search found TaxGPT, Botkeeper, Zeni and others doing both |

Outputs: `output/decision.json`, `output/dashboard.html`. Test suite: 8/8 passing (all mock-path).

---

## 2. Bugs found during the live run

### 2.1 Silent mock fallback that *claims* to be live (highest priority)

When `ANTHROPIC_API_KEY` is unset and `--mock` is not passed, the pipeline logs `extracting checkable assertions (Claude)` but actually runs the mock extractor. This happened in practice: an intermediate run printed "(Claude)", finished in 0.00s, and produced mock results — easy to mistake for a real live run.

Cause: the log message in `pipeline.py` keys off the `--mock` flag, but `extract_claims()` in `claims.py` independently falls back to mock when `live_available()` is False:

```116:121:vcbrain/claims.py
def extract_claims(sub: Submission, mock: bool = False) -> list[Claim]:
    from .llm import live_available

    if mock or not live_available():
        return _mock_extract(sub)
    return _live_extract(sub)
```

**Fix:** decide mock-vs-live once in `pipeline.run()` (e.g. `mock = mock or not llm.live_available()`), log which mode was actually chosen, and consider a hard error (or at least a loud warning) when the user asked for live but no key exists.

### 2.2 Curated mock reference table leaks into live runs

`_verify_external()` in `evidence.py` compares **any** market-size claim against a hardcoded `EXTERNAL_REFERENCE` table for the *SMB accounting software market* — and it runs before LLM adjudication in live mode too. In the live run, C11 was marked "corroborated — Grand View Research 2025 (curated ref table)" even though this is sample-specific data. For any company outside SMB accounting, market claims would be scored against an irrelevant $28.4B reference.

**Fix:** in live mode, skip the curated table (or use it only for the bundled sample) and route market claims to the web-search adjudicator, which already handles them well.

### 2.3 Unvalidated LLM output can crash the pipeline

`_live_extract()` does `ClaimType(c["claim_type"])` with no guard — one off-enum value from the model (e.g. `"go-to-market"`) raises `ValueError` and kills the run. The adjudicator has a fallback for this exact situation; the extractor should too. Also `payload["claims"]` (KeyError) and `c["text"]` are unguarded.

### 2.4 Adjudication failures are swallowed with zero diagnostics

```231:235:vcbrain/evidence.py
    try:
        from .adjudicate import adjudicate
        verdicts = adjudicate(pending, sub)
    except Exception:
        return table  # graceful degradation: heuristic evidence stands
```

Graceful degradation is right for a demo, but the bare `except Exception` with no logging means a bad API key, a rate limit, or the "adjudicator omitted verdicts" RuntimeError all look identical to success. At minimum log the exception; ideally surface "adjudication skipped: <reason>" in the pipeline log and dashboard footer.

Related: `adjudicate()` raises if *any* claim is missing a verdict, discarding all the good verdicts in the batch. Partial acceptance (keep what came back, leave the rest unsupported) would be more robust and cheaper.

---

## 3. Engineering improvements (prioritized)

1. **Key/config handling.** Support a `.env` file (python-dotenv) so keys never travel through chat/shell history. The key used for this run was pasted into a chat session and **must be rotated**.
2. **Number matching is brittle.** `_first_number()` grabs the first numeral in the claim text. "Top 50 accounting firms use us, retention 95%" would compare *50* against the retention metric. Extract the number adjacent to the matched keyword, or have the extractor return `stated_value` as a structured field (it's an LLM call anyway — ask for `{metric, value, unit}`).
3. **Cross-doc keyword routing is fragile.** `_METRIC_KEYS` matches "customers" before "cac" only by list order, and "margin" matches both gross and net claims. Same fix as above: structured extraction beats regex-on-prose.
4. **Claim IDs are unstable across runs** (C05 in one run is C06 in the next), which makes runs incomparable and breaks any cached/linked artifacts. Consider a content hash suffix or ordering by document position.
5. **Retry/timeout on the API path.** `complete_json()` retries once on JSON-parse failure but not on transport errors (429/529/timeouts). The 58s run had a single point of failure per call. Add `max_retries`/timeout via the Anthropic client options.
6. **Cost/latency visibility.** Log token usage from `msg.usage` per call; the adjudication call with web search is the expensive one (6 searches allowed).
7. **Web app (`webapp.py`):** `RUNS` dict grows unbounded (no eviction); SSE generator does the whole pipeline inside the request thread with cosmetic `time.sleep()`s — a live run will hold the connection ~60s with no heartbeat, which some proxies kill. Emit a keepalive or stream real progress from `run_evidence` (the `on_adjudicate` callback is already there; extend the pattern).
8. **Tests only cover the mock path.** `set_client_factory()` exists precisely to fake the client — add tests for `_live_extract` (bad enum, missing keys), `adjudicate` (missing verdicts, malformed JSON, citation mapping), and `complete_json` (retry path, `_extract_json` on nested braces in strings — note: `_extract_json` counts braces inside string literals and will mis-parse `{"a": "}"}`).
9. **Scoring nits (by design, but document them):** integrity is double-counted (10% weighted dimension *and* a 0.70–1.00 multiplier on everything); each unsupported claim costs 5 integrity points, so a chatty extractor that finds more unverifiable claims (as the live one did: 20 vs 15) mechanically lowers the score — extraction verbosity shouldn't change the verdict. Consider normalizing the unsupported penalty by claim count.

---

## 4. Design improvements (dashboard)

The dashboard is already solid: self-contained HTML, dark mode, status conveyed by icon+label not just color, rationale behind `<details>`. Suggested upgrades:

1. **Contradictions above the fold.** The two most important findings live in the middle of a 20-row table. Add a "Top findings" card right under the hero: contradicted claims with stated-vs-found deltas, then the decision conditions.
2. **Filter/sort the evidence table** by status (a row of clickable count-tiles would do it — the tiles already exist, make them filter buttons).
3. **Show the contradiction on the chart.** The revenue SVG is the *evidence* for C06 — annotate it with the claimed 40% trajectory as a ghost line vs the actual series. This is the single most persuasive visual the product can make.
4. **Citations need more affordance.** Live adjudication returns real URLs but they render as a tiny 11px "sources:" line. Give verified/contradicted external claims a visible source chip; cap of 4 is fine.
5. **Confidence is computed but never shown.** Each `Evidence` carries `confidence` — a small bar or percentage in the status column would communicate the deterministic-vs-LLM trust hierarchy the README sells.
6. **Mode banner.** Show prominently whether the memo was produced in mock or live mode (ties into bug 2.1); a memo that says "adjudicated by Claude + web search" vs "curated ref table" should be visually distinct.
7. **Web app iframe** is a fixed 1200px height — resize to content via `postMessage` or just link out.

---

## 5. What's verified working

- End-to-end live path: ingest → Claude claim extraction → deterministic verifiers → Claude + web-search adjudication → deterministic scoring → JSON + HTML memo.
- Web-search citations flow through to the dashboard (C12 shows its sources).
- Deterministic verifiers are never overturned by the LLM (C06 stayed contradicted).
- Graceful degradation: no key → mock; adjudication failure → heuristic evidence stands (modulo the logging gaps above).
- 8/8 unit tests pass; mock pipeline runs in <1s, live in ~60s.
