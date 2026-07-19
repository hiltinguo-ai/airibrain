"""VC Brain web UI.

    python -m vcbrain.webapp          # http://localhost:5001

Single-page flow: paste (or load the sample) founder materials → hit RUN AUDIT →
watch the evidence engine stream claim-by-claim → the decision dashboard appears
inline. Mock mode by default (zero API calls, demo-safe); live Claude extraction
kicks in automatically when ANTHROPIC_API_KEY is set and "live" is checked.
"""

from __future__ import annotations

import csv
import io
import json
import os
import queue
import tempfile
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path

from flask import Flask, Response, abort, jsonify, request

from .claims import extract_claims
from .evidence import run_evidence
from .memo import write_dashboard
from .models import EvidenceStatus, Submission
from .scoring import score

app = Flask(__name__)
RUNS: "OrderedDict[str, dict]" = OrderedDict()
MAX_RUNS = 50  # bounded memory: oldest runs evicted
HEARTBEAT_S = 10  # SSE keepalive so proxies don't kill long live runs

_SAMPLE_DIR = Path(__file__).resolve().parent.parent / "samples" / "parsely_ai"


def _load_sample() -> dict:
    return {
        "company": json.loads((_SAMPLE_DIR / "company.json").read_text()),
        "deck": (_SAMPLE_DIR / "deck.md").read_text(),
        "metrics": (_SAMPLE_DIR / "metrics.json").read_text(),
        "revenue": (_SAMPLE_DIR / "revenue.csv").read_text(),
        "qa": (_SAMPLE_DIR / "qa.json").read_text(),
    }


def _build_submission(p: dict) -> Submission:
    revenue = []
    if p.get("revenue", "").strip():
        for row in csv.DictReader(io.StringIO(p["revenue"].strip())):
            revenue.append({"month": row["month"].strip(), "revenue": float(row["revenue"])})
    return Submission(
        company=p.get("company", "Unnamed startup").strip() or "Unnamed startup",
        one_liner=p.get("one_liner", "").strip(),
        ask=p.get("ask", "$100,000").strip() or "$100,000",
        deck_text=p.get("deck", ""),
        metrics=json.loads(p["metrics"]) if p.get("metrics", "").strip() else {},
        revenue_series=revenue,
        qa=json.loads(p["qa"]) if p.get("qa", "").strip() else {},
        source_files=["deck (pasted)", "metrics (pasted)", "revenue series (pasted)"],
    )


def _sample_payload() -> dict:
    s = _load_sample()
    return {
        "company": s["company"]["company"],
        "one_liner": s["company"]["one_liner"],
        "ask": s["company"]["ask"],
        "deck": s["deck"], "metrics": s["metrics"],
        "revenue": s["revenue"], "qa": s["qa"],
    }


@app.post("/api/run")
def api_run() -> Response:
    if request.content_type and "multipart/form-data" in request.content_type:
        if request.form.get("use_sample") == "1":
            payload = _sample_payload()
        else:
            from .uploads import parse_files

            payload = parse_files(request.files.getlist("files"))
            for k in ("company", "one_liner", "ask"):
                v = request.form.get(k, "").strip()
                if v:
                    payload[k] = v
    else:
        payload = request.get_json(force=True)
    run_id = uuid.uuid4().hex[:12]
    RUNS[run_id] = {"payload": payload, "html": None}
    while len(RUNS) > MAX_RUNS:
        RUNS.popitem(last=False)
    return jsonify({"run_id": run_id})


@app.get("/api/stream/<run_id>")
def api_stream(run_id: str) -> Response:
    if run_id not in RUNS:
        abort(404)

    q: "queue.Queue[str | None]" = queue.Queue()

    def emit(event: str, data: dict) -> None:
        q.put(f"event: {event}\ndata: {json.dumps(data)}\n\n")

    def worker() -> None:
        from .llm import live_available

        payload = RUNS[run_id]["payload"]
        mock = not live_available()
        pace = 0.28 if mock else 0.0  # cosmetic pacing only when instant anyway
        try:
            emit("log", {"stage": "config",
                         "msg": "engine: " + ("mock — deterministic only"
                                              if mock else "live — Claude + web search")})
            emit("log", {"stage": "ingest", "msg": "normalizing submitted materials…"})
            sub = _build_submission(payload)
            time.sleep(pace)
            emit("log", {"stage": "ingest",
                         "msg": f"{sub.company} — {len(sub.revenue_series)} months of revenue data, "
                                f"{len(sub.metrics)} headline metrics"})

            emit("log", {"stage": "claims",
                         "msg": "extracting checkable assertions"
                                + (" (deterministic extractor)" if mock else " (Claude)")})
            claims = extract_claims(sub, mock=mock)
            time.sleep(pace)
            emit("log", {"stage": "claims",
                         "msg": f"{len(claims)} claims extracted — every one will be audited"})

            emit("log", {"stage": "evidence",
                         "msg": "auditing: recompute → cross-document → "
                                + ("curated reference (mock)…" if mock
                                   else "Claude + live web search…")})
            evidence = run_evidence(
                claims, sub, mock=mock,
                on_adjudicate=lambda n: emit("log", {
                    "stage": "evidence",
                    "msg": f"{n} claim(s) beyond deterministic reach — "
                           f"adjudicating with Claude + web search (this is the slow part)"}),
                on_note=lambda m: emit("log", {"stage": "evidence", "msg": f"NOTE: {m}"}),
            )
            by_id = {c.id: c for c in claims}
            for e in evidence:
                time.sleep(pace)
                emit("claim", {"id": e.claim_id, "status": e.status.value,
                               "text": by_id[e.claim_id].text, "method": e.method})
            n_bad = sum(1 for e in evidence if e.status == EvidenceStatus.CONTRADICTED)
            emit("log", {"stage": "evidence", "msg": f"audit complete — {n_bad} contradiction(s) found"})

            emit("log", {"stage": "scoring", "msg": "running deterministic scoring model (no LLM in the loop)"})
            decision = score(sub, claims, evidence)
            time.sleep(pace * 2)
            emit("log", {"stage": "scoring",
                         "msg": f"composite {decision.composite}/100 · integrity ×{decision.integrity_multiplier}"})

            with tempfile.TemporaryDirectory() as td:
                out = Path(td) / "dashboard.html"
                write_dashboard(out, sub, claims, evidence, decision,
                                mode="mock" if mock else "live")
                RUNS[run_id]["html"] = out.read_text()

            from dataclasses import asdict
            RUNS[run_id]["data"] = {
                "company": sub.company,
                "one_liner": sub.one_liner,
                "ask": sub.ask,
                "mode": "mock" if mock else "live",
                "decision": asdict(decision),
                "claims": [c.to_dict() for c in claims],
                "evidence": [e.to_dict() for e in evidence],
                "revenue_series": sub.revenue_series,
                "memo_url": f"/result/{run_id}",
            }

            emit("done", {"url": f"/result/{run_id}",
                          "data_url": f"/api/result/{run_id}",
                          "decision": decision.decision,
                          "composite": decision.composite})
        except Exception as exc:  # surface errors to the UI rather than dying silently
            emit("fail", {"msg": f"{type(exc).__name__}: {exc}"})
        finally:
            q.put(None)  # end of stream

    threading.Thread(target=worker, daemon=True).start()

    def gen():
        # Heartbeat comments keep the connection alive through long LLM calls.
        while True:
            try:
                item = q.get(timeout=HEARTBEAT_S)
            except queue.Empty:
                yield ": ping\n\n"
                continue
            if item is None:
                return
            yield item

    return Response(gen(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/result/<run_id>")
def api_result(run_id: str) -> Response:
    run = RUNS.get(run_id)
    if not run or not run.get("data"):
        abort(404)
    return jsonify(run["data"])


@app.get("/result/<run_id>")
def result(run_id: str) -> Response:
    run = RUNS.get(run_id)
    if not run or not run["html"]:
        abort(404)
    return Response(run["html"], mimetype="text/html")


@app.get("/")
def index() -> Response:
    from ._page import PAGE
    from .llm import live_available

    sample = _load_sample()
    live = live_available()
    mode = ("LIVE · claude + web search" if live
            else "MOCK · deterministic (set ANTHROPIC_API_KEY)")
    page = (PAGE.replace("__SAMPLE__", json.dumps(sample))
                .replace("__MODE__", mode)
                .replace("__LEDCLASS__", "led-live" if live else "led-mock"))
    return Response(page, mimetype="text/html")


def main() -> None:
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")), threaded=True)


if __name__ == "__main__":
    main()
