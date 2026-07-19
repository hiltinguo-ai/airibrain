"""Stage 5 - Memo generator: decision.json + dashboard.html.

The dashboard is a single self-contained HTML file (inline CSS, no dependencies)
styled per the dataviz reference palette: status colors carry icon + label (never
color alone), dimension meters are single-hue blue ramps, text wears text tokens.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import asdict
from pathlib import Path

from .models import Claim, Decision, Evidence, EvidenceStatus, Submission

# status → (label, icon, light hex, dark hex)
_STATUS_CHIP = {
    "verified": ("Verified", "✓", "#0ca30c", "#0ca30c"),
    "corroborated": ("Corroborated", "◐", "#2a78d6", "#3987e5"),
    "unsupported": ("Unsupported", "!", "#c98500", "#fab219"),
    "contradicted": ("Contradicted", "✕", "#d03b3b", "#d03b3b"),
}

_DECISION_META = {
    "INVEST": ("INVEST", "✓", "good"),
    "INVEST_WITH_CONDITIONS": ("INVEST - WITH CONDITIONS", "!", "warn"),
    "DECLINE": ("DECLINE", "✕", "crit"),
}


def write_json(path: Path, sub: Submission, claims: list[Claim],
               evidence: list[Evidence], decision: Decision,
               mode: str = "mock") -> None:
    payload = {
        "company": sub.company,
        "one_liner": sub.one_liner,
        "ask": sub.ask,
        "engine_mode": mode,
        "decision": asdict(decision),
        "claims": [c.to_dict() for c in claims],
        "evidence": [e.to_dict() for e in evidence],
        "source_files": sub.source_files,
    }
    path.write_text(json.dumps(payload, indent=2))


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _claimed_growth_pct(evidence: list[Evidence]) -> float | None:
    """Stated MoM growth from a recomputed-growth contradiction, if any."""
    for e in evidence:
        if (e.status == EvidenceStatus.CONTRADICTED
                and e.method.startswith("recomputed") and e.stated_value):
            m = re.search(r"(\d+(?:\.\d+)?)", e.stated_value)
            if m:
                return float(m.group(1))
    return None


def _revenue_svg(sub: Submission, evidence: list[Evidence]) -> str:
    """Actual submitted revenue (blue) vs the founder's claimed growth
    trajectory (orange) - the chart IS the evidence for the contradiction.
    The claimed line exits the top of the plot when it outruns reality."""
    series = sub.revenue_series
    if len(series) < 2:
        return ""
    W, H, PAD_L, PAD_R, PAD_T, PAD_B = 640, 230, 56, 76, 18, 30
    revs = [p["revenue"] for p in series]
    top = max(revs) * 1.15
    n = len(series)

    def x(i: float) -> float:
        return PAD_L + (W - PAD_L - PAD_R) * (i / (n - 1))

    def y(v: float) -> float:
        return PAD_T + (H - PAD_T - PAD_B) * (1 - v / top)

    # clean gridline steps
    step = 10_000 if top > 30_000 else 5_000
    grid, ticks = [], []
    g = step
    while g < top:
        gy = y(g)
        grid.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{W - PAD_R}" y2="{gy:.1f}" class="grid"/>')
        ticks.append(f'<text x="{PAD_L - 8}" y="{gy + 4:.1f}" class="tick" text-anchor="end">{g // 1000}K</text>')
        g += step

    pts = " ".join(f"{x(i):.1f},{y(p['revenue']):.1f}" for i, p in enumerate(series))
    xlabels = "".join(
        f'<text x="{x(i):.1f}" y="{H - 8}" class="tick" text-anchor="middle">{_esc(p["month"])}</text>'
        for i, p in enumerate(series)
    )
    lx, ly = x(n - 1), y(revs[-1])

    # claimed-growth ghost trajectory
    claimed_svg, legend_claimed = "", ""
    claimed_pct = _claimed_growth_pct(evidence)
    if claimed_pct:
        r = 1 + claimed_pct / 100.0
        cvals = [revs[0] * (r ** i) for i in range(n)]
        cpts, exit_xy = [], None
        for i, v in enumerate(cvals):
            if v <= top:
                cpts.append((x(i), y(v)))
            else:
                # interpolate the exit through the top of the plot
                prev = cvals[i - 1]
                f = (top - prev) / (v - prev)
                exit_xy = (x(i - 1) + f * (x(i) - x(i - 1)), PAD_T)
                cpts.append(exit_xy)
                break
        cline = " ".join(f"{px:.1f},{py:.1f}" for px, py in cpts)
        if exit_xy:
            label = (f'<text x="{min(exit_xy[0] + 8, W - 4):.1f}" y="{PAD_T + 12}" '
                     f'class="claim-label">claimed {claimed_pct:g}%/mo - off the chart</text>')
        else:
            ex, ey = cpts[-1]
            label = (f'<text x="{ex + 12:.1f}" y="{ey + 4:.1f}" '
                     f'class="claim-label">claimed {claimed_pct:g}%/mo</text>')
        claimed_svg = (f'<polyline points="{cline}" fill="none" class="claim-line"/>{label}')
        legend_claimed = ('<span class="key"><span class="swatch swatch-claimed"></span>'
                          f'claimed trajectory ({claimed_pct:g}% MoM)</span>')

    legend = (f'<div class="legend"><span class="key">'
              f'<span class="swatch swatch-actual"></span>actual (submitted CSV)</span>'
              f'{legend_claimed}</div>')
    return f"""{legend}
<svg viewBox="0 0 {W} {H}" role="img"
     aria-label="Monthly revenue: actual submitted series vs claimed growth trajectory">
  {''.join(grid)}
  <line x1="{PAD_L}" y1="{H - PAD_B}" x2="{W - PAD_R}" y2="{H - PAD_B}" class="axis"/>
  {''.join(ticks)}{xlabels}
  {claimed_svg}
  <polyline points="{pts}" fill="none" class="rev-line"/>
  <circle cx="{lx:.1f}" cy="{ly:.1f}" r="6" class="end-dot"/>
  <text x="{lx + 12:.1f}" y="{ly + 4:.1f}" class="end-label">${revs[-1]:,.0f}</text>
</svg>"""


def _meter(d) -> str:
    return f"""
<div class="dim">
  <div class="dim-head"><span>{_esc(d.dimension.title())}</span>
    <span class="dim-val">{d.score:.0f}<span class="dim-den">/100</span>
      <span class="dim-wt">w {d.weight:.0%}</span></span></div>
  <div class="track"><div class="fill" style="width:{d.score:.0f}%"></div></div>
  <details><summary>rationale</summary><ul>{''.join(f'<li>{_esc(r)}</li>' for r in d.rationale)}</ul></details>
</div>"""


def write_dashboard(path: Path, sub: Submission, claims: list[Claim],
                    evidence: list[Evidence], decision: Decision,
                    mode: str = "mock") -> None:
    ev = {e.claim_id: e for e in evidence}
    label, icon, tone = _DECISION_META[decision.decision]

    counts = {s.value: 0 for s in EvidenceStatus}
    for e in evidence:
        counts[e.status.value] += 1

    mode_live = mode == "live"
    mode_txt = ("live - Claude extraction · web-search adjudication" if mode_live
                else "mock - deterministic engine only (no LLM, no web search)")

    # Top findings: contradictions first - the memo leads with what matters.
    findings = []
    for c in claims:
        e = ev[c.id]
        if e.status != EvidenceStatus.CONTRADICTED:
            continue
        delta = (f'<span class="delta">stated <b>{_esc(e.stated_value)}</b> → '
                 f'found <b>{_esc(e.computed_value)}</b></span>'
                 if e.stated_value else "")
        findings.append(
            f'<div class="finding"><span class="chip chip-contradicted">'
            f'<span class="chip-icon">✕</span>Contradicted</span>'
            f'<div><div class="claim-text">{_esc(c.text)}</div>'
            f'<div class="detail">{_esc(e.detail)} {delta}</div></div></div>')
    findings_card = (
        f'<div class="card"><h2>Top findings</h2>{"".join(findings)}'
        f'<div class="hint-line">{len(decision.conditions)} open item(s) routed to '
        f'the founder question list below.</div></div>'
        if findings else "")

    rows = []
    for c in claims:
        e = ev[c.id]
        clabel, cicon, lt, dk = _STATUS_CHIP[e.status.value]
        stated = f'<div class="sv">stated <b>{_esc(e.stated_value)}</b> · found <b>{_esc(e.computed_value)}</b></div>' \
            if e.stated_value else ""
        cites = ""
        if e.citations:
            links = "".join(
                f'<a href="{_esc(c["url"])}" target="_blank" rel="noopener">'
                f'{_esc((c.get("title") or c["url"]))[:52]} ↗</a>'
                for c in e.citations[:4]
            )
            cites = f'<div class="cites">{links}</div>'
        rows.append(f"""
<tr data-status="{e.status.value}" class="{'row-bad' if e.status.value == 'contradicted' else ''}">
  <td class="mono">{c.id.split('-')[0]}</td>
  <td><div class="claim-text">{_esc(c.text)}</div>
      <div class="prov">{_esc(c.provenance)}{'' if c.claim_type.value in c.provenance.lower() else ' · ' + _esc(c.claim_type.value)}</div></td>
  <td><span class="chip chip-{e.status.value}"><span class="chip-icon">{cicon}</span>{clabel}</span>
      <div class="conf">conf {e.confidence:.0%}</div></td>
  <td><div class="detail">{_esc(e.detail)}</div>{stated}{cites}
      <div class="prov">{_esc(e.method)}</div></td>
</tr>""")

    conditions = "".join(f"<li>{_esc(x)}</li>" for x in decision.conditions) or "<li>None.</li>"
    risks = "".join(f"<li>{_esc(x)}</li>" for x in decision.key_risks) or "<li>None identified.</li>"
    meters = "".join(_meter(d) for d in decision.dimensions)
    rev_chart = _revenue_svg(sub, evidence)

    doc = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AiriBrain - {_esc(sub.company)} decision memo</title>
<style>
  .viz-root {{
    color-scheme: dark;
    --surface-1:#0d1420; --page:#070b12;
    --ink-1:#e8eef6; --ink-2:#8aa0bd; --ink-3:#51648a;
    --grid:#1c2942; --axis:#2a3c5e; --border:#1c2942;
    --blue:#3987e5; --blue-track:#16365f; --claimed:#d95926;
    --cyan:#3fd0ff;
    --good:#0ca30c; --warn:#fab219; --crit:#d03b3b; --corr:#3987e5;
    --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,"Cascadia Code",Consolas,monospace;
  }}
  * {{ box-sizing:border-box; margin:0; }}
  body {{ font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
  .viz-root {{ background:var(--page); color:var(--ink-1); min-height:100vh;
               padding:32px 20px;
               background-image:
                 radial-gradient(900px 400px at 50% -10%, rgba(63,208,255,.06), transparent 60%),
                 repeating-linear-gradient(0deg, transparent 0 39px, rgba(63,208,255,.04) 39px 40px),
                 repeating-linear-gradient(90deg, transparent 0 39px, rgba(63,208,255,.04) 39px 40px); }}
  .wrap {{ max-width:960px; margin:0 auto; display:grid; gap:16px; }}
  .card {{ background:var(--surface-1); border:1px solid var(--border);
           border-radius:10px; padding:20px 24px; }}
  h1 {{ font-size:20px; font-weight:700; font-family:var(--mono); letter-spacing:.02em; }}
  h2 {{ font-size:11px; font-weight:600; color:var(--ink-2); font-family:var(--mono);
        text-transform:uppercase; letter-spacing:.14em; margin-bottom:12px; }}
  h2::before {{ content:"// "; color:var(--ink-3); }}
  .sub {{ color:var(--ink-2); font-size:14px; margin-top:4px; }}
  .head {{ display:flex; justify-content:space-between; gap:16px; align-items:flex-start; flex-wrap:wrap; }}
  .hero {{ text-align:right; }}
  .hero .num {{ font-size:52px; font-weight:700; line-height:1; font-family:var(--mono);
                color:var(--cyan); text-shadow:0 0 20px rgba(63,208,255,.45); }}
  .hero .den {{ font-size:16px; color:var(--ink-3); font-weight:400; }}
  .hero .cap {{ font-size:12px; color:var(--ink-2); margin-top:2px; }}
  .decision {{ display:inline-flex; align-items:center; gap:8px; margin-top:10px;
               font-weight:650; font-size:14px; padding:6px 12px; border-radius:8px;
               border:1.5px solid; }}
  .tone-good {{ color:var(--good); border-color:var(--good); }}
  .tone-warn {{ color:var(--warn); border-color:var(--warn); }}
  .tone-crit {{ color:var(--crit); border-color:var(--crit); }}
  .tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; }}
  .tile {{ background:var(--surface-1); border:1px solid var(--border);
           border-radius:12px; padding:14px 16px; font:inherit; color:inherit;
           text-align:left; cursor:pointer; }}
  .tile:hover {{ border-color:var(--ink-3); }}
  .tile.active {{ border-color:var(--blue); box-shadow:0 0 0 1px var(--blue); }}
  .tile .lab {{ font-size:11px; color:var(--ink-2); font-family:var(--mono);
                letter-spacing:.06em; text-transform:uppercase; }}
  .tile .val {{ font-size:26px; font-weight:700; margin-top:2px; font-family:var(--mono); }}
  .mode {{ font-size:11px; margin-top:8px; }}
  .mode-live {{ color:var(--good); }}
  .mode-mock {{ color:var(--ink-3); }}
  .finding {{ display:flex; gap:12px; align-items:flex-start; padding:10px 0;
              border-bottom:1px solid var(--grid); }}
  .finding:last-of-type {{ border-bottom:none; }}
  .delta {{ color:var(--crit); }}
  .hint-line {{ font-size:12px; color:var(--ink-3); margin-top:10px; }}
  .conf {{ font-size:10px; color:var(--ink-3); margin-top:4px; }}
  .legend {{ display:flex; gap:18px; font-size:12px; color:var(--ink-2); margin-bottom:8px; }}
  .key {{ display:inline-flex; align-items:center; gap:6px; }}
  .swatch {{ width:14px; height:3px; border-radius:2px; display:inline-block; }}
  .swatch-actual {{ background:var(--blue); }}
  .swatch-claimed {{ background:var(--claimed); }}
  .dim {{ margin-bottom:14px; }}
  .dim-head {{ display:flex; justify-content:space-between; font-size:13px; margin-bottom:5px; }}
  .dim-val {{ font-weight:600; }}
  .dim-den, .dim-wt {{ color:var(--ink-3); font-weight:400; font-size:11px; }}
  .dim-wt {{ margin-left:6px; }}
  .track {{ height:10px; border-radius:5px; background:var(--blue-track); overflow:hidden; }}
  .fill {{ height:100%; background:var(--blue); border-radius:0 5px 5px 0; }}
  details {{ margin-top:4px; }}
  summary {{ font-size:11px; color:var(--ink-3); cursor:pointer; }}
  details ul {{ margin:6px 0 0 16px; font-size:12px; color:var(--ink-2); display:grid; gap:3px; }}
  table {{ width:100%; border-collapse:collapse; font-size:13px; }}
  th {{ text-align:left; font-size:11px; text-transform:uppercase; letter-spacing:.04em;
        color:var(--ink-3); font-weight:600; padding:6px 10px 8px 0; border-bottom:1px solid var(--grid); }}
  td {{ padding:10px 10px 10px 0; border-bottom:1px solid var(--grid); vertical-align:top; }}
  tr:last-child td {{ border-bottom:none; }}
  tr:hover td {{ background:color-mix(in srgb, var(--ink-1) 3%, transparent); }}
  .row-bad td {{ background:color-mix(in srgb, var(--crit) 6%, transparent); }}
  .mono {{ font-variant-numeric:tabular-nums; color:var(--ink-3); font-size:11px;
           font-family:var(--mono); }}
  .claim-text {{ font-weight:550; }}
  .prov {{ font-size:11px; color:var(--ink-3); margin-top:3px; }}
  .detail {{ color:var(--ink-2); }}
  .sv {{ font-size:12px; margin-top:4px; color:var(--ink-2); }}
  .cites {{ margin-top:6px; display:flex; flex-wrap:wrap; gap:6px; }}
  .cites a {{ font-size:11px; font-weight:600; color:var(--blue); text-decoration:none;
              border:1px solid var(--border); border-radius:999px; padding:2px 9px; }}
  .cites a:hover {{ border-color:var(--blue); }}
  .chip {{ display:inline-flex; align-items:center; gap:5px; font-size:11px;
           font-weight:700; padding:3px 9px; border-radius:999px; border:1.5px solid;
           white-space:nowrap; font-family:var(--mono); letter-spacing:.04em; }}
  .chip-verified {{ box-shadow:0 0 10px rgba(12,163,12,.25); }}
  .chip-contradicted {{ box-shadow:0 0 10px rgba(208,59,59,.3); }}
  .chip-icon {{ font-size:11px; }}
  .chip-verified {{ color:var(--good); border-color:var(--good); }}
  .chip-corroborated {{ color:var(--corr); border-color:var(--corr); }}
  .chip-unsupported {{ color:var(--warn); border-color:var(--warn); }}
  .chip-contradicted {{ color:var(--crit); border-color:var(--crit); }}
  ol,ul.plain {{ margin-left:18px; font-size:13px; color:var(--ink-2); display:grid; gap:8px; }}
  svg {{ width:100%; height:auto; display:block; }}
  .grid {{ stroke:var(--grid); stroke-width:1; }}
  .axis {{ stroke:var(--axis); stroke-width:1; }}
  .tick {{ fill:var(--ink-3); font-size:11px; font-family:inherit; }}
  .rev-line {{ stroke:var(--blue); stroke-width:2; stroke-linejoin:round; stroke-linecap:round; }}
  .claim-line {{ stroke:var(--claimed); stroke-width:2; stroke-linejoin:round;
                 stroke-linecap:round; opacity:.85; }}
  .claim-label {{ fill:var(--ink-2); font-size:11px; font-weight:600; font-family:inherit; }}
  .end-dot {{ fill:var(--blue); stroke:var(--surface-1); stroke-width:2; }}
  .end-label {{ fill:var(--ink-1); font-size:12px; font-weight:600; font-family:inherit; }}
  .foot {{ font-size:11px; color:var(--ink-3); text-align:center; padding:8px 0 4px; }}
</style></head>
<body><div class="viz-root"><div class="wrap">

  <div class="card head">
    <div>
      <h1>{_esc(sub.company)}</h1>
      <div class="sub">{_esc(sub.one_liner)}</div>
      <div class="sub">Ask: {_esc(sub.ask)} · Sources: {_esc(', '.join(sub.source_files))}</div>
      <div class="decision tone-{tone}"><span>{icon}</span>{label}
        {'· $' + format(decision.check_size, ',') if decision.check_size else ''}</div>
    </div>
    <div class="hero">
      <div class="num">{decision.composite:g}<span class="den">/100</span></div>
      <div class="cap">composite · integrity ×{decision.integrity_multiplier}</div>
      <div class="mode {'mode-live' if mode_live else 'mode-mock'}">● {_esc(mode_txt)}</div>
    </div>
  </div>

  <div class="card"><div style="font-size:14px; color:var(--ink-2)">{_esc(decision.summary)}</div></div>

  {findings_card}

  <div class="tiles" id="tiles">
    <button class="tile active" data-status=""><div class="lab">Claims audited</div><div class="val">{len(claims)}</div></button>
    <button class="tile" data-status="verified"><div class="lab">Verified</div><div class="val">{counts['verified']}</div></button>
    <button class="tile" data-status="corroborated"><div class="lab">Corroborated</div><div class="val">{counts['corroborated']}</div></button>
    <button class="tile" data-status="unsupported"><div class="lab">Unsupported</div><div class="val">{counts['unsupported']}</div></button>
    <button class="tile" data-status="contradicted"><div class="lab">Contradicted</div><div class="val">{counts['contradicted']}</div></button>
  </div>

  <div class="card"><h2>Score by dimension</h2>{meters}</div>

  {f'<div class="card"><h2>Submitted revenue series (basis for recomputation)</h2>{rev_chart}</div>' if rev_chart else ''}

  <div class="card"><h2>Claim-by-claim evidence table</h2>
    <table>
      <thead><tr><th>ID</th><th>Claim</th><th>Status</th><th>Evidence</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </div>

  <div class="card"><h2>Conditions - auto-generated founder question list</h2><ol>{conditions}</ol></div>
  <div class="card"><h2>Key risks</h2><ul class="plain">{risks}</ul></div>

  <div class="foot">Generated by AiriBrain ({_esc(mode_txt)}) · every line above traces to a
    claim ID and a verification method · live scoring by Claude IC partner (mock = rules)</div>
<script>
  document.querySelectorAll('#tiles .tile').forEach(t => t.addEventListener('click', () => {{
    const s = t.dataset.status;
    document.querySelectorAll('#tiles .tile').forEach(x => x.classList.toggle('active', x === t));
    document.querySelectorAll('tbody tr').forEach(r =>
      r.style.display = (!s || r.dataset.status === s) ? '' : 'none');
  }}));
</script>
</div></div></body></html>"""
    path.write_text(doc)
