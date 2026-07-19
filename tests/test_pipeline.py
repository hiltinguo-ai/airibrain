"""VC Brain test suite.

Covers: mock-mode regression, the LLM adjudication path via a stubbed Anthropic
client (extraction JSON, adjudication verdicts with web-search citations, JSON
retry, graceful degradation), and dashboard rendering with citations.

Run:  pytest tests/ -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vcbrain import llm  # noqa: E402
from vcbrain.claims import extract_claims  # noqa: E402
from vcbrain.evidence import run_deterministic, run_evidence  # noqa: E402
from vcbrain.ingest import load_submission  # noqa: E402
from vcbrain.memo import write_dashboard  # noqa: E402
from vcbrain.models import EvidenceStatus  # noqa: E402
from vcbrain.scoring import score, score_deterministic  # noqa: E402

SAMPLE = ROOT / "samples" / "parsely_ai"


@pytest.fixture
def sub():
    return load_submission(SAMPLE)


@pytest.fixture(autouse=True)
def reset_client_factory():
    yield
    llm.set_client_factory(None)


# ---------------------------------------------------------------- fake client

def _text_block(text):
    return SimpleNamespace(type="text", text=text, citations=None)


def _search_block(results):
    return SimpleNamespace(
        type="web_search_tool_result",
        content=[SimpleNamespace(url=u, title=t) for u, t in results],
    )


class FakeClient:
    """Stands in for anthropic.Anthropic; returns queued responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        blocks = self._responses.pop(0)
        return SimpleNamespace(content=blocks)


# ------------------------------------------------------------ mock-mode tests

def test_mock_pipeline_regression(sub):
    claims = extract_claims(sub, mock=True)
    assert len(claims) == 15
    evidence = run_evidence(claims, sub, mock=True)
    statuses = [e.status for e in evidence]
    assert statuses.count(EvidenceStatus.VERIFIED) == 7
    assert statuses.count(EvidenceStatus.CORROBORATED) == 2
    assert statuses.count(EvidenceStatus.CONTRADICTED) == 1
    decision = score(sub, claims, evidence, mock=True)
    assert decision.decision == "INVEST_WITH_CONDITIONS"
    assert decision.composite == 58.8
    assert decision.check_size == 100_000


def test_growth_contradiction_is_caught(sub):
    claims = extract_claims(sub, mock=True)
    evidence = {e.claim_id: e for e in run_deterministic(claims, sub)}
    bad = [c for c in claims if "40% MoM" in c.text]
    assert len(bad) == 1
    e = evidence[bad[0].id]
    assert e.status == EvidenceStatus.CONTRADICTED
    assert "21.0% MoM" in e.detail  # recomputed from the founder's own CSV


# ------------------------------------------------------------ live-path tests

def test_live_extraction_uses_llm(sub):
    payload = {"claims": [
        {"text": "Hit $45,000 MRR in June 2026", "claim_type": "traction",
         "provenance": "deck · Traction", "quantitative": True},
    ]}
    fake = FakeClient([[_text_block(json.dumps(payload))]])
    llm.set_client_factory(lambda: fake)
    claims = extract_claims(sub, mock=False)
    assert len(claims) == 1 and claims[0].id.startswith("C01-")
    assert "45,000" in fake.calls[0]["messages"][0]["content"]  # deck reached the model


def test_adjudication_replaces_unsupported_with_cited_verdicts(sub):
    claims = extract_claims(sub, mock=True)
    # live path skips the curated reference table → market claims join the pending set
    pending_ids = [e.claim_id
                   for e in run_deterministic(claims, sub, use_reference_table=False)
                   if e.status == EvidenceStatus.UNSUPPORTED]
    assert len(pending_ids) == 6

    verdicts = {"verdicts": [
        {"claim_id": cid, "status": "corroborated",
         "detail": "Confirmed via public sources.", "confidence": 0.8,
         "sources": ["https://example.com/ref"]}
        for cid in pending_ids
    ]}
    fake = FakeClient([[
        _search_block([("https://example.com/ref", "Example Reference")]),
        _text_block(json.dumps(verdicts)),
    ]])
    llm.set_client_factory(lambda: fake)

    evidence = run_evidence(claims, sub, mock=False)
    by_id = {e.claim_id: e for e in evidence}
    for cid in pending_ids:
        assert by_id[cid].status == EvidenceStatus.CORROBORATED
        assert by_id[cid].citations == [
            {"url": "https://example.com/ref", "title": "Example Reference"}]
        assert by_id[cid].method == "adjudicated by Claude + web search"
    # web search was enabled on the adjudication call
    assert fake.calls[0]["tools"][0]["type"].startswith("web_search")
    # deterministic findings untouched
    assert sum(1 for e in evidence if e.status == EvidenceStatus.CONTRADICTED) == 1


def test_adjudication_never_overturns_deterministic(sub):
    claims = extract_claims(sub, mock=True)
    contradicted = [e.claim_id
                    for e in run_deterministic(claims, sub, use_reference_table=False)
                    if e.status == EvidenceStatus.CONTRADICTED]
    pending = [e.claim_id
               for e in run_deterministic(claims, sub, use_reference_table=False)
               if e.status == EvidenceStatus.UNSUPPORTED]
    # model tries to bless everything, including the contradicted growth claim
    verdicts = {"verdicts": [
        {"claim_id": cid, "status": "verified", "detail": "ok", "confidence": 0.9}
        for cid in pending + contradicted
    ]}
    fake = FakeClient([[_text_block(json.dumps(verdicts))]])
    llm.set_client_factory(lambda: fake)
    evidence = {e.claim_id: e for e in run_evidence(claims, sub, mock=False)}
    assert evidence[contradicted[0]].status == EvidenceStatus.CONTRADICTED


def test_json_retry_then_success(sub):
    good = {"claims": [{"text": "5 pilots", "claim_type": "traction",
                        "provenance": "deck", "quantitative": True}]}
    fake = FakeClient([
        [_text_block("Sure! Here are the claims I found:")],   # no JSON → retry
        [_text_block(json.dumps(good))],
    ])
    llm.set_client_factory(lambda: fake)
    claims = extract_claims(sub, mock=False)
    assert len(fake.calls) == 2
    assert len(claims) == 1


def test_llm_failure_degrades_gracefully(sub):
    class ExplodingClient:
        def __init__(self):
            self.messages = SimpleNamespace(create=self._boom)

        def _boom(self, **kwargs):
            raise ConnectionError("network down")

    claims = extract_claims(sub, mock=True)
    llm.set_client_factory(ExplodingClient)
    notes = []
    evidence = run_evidence(claims, sub, mock=False,
                            on_note=notes.append)  # must not raise
    assert len(evidence) == len(claims)
    # no reference table in live mode → 6 unsupported survive the failed adjudication
    assert sum(1 for e in evidence if e.status == EvidenceStatus.UNSUPPORTED) == 6
    assert notes and "adjudication skipped" in notes[0]  # failure is diagnosed, not silent


# ------------------------------------------------------- report-driven fixes


def test_extract_json_ignores_braces_inside_strings():
    assert llm._extract_json('noise {"a": "}"} tail') == {"a": "}"}
    assert llm._extract_json('x {"a": {"b": "{"}, "c": 1}') == {"a": {"b": "{"}, "c": 1}


def test_number_near_picks_keyword_adjacent_number(sub):
    from vcbrain.evidence import _number_near, run_deterministic as rd
    from vcbrain.models import Claim, ClaimType

    assert _number_near("Top 50 firms use us, logo retention 95%",
                        ["retention"]) == 95.0
    claim = Claim(id="C01-test", text="Top 50 accounting firms use us, logo retention 85%",
                  claim_type=ClaimType.TRACTION, provenance="deck")
    e = rd([claim], sub)[0]
    assert e.status == EvidenceStatus.VERIFIED  # compared 85 vs metrics 85, not 50
    assert e.stated_value == "85"


def test_off_enum_claim_type_is_classified_not_crashed(sub):
    payload = {"claims": [
        {"text": "Revenue growing 12% MoM", "claim_type": "go-to-market",  # off-enum
         "provenance": "deck"},
        {"claim_type": "traction"},          # missing text → skipped
        "not-a-dict",                        # junk → skipped
    ]}
    fake = FakeClient([[_text_block(json.dumps(payload))]])
    llm.set_client_factory(lambda: fake)
    claims = extract_claims(sub, mock=False)
    assert len(claims) == 1
    assert claims[0].claim_type.value == "traction"  # heuristic reclassification


def test_claim_ids_stable_across_runs(sub):
    a = extract_claims(sub, mock=True)
    b = extract_claims(sub, mock=True)
    assert [c.id for c in a] == [c.id for c in b]
    assert all("-" in c.id for c in a)  # position + content hash


def test_live_mode_skips_curated_reference_table(sub):
    claims = extract_claims(sub, mock=True)
    fake = FakeClient([[_text_block(json.dumps({"verdicts": []}))]])
    llm.set_client_factory(lambda: fake)
    evidence = run_evidence(claims, sub, mock=False)
    assert not any("curated ref table" in e.method for e in evidence)
    # ...but mock mode still uses it
    ev_mock = run_evidence(claims, sub, mock=True)
    assert any("curated ref table" in e.method for e in ev_mock)


def test_partial_verdicts_accepted(sub):
    claims = extract_claims(sub, mock=True)
    pending = [e.claim_id
               for e in run_deterministic(claims, sub, use_reference_table=False)
               if e.status == EvidenceStatus.UNSUPPORTED]
    # model only answers for the first pending claim
    verdicts = {"verdicts": [{"claim_id": pending[0], "status": "verified",
                              "detail": "confirmed", "confidence": 0.9}]}
    fake = FakeClient([[_text_block(json.dumps(verdicts))]])
    llm.set_client_factory(lambda: fake)
    notes = []
    evidence = {e.claim_id: e for e in
                run_evidence(claims, sub, mock=False, on_note=notes.append)}
    assert evidence[pending[0]].status == EvidenceStatus.VERIFIED  # kept, not discarded
    for cid in pending[1:]:
        assert evidence[cid].status == EvidenceStatus.UNSUPPORTED
    assert notes and "no verdict" in notes[0]


# ------------------------------------------------------------- upload parsing

def test_upload_parsing_csv_and_xlsx(tmp_path):
    import io as _io

    from openpyxl import Workbook

    from vcbrain.uploads import parse_files

    class F:
        def __init__(self, name, data):
            self.filename, self._d = name, data

        def read(self):
            return self._d

    rev_csv = b"month,revenue\nJan-26,1000\nFeb-26,1200\n"
    met_csv = b"gross margin pct,78\ncac usd,1450\n"
    wb = Workbook()
    ws = wb.active
    ws.append(["month", "revenue"])
    ws.append(["Mar-26", 1500])
    buf = _io.BytesIO()
    wb.save(buf)
    deck = b"# Traction\n- Hit $45,000 MRR in June 2026.\n"

    out = parse_files([F("revenue.csv", rev_csv), F("metrics.csv", met_csv),
                       F("more.xlsx", buf.getvalue()), F("deck.md", deck),
                       F("weird.xyz", b"ignored")])
    assert "45,000 MRR" in out["deck"]
    assert '"gross_margin_pct": 78.0' in out["metrics"]
    rows = out["revenue"].strip().splitlines()
    assert rows[0] == "month,revenue" and len(rows) == 4  # csv 2 + xlsx 1


def test_decline_band_label(sub):
    """Sub-50 composite must read DECLINE, not the ambiguous 'PASS'."""
    claims = extract_claims(sub, mock=True)
    evidence = run_deterministic(claims, sub)
    for e in evidence:  # sabotage: contradict everything → score collapses
        e.status = EvidenceStatus.CONTRADICTED
    d = score_deterministic(sub, claims, evidence)
    assert d.composite < 50
    assert d.decision == "DECLINE"
    assert d.check_size == 0


def test_live_scoring_uses_llm(sub):
    """Live scoring path calls Claude and maps the IC JSON into a Decision."""
    payload = {
        "dimensions": [
            {"dimension": "team", "score": 60, "rationale": ["C01 unsupported"]},
            {"dimension": "traction", "score": 40, "rationale": ["C05 contradicted growth"]},
            {"dimension": "market", "score": 55, "rationale": ["TAM roughly in range"]},
            {"dimension": "product", "score": 50, "rationale": ["thin product evidence"]},
            {"dimension": "economics", "score": 70, "rationale": ["gross margin software-grade"]},
            {"dimension": "integrity", "score": 30, "rationale": ["one hard contradiction"]},
        ],
        "integrity_multiplier": 0.79,
        "composite": 42.0,
        "decision": "DECLINE",
        "check_size": 0,
        "conditions": ["Resolve the MoM growth contradiction"],
        "key_risks": ["Founder inflated growth"],
        "summary": "Integrity failure drives a decline.",
    }
    llm.set_client_factory(lambda: FakeClient([[_text_block(json.dumps(payload))]]))
    claims = extract_claims(sub, mock=True)
    evidence = run_deterministic(claims, sub)
    d = score(sub, claims, evidence, mock=False)
    assert d.decision == "DECLINE"
    assert d.composite == 42.0
    assert d.integrity_multiplier == 0.79
    assert any(x.dimension == "integrity" and x.score == 30 for x in d.dimensions)
    assert "growth" in d.conditions[0].lower() or "MoM" in d.conditions[0]


# ------------------------------------------------------------ rendering tests

def test_dashboard_renders_citations(tmp_path, sub):
    claims = extract_claims(sub, mock=True)
    evidence = run_deterministic(claims, sub)
    target = next(e for e in evidence if e.status == EvidenceStatus.UNSUPPORTED)
    target.citations = [{"url": "https://example.com/ref", "title": "Example Ref"}]
    decision = score(sub, claims, evidence, mock=True)
    out = tmp_path / "dash.html"
    write_dashboard(out, sub, claims, evidence, decision, mode="live")
    html = out.read_text()
    assert 'href="https://example.com/ref"' in html
    assert "Example Ref" in html
    assert str(decision.composite) in html
    assert "live — Claude extraction" in html          # mode banner (§4.6)
    assert "Top findings" in html                      # contradictions above the fold (§4.1)
    assert "claimed 40%/mo" in html                    # ghost trajectory on chart (§4.3)
    assert 'data-status="contradicted"' in html        # filterable table rows (§4.2)
    assert "conf 97%" in html or "conf " in html       # confidence surfaced (§4.5)
