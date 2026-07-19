"""VC Brain pipeline CLI.

    python -m vcbrain.pipeline samples/parsely_ai --mock -o output/
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from .claims import extract_claims
from .evidence import run_evidence
from .ingest import load_submission
from .memo import write_dashboard, write_json
from .models import EvidenceStatus
from .scoring import score


def _log(stage: str, msg: str) -> None:
    print(f"[{stage:>8}] {msg}", flush=True)


def run(folder: str, out_dir: str, mock: bool) -> int:
    from . import llm

    t0 = time.time()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Decide mock-vs-live ONCE, up front, and never lie about it in the logs.
    live_requested = not mock
    mock = mock or not llm.live_available()
    if live_requested and mock:
        _log("config", "WARNING: live mode requested but ANTHROPIC_API_KEY is not "
                       "set — running MOCK (deterministic extractors, no web search)")
    mode = "mock" if mock else "live"
    _log("config", f"engine mode: "
                   + ("mock — deterministic only" if mock
                      else "live — Claude extraction + web-search adjudication"))

    _log("ingest", f"loading submission from {folder}")
    sub = load_submission(folder)
    _log("ingest", f"{sub.company} — {len(sub.source_files)} files, "
                   f"{len(sub.revenue_series)} months of revenue data")

    _log("claims", "extracting checkable assertions"
                   + (" (mock extractor)" if mock else " (Claude)"))
    claims = extract_claims(sub, mock=mock)
    _log("claims", f"{len(claims)} claims extracted")

    _log("evidence", "auditing every claim (recompute → cross-doc → external)")
    evidence = run_evidence(
        claims, sub, mock=mock,
        on_adjudicate=lambda n: _log(
            "evidence", f"{n} claim(s) beyond deterministic reach — "
                        f"adjudicating with Claude + web search"),
        on_note=lambda m: _log("evidence", f"NOTE: {m}"),
    )
    for e in evidence:
        mark = {"verified": "✓", "corroborated": "◐",
                "unsupported": "!", "contradicted": "✕"}[e.status.value]
        _log("evidence", f"  {mark} {e.claim_id} {e.status.value:<12} — {e.method}")

    n_bad = sum(1 for e in evidence if e.status == EvidenceStatus.CONTRADICTED)
    _log("evidence", f"done: {n_bad} contradiction(s) found")

    _log("scoring", "running deterministic scoring model")
    decision = score(sub, claims, evidence)
    _log("scoring", f"composite {decision.composite}/100 "
                    f"(integrity ×{decision.integrity_multiplier}) → {decision.decision}")

    json_path = out / "decision.json"
    html_path = out / "dashboard.html"
    write_json(json_path, sub, claims, evidence, decision, mode=mode)
    write_dashboard(html_path, sub, claims, evidence, decision, mode=mode)
    _log("memo", f"wrote {json_path} and {html_path}")
    _log("done", f"pipeline completed in {time.time() - t0:.2f}s")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="[%(name)s] %(levelname)s %(message)s")
    p = argparse.ArgumentParser(prog="vcbrain", description="VC Brain diligence pipeline")
    p.add_argument("submission", help="path to the submission folder")
    p.add_argument("-o", "--out", default="output", help="output directory")
    p.add_argument("--mock", action="store_true",
                   help="run without API calls (deterministic extractors)")
    args = p.parse_args()
    return run(args.submission, args.out, args.mock)


if __name__ == "__main__":
    sys.exit(main())
