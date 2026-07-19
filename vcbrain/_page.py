"""The VC Brain app — three layers, modern and friendly.

Layer 1 · DECISION — drop in a deck (PDF) + financials (Excel/CSV), get a verdict.
Layer 2 · EVIDENCE — the proof behind the verdict.
Layer 3 · ENGINE   — the algorithm, the live log, the raw data.

Design: dark, soft, spacious. One cyan→blue accent, big rounded cards, gentle
staggered animations (disabled under prefers-reduced-motion), status always
icon + label. Sans for words, mono only for numbers and code.
"""

PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AiriBrain — evidence-backed decisions</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0' stop-color='%233fd0ff'/%3E%3Cstop offset='1' stop-color='%232f6fe0'/%3E%3C/linearGradient%3E%3C/defs%3E%3Crect x='2' y='2' width='60' height='60' rx='15' fill='url(%23g)'/%3E%3Cpath d='M19 45 L32 17 L45 45' fill='none' stroke='%23fff' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M25.5 36.5 H38.5' fill='none' stroke='%23fff' stroke-width='5' stroke-linecap='round'/%3E%3Ccircle cx='32' cy='17' r='4.2' fill='%23fff'/%3E%3Ccircle cx='19' cy='45' r='4.2' fill='%23fff'/%3E%3Ccircle cx='45' cy='45' r='4.2' fill='%23fff'/%3E%3C/svg%3E">
<style>
  :root {
    color-scheme: dark;
    --bg:#0b0f17; --card:#121a28; --card-2:#0d1420; --line:#1f2b40; --line-2:#2a3a58;
    --ink:#f1f5f9; --dim:#94a3b8; --faint:#5b6b85;
    --cyan:#3fd0ff; --blue:#3987e5; --blue-track:#17304f;
    --grad:linear-gradient(135deg,#3fd0ff,#3987e5);
    --good:#0ca30c; --warn:#fab219; --crit:#d03b3b; --claimed:#d95926;
    --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
    --r:16px;
  }
  * { box-sizing:border-box; margin:0; }
  html { scroll-behavior:smooth; }
  body { font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
         background:var(--bg); color:var(--ink); min-height:100vh; padding:24px 20px 70px;
         background-image:radial-gradient(1000px 460px at 50% -8%, rgba(63,208,255,.08), transparent 60%); }
  .wrap { max-width:1180px; margin:0 auto; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation:none !important; transition:none !important; }
  }

  /* ---------- top bar ---------- */
  .topbar { display:flex; align-items:center; gap:14px; flex-wrap:wrap;
            padding:14px 20px; background:var(--card); border:1px solid var(--line);
            border-radius:var(--r); margin-bottom:16px; }
  .logo { display:flex; align-items:center; gap:10px; font-weight:800; font-size:17px;
          letter-spacing:-.01em; }
  .logo .dot { width:30px; height:30px; border-radius:9px; background:var(--grad);
               display:grid; place-items:center; color:#06121f; font-size:15px;
               font-family:var(--mono); font-weight:800;
               box-shadow:0 0 18px rgba(63,208,255,.35); }
  .mode { display:flex; align-items:center; gap:7px; font-size:12px; color:var(--dim);
          background:var(--card-2); border:1px solid var(--line); border-radius:999px;
          padding:5px 12px; }
  .led { width:8px; height:8px; border-radius:50%; }
  .led-live { background:var(--good); box-shadow:0 0 8px var(--good); }
  .led-mock { background:var(--warn); box-shadow:0 0 8px var(--warn); }

  .layers { margin-left:auto; display:flex; gap:4px; background:var(--card-2);
            border:1px solid var(--line); border-radius:999px; padding:4px; }
  .lbtn { font-size:12.5px; font-weight:650; padding:8px 18px; border-radius:999px;
          border:none; background:transparent; color:var(--dim); cursor:pointer;
          transition:all .25s; }
  .lbtn:hover:not(:disabled):not(.on) { color:var(--ink); }
  .lbtn.on { background:var(--grad); color:#06121f;
             box-shadow:0 0 16px rgba(63,208,255,.35); }
  .lbtn:disabled { opacity:.35; cursor:default; }

  .layer { display:none; }
  .layer.on { display:block; animation:fadein .3s ease-out; }
  @keyframes fadein { from { opacity:0; transform:translateY(8px);} to { opacity:1; } }

  /* ---------- cards ---------- */
  .card { background:var(--card); border:1px solid var(--line); border-radius:var(--r);
          transition:border-color .25s; }
  .stack > * + * { margin-top:14px; }
  .card-head { display:flex; align-items:center; gap:10px; padding:15px 20px;
               border-bottom:1px solid var(--line); font-weight:700; font-size:13.5px; }
  .card-head .sub { margin-left:auto; font-size:11px; color:var(--faint); font-weight:500; }
  .card-body { padding:18px 20px; }
  .pop { animation:pop .45s cubic-bezier(.2,.9,.3,1.2) backwards; }
  @keyframes pop { from { opacity:0; transform:scale(.96) translateY(8px);} to { opacity:1; } }

  /* ---------- layer 1 ---------- */
  .cockpit { display:grid; grid-template-columns:5fr 7fr; gap:14px; align-items:start; }
  @media (max-width:980px) { .cockpit { grid-template-columns:1fr; } }
  label { display:block; font-size:11px; font-weight:650; color:var(--faint);
          margin:13px 0 6px; letter-spacing:.02em; }
  input { width:100%; background:var(--card-2); color:var(--ink);
      border:1px solid var(--line); border-radius:10px; padding:10px 13px;
      font:inherit; font-size:13.5px; transition:all .2s; }
  input:focus { outline:none; border-color:var(--cyan);
      box-shadow:0 0 0 3px rgba(63,208,255,.15); }
  .grid2 { display:grid; grid-template-columns:1.4fr 1fr; gap:0 12px; }

  .drop { margin-top:16px; border:1.5px dashed var(--line-2); border-radius:12px;
          padding:26px 18px; text-align:center; cursor:pointer; transition:all .25s;
          background:var(--card-2); }
  .drop:hover, .drop.over { border-color:var(--cyan); background:rgba(63,208,255,.05);
          box-shadow:inset 0 0 30px rgba(63,208,255,.05); }
  .drop.over { transform:scale(1.01); }
  .drop .big { font-size:14px; font-weight:650; }
  .drop .small { font-size:12px; color:var(--faint); margin-top:5px; }
  .drop .icon { font-size:22px; margin-bottom:8px; opacity:.9; }
  .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
  .fchip { display:inline-flex; align-items:center; gap:8px; font-size:12px;
           background:var(--card-2); border:1px solid var(--line); border-radius:999px;
           padding:6px 7px 6px 8px; animation:pop .3s backwards; }
  .fchip .type { font-family:var(--mono); font-size:9px; font-weight:800; color:#06121f;
                 background:var(--grad); border-radius:6px; padding:3px 6px; }
  .fchip .x { width:18px; height:18px; border-radius:50%; border:none; cursor:pointer;
              background:var(--line); color:var(--dim); font-size:11px; line-height:1;
              display:grid; place-items:center; }
  .fchip .x:hover { background:var(--crit); color:#fff; }

  .row { display:flex; gap:10px; margin-top:18px; align-items:center; flex-wrap:wrap; }
  .btn { font:inherit; font-size:13.5px; font-weight:700; border-radius:12px;
         padding:12px 22px; cursor:pointer; border:1px solid var(--line);
         background:var(--card-2); color:var(--ink); transition:all .2s; }
  .btn:hover:not(:disabled) { transform:translateY(-1px); border-color:var(--line-2); }
  .btn-primary { background:var(--grad); border:none; color:#06121f; }
  .btn-primary:hover:not(:disabled) { box-shadow:0 6px 22px rgba(63,208,255,.35); }
  .btn:disabled { opacity:.55; cursor:default; transform:none; }
  .hint { font-size:11.5px; color:var(--faint); }

  /* progress steps */
  .steps { display:flex; gap:0; align-items:center; padding:22px 20px 6px; }
  .stepp { flex:1; text-align:center; position:relative; }
  .stepp .bub { width:34px; height:34px; border-radius:50%; margin:0 auto;
      display:grid; place-items:center; font-size:13px; font-weight:700;
      background:var(--card-2); border:1.5px solid var(--line); color:var(--faint);
      transition:all .35s; position:relative; z-index:1; }
  .stepp .lbl { font-size:10.5px; color:var(--faint); margin-top:7px; font-weight:650;
                letter-spacing:.03em; }
  .stepp::before { content:""; position:absolute; top:17px; left:-50%; width:100%;
      height:2px; background:var(--line); z-index:0; transition:background .35s; }
  .stepp:first-child::before { display:none; }
  .stepp.act .bub { border-color:var(--cyan); color:var(--cyan);
      box-shadow:0 0 0 5px rgba(63,208,255,.12), 0 0 18px rgba(63,208,255,.3);
      animation:pulse 1.4s ease-in-out infinite; }
  @keyframes pulse { 50% { box-shadow:0 0 0 9px rgba(63,208,255,.06), 0 0 18px rgba(63,208,255,.3);} }
  .stepp.did .bub { background:var(--grad); border-color:transparent; color:#06121f; }
  .stepp.did::before, .stepp.act::before { background:var(--blue); }
  .stepp.act .lbl, .stepp.did .lbl { color:var(--dim); }
  .lastline { font-size:12.5px; color:var(--dim); padding:14px 22px 20px; min-height:44px;
              text-align:center; }

  /* results */
  .placeholder { padding:70px 24px; text-align:center; color:var(--faint); }
  .placeholder .icon { font-size:30px; margin-bottom:12px; opacity:.7; }
  .hero { display:flex; align-items:center; justify-content:center; gap:36px;
          padding:28px 20px 6px; flex-wrap:wrap; }
  .ring { position:relative; width:168px; height:168px; }
  .ring svg { transform:rotate(-90deg); }
  .ring .track { stroke:var(--blue-track); }
  .ring .arc { stroke-linecap:round; transition:stroke-dashoffset 1.4s cubic-bezier(.3,.7,.3,1); }
  .ring .mid { position:absolute; inset:0; display:grid; place-items:center; text-align:center; }
  .ring .val { font-family:var(--mono); font-size:38px; font-weight:800; line-height:1; }
  .ring .cap { font-size:10px; color:var(--faint); margin-top:4px; font-weight:650;
               letter-spacing:.06em; }
  .verdict-side { text-align:left; max-width:380px; }
  .stamp { display:inline-block; padding:10px 22px; border:2px solid; border-radius:12px;
           font-size:16px; font-weight:800; letter-spacing:.04em;
           transform:scale(2.4); opacity:0; }
  .stamp.on { animation:stamp .5s cubic-bezier(.2,1.5,.35,1) .9s forwards; }
  @keyframes stamp { to { transform:scale(1); opacity:1; } }
  .tone-good { color:var(--good); border-color:var(--good); background:rgba(12,163,12,.08); }
  .tone-warn { color:var(--warn); border-color:var(--warn); background:rgba(250,178,25,.07); }
  .tone-crit { color:var(--crit); border-color:var(--crit); background:rgba(208,59,59,.08); }
  .v-meta { font-size:12.5px; color:var(--dim); margin-top:12px; line-height:1.6; }
  .summary { font-size:13.5px; color:var(--dim); text-align:center; padding:14px 26px 4px;
             line-height:1.6; }

  .tiles { display:grid; grid-template-columns:repeat(5,1fr); gap:10px; padding:18px 20px 6px; }
  @media (max-width:760px) { .tiles { grid-template-columns:repeat(2,1fr); } }
  .tile { background:var(--card-2); border:1px solid var(--line); border-radius:12px;
          padding:12px 14px; cursor:pointer; font:inherit; color:inherit; text-align:left;
          transition:all .22s; }
  .tile:hover { transform:translateY(-3px); border-color:var(--cyan);
                box-shadow:0 8px 20px rgba(0,0,0,.35); }
  .tile .lab { font-size:10.5px; font-weight:650; color:var(--faint); }
  .tile .val { font-family:var(--mono); font-size:24px; font-weight:800; margin-top:3px; }
  .tile .go { font-size:10px; color:var(--faint); margin-top:4px; transition:color .2s; }
  .tile:hover .go { color:var(--cyan); }

  .dims { padding:8px 20px 18px; }
  .dim { display:grid; grid-template-columns:96px 1fr 88px; gap:12px; align-items:center;
         padding:7px 8px; cursor:pointer; border-radius:10px; transition:background .2s; }
  .dim:hover { background:rgba(63,208,255,.06); }
  .dim .name { font-size:12.5px; font-weight:650; color:var(--dim); text-transform:capitalize; }
  .track2 { display:block; height:9px; border-radius:5px; background:var(--blue-track);
            overflow:hidden; }
  .fill { display:block; height:100%; background:var(--grad); border-radius:5px; width:0;
          transition:width 1s cubic-bezier(.2,.8,.3,1); }
  .dim .num { font-family:var(--mono); font-size:12px; font-weight:700; text-align:right;
              white-space:nowrap; }
  .dim .num i { color:var(--faint); font-style:normal; font-size:9.5px; font-weight:500; }

  .finding { margin:4px 20px 20px; padding:14px 16px; border:1px solid rgba(208,59,59,.45);
             border-radius:12px; background:rgba(208,59,59,.06); cursor:pointer;
             display:flex; gap:12px; align-items:flex-start; transition:all .22s; }
  .finding:hover { box-shadow:0 6px 22px rgba(208,59,59,.2); transform:translateY(-2px); }
  .finding .body { font-size:13px; color:var(--dim); line-height:1.55; }
  .finding .body b { color:var(--ink); display:block; margin-bottom:3px; }
  .finding .delta { color:var(--crit); font-family:var(--mono); font-size:12px; margin-top:4px; }

  /* ---------- chips ---------- */
  .chip { display:inline-flex; align-items:center; gap:5px; font-size:10.5px;
          font-weight:800; padding:3px 10px; border-radius:999px; border:1.5px solid;
          white-space:nowrap; letter-spacing:.03em; }
  .chip-verified     { color:var(--good); border-color:var(--good); background:rgba(12,163,12,.08); }
  .chip-corroborated { color:var(--blue); border-color:var(--blue); background:rgba(57,135,229,.08); }
  .chip-unsupported  { color:var(--warn); border-color:var(--warn); background:rgba(250,178,25,.07); }
  .chip-contradicted { color:var(--crit); border-color:var(--crit); background:rgba(208,59,59,.08); }

  /* ---------- layer 2 ---------- */
  .filters { display:flex; gap:8px; flex-wrap:wrap; padding:16px 20px 4px; }
  .fbtn { font:inherit; font-size:12px; font-weight:700; padding:7px 15px; border-radius:999px;
          border:1px solid var(--line); background:var(--card-2); color:var(--dim);
          cursor:pointer; transition:all .2s; }
  .fbtn:hover { border-color:var(--line-2); color:var(--ink); }
  .fbtn.on { background:var(--grad); color:#06121f; border-color:transparent; }
  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; font-size:10px; text-transform:uppercase; letter-spacing:.08em;
       color:var(--faint); font-weight:700; padding:8px 10px 9px 0;
       border-bottom:1px solid var(--line); }
  td { padding:13px 10px 13px 0; border-bottom:1px solid var(--line); vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  tbody tr { transition:background .15s; }
  tbody tr:hover { background:rgba(63,208,255,.04); }
  .row-bad { background:rgba(208,59,59,.05); }
  .cid { font-family:var(--mono); font-size:10px; color:var(--faint); }
  .claim-text { font-weight:650; font-size:13px; line-height:1.45; }
  .prov { font-size:10.5px; color:var(--faint); margin-top:4px; }
  .detail { color:var(--dim); font-size:12.5px; line-height:1.55; }
  .sv { font-family:var(--mono); font-size:11.5px; margin-top:5px; color:var(--dim); }
  .sv b { color:var(--ink); }
  .conf { font-size:10px; color:var(--faint); margin-top:5px; }
  .cites { margin-top:7px; display:flex; flex-wrap:wrap; gap:6px; }
  .cites a { font-size:11px; font-weight:650; color:var(--cyan); text-decoration:none;
             border:1px solid var(--line); border-radius:999px; padding:3px 11px;
             transition:border-color .2s; }
  .cites a:hover { border-color:var(--cyan); }
  details.rat { border-bottom:1px solid var(--line); padding:10px 0; }
  details.rat:last-child { border-bottom:none; }
  details.rat summary { cursor:pointer; display:grid;
      grid-template-columns:96px 1fr 88px; gap:12px; align-items:center; list-style:none; }
  details.rat summary::-webkit-details-marker { display:none; }
  details.rat ul { margin:10px 0 4px 110px; font-size:12px; color:var(--dim);
                   display:grid; gap:5px; padding-left:14px; line-height:1.5; }
  .legend { display:flex; gap:18px; font-size:11.5px; color:var(--dim); padding:0 0 10px; }
  .key { display:inline-flex; align-items:center; gap:7px; }
  .swatch { width:16px; height:4px; border-radius:2px; }
  ol.conds, ul.risks { margin-left:18px; font-size:13px; color:var(--dim);
                       display:grid; gap:9px; line-height:1.55; }

  /* ---------- layer 3 ---------- */
  #console { font-family:var(--mono); font-size:11.5px; line-height:1.9;
             padding:16px 18px; min-height:120px; max-height:420px; overflow-y:auto;
             background:#080c13; border-radius:0 0 var(--r) var(--r); }
  #console .t { color:var(--faint); margin-right:10px; }
  #console .stage-tag { color:var(--faint); display:inline-block; min-width:76px; }
  #console .msg { color:var(--dim); }
  #console .msg-hi { color:var(--ink); }
  #console div { animation:rise .2s ease-out; }
  @keyframes rise { from { opacity:0; transform:translateY(3px);} to { opacity:1; } }
  .st { font-weight:800; }
  .st-verified { color:var(--good); } .st-corroborated { color:var(--blue); }
  .st-unsupported { color:var(--warn); } .st-contradicted { color:var(--crit); }
  .flash-bad { animation:flash .9s ease-out 1; }
  @keyframes flash { 0% { background:rgba(208,59,59,.28);} 100% { background:transparent;} }
  .spec { font-size:13px; color:var(--dim); line-height:1.7; }
  .spec b { color:var(--ink); }
  .spec .f { font-family:var(--mono); font-size:12px; color:var(--cyan);
             background:#080c13; border:1px solid var(--line); border-radius:10px;
             padding:11px 15px; margin:9px 0; display:block; }
  .wtable td, .wtable th { padding:6px 12px 6px 0; font-family:var(--mono); font-size:11.5px;
                           border:none; }
  pre#raw { font-family:var(--mono); font-size:10.5px; line-height:1.5; color:var(--dim);
            background:#080c13; padding:16px 18px; overflow:auto; max-height:460px;
            border-radius:0 0 var(--r) var(--r); }
  .stepsv { counter-reset:s; }
  .stepv { display:flex; gap:14px; padding:10px 0; border-bottom:1px solid var(--line);
           line-height:1.6; }
  .stepv:last-child { border-bottom:none; }
  .stepv::before { counter-increment:s; content:counter(s);
      min-width:26px; height:26px; border-radius:50%; background:var(--grad);
      color:#06121f; display:grid; place-items:center; font-weight:800; font-size:12px;
      margin-top:2px; }
  a { color:var(--cyan); }
</style></head>
<body><div class="wrap">

  <div class="topbar pop">
    <div class="logo">
      <svg width="32" height="32" viewBox="0 0 64 64" aria-label="AiriBrain logo">
        <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#3fd0ff"/><stop offset="1" stop-color="#2f6fe0"/>
        </linearGradient></defs>
        <rect x="2" y="2" width="60" height="60" rx="15" fill="url(#lg)"/>
        <path d="M19 45 L32 17 L45 45" fill="none" stroke="#fff" stroke-width="5"
              stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M25.5 36.5 H38.5" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round"/>
        <circle cx="32" cy="17" r="4.2" fill="#fff"/><circle cx="19" cy="45" r="4.2" fill="#fff"/>
        <circle cx="45" cy="45" r="4.2" fill="#fff"/>
        <circle cx="32" cy="17" r="1.7" fill="#2f6fe0"/><circle cx="19" cy="45" r="1.7" fill="#2f6fe0"/>
        <circle cx="45" cy="45" r="1.7" fill="#2f6fe0"/>
        <circle cx="49" cy="13.5" r="2.6" fill="#fff" opacity=".95"/>
        <circle cx="54" cy="20" r="1.7" fill="#fff" opacity=".7"/>
      </svg>
      <span>Airi<span style="background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent">Brain</span></span></div>
    <div class="mode"><span class="led __LEDCLASS__"></span>__MODE__</div>
    <div class="layers">
      <button class="lbtn on" id="lb1" onclick="showLayer(1)">1 · Decision</button>
      <button class="lbtn" id="lb2" onclick="showLayer(2)" disabled>2 · Evidence</button>
      <button class="lbtn" id="lb3" onclick="showLayer(3)">3 · Engine</button>
    </div>
  </div>

  <!-- ================= LAYER 1 ================= -->
  <div class="layer on" id="layer1">
    <div class="cockpit">
      <div class="card pop" style="animation-delay:.05s">
        <div class="card-head">Submit a deal <span class="sub">inputs</span></div>
        <div class="card-body">
          <div class="grid2">
            <div><label>Company</label><input id="company" placeholder="Acme AI"></div>
            <div><label>Ask</label><input id="ask" placeholder="$100,000 SAFE"></div>
          </div>
          <label>One-liner</label><input id="one_liner" placeholder="What does it do?">

          <div class="drop" id="drop">
            <div class="icon">⇪</div>
            <div class="big">Drop the data room here</div>
            <div class="small">pitch deck <b>PDF</b> · financials <b>Excel / CSV</b> · notes <b>MD / TXT / JSON</b><br>or click to browse</div>
            <input type="file" id="file-in" multiple hidden
                   accept=".pdf,.csv,.xlsx,.xlsm,.md,.txt,.json">
          </div>
          <div class="chips" id="chips"></div>

          <div class="row">
            <button class="btn btn-primary" id="run">Run audit →</button>
            <button class="btn" id="load">Try the sample</button>
          </div>
          <div class="row"><span class="hint">Every claim in the materials gets audited —
            recomputed from the raw numbers first, checked by AI + web search second.</span></div>
        </div>
      </div>

      <div class="card pop" style="animation-delay:.12s">
        <div class="card-head">Decision <span class="sub">outputs</span></div>
        <div id="progress" style="display:none">
          <div class="steps">
            <div class="stepp" data-s="ingest"><div class="bub">1</div><div class="lbl">Ingest</div></div>
            <div class="stepp" data-s="claims"><div class="bub">2</div><div class="lbl">Claims</div></div>
            <div class="stepp" data-s="evidence"><div class="bub">3</div><div class="lbl">Evidence</div></div>
            <div class="stepp" data-s="scoring"><div class="bub">4</div><div class="lbl">Scoring</div></div>
            <div class="stepp" data-s="memo"><div class="bub">5</div><div class="lbl">Memo</div></div>
          </div>
          <div class="lastline" id="lastline">warming up…</div>
        </div>
        <div id="out">
          <div class="placeholder">
            <div class="icon">◎</div>
            <div style="font-weight:650; color:var(--dim)">No audit yet</div>
            <div class="hint" style="margin-top:6px">Drop a data room (or try the sample) and run —<br>
              the verdict lands here, the proof in layer 2, the machinery in layer 3.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ================= LAYER 2 ================= -->
  <div class="layer" id="layer2"><div class="stack" id="l2body"></div></div>

  <!-- ================= LAYER 3 ================= -->
  <div class="layer" id="layer3">
    <div class="stack">
      <div class="card">
        <div class="card-head">Audit stream <span class="sub">raw log, timestamped</span></div>
        <div id="console"><div class="hint" style="padding:6px 2px">No run yet — the full machine log streams here during an audit.</div></div>
      </div>

      <div class="card">
        <div class="card-head">How a verdict earns trust <span class="sub">verification hierarchy</span></div>
        <div class="card-body spec">
          <div class="stepsv">
            <div class="stepv"><div><b>Recompute the numbers.</b> Anything derivable from the
              founder's own raw data is recomputed — growth from the revenue file, stated
              figures against the metrics sheet. Pure arithmetic, never overturned later.
              Numbers are checked, not believed.</div></div>
            <div class="stepv"><div><b>Cross-check the documents.</b> Each quantitative claim is
              compared to its keyword-adjacent figure in the data room: within 10% →
              <span class="chip chip-verified">✓ VERIFIED</span> · beyond 25% →
              <span class="chip chip-contradicted">✕ CONTRADICTED</span> · between →
              <span class="chip chip-corroborated">◐ CORROBORATED</span>.</div></div>
            <div class="stepv"><div><b>Ask AI + the open web</b> (live mode). Claims the rules
              can't reach — market sizes, competitors, team backgrounds — go to Claude with
              the full data room and live web search; verdicts come back with reasoning and
              citations. <span class="chip chip-unsupported">! UNSUPPORTED</span> stays a
              legitimate answer, so nothing gets blessed on vibes.</div></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-head">The scoring model <span class="sub">deterministic · zero LLM · inspectable</span></div>
        <div class="card-body spec">
          Six dimensions, each 0–100 from the evidence table
          (<b>verified 100 · corroborated 75 · unsupported 45 · contradicted 0</b>, averaged),
          plus hard-metric adjustments (gross margin ≥70% +10 · LTV/CAC ≥3× +10 ·
          recomputed MoM ≥15% +10 · retention ≥90% +5 · short runway −10).
          <table class="wtable"><tr>
            <th>team</th><th>traction</th><th>market</th><th>product</th><th>economics</th><th>integrity</th></tr>
            <tr><td>20%</td><td>25%</td><td>15%</td><td>10%</td><td>20%</td><td>10%</td></tr>
          </table>
          <span class="f">integrity = 100 − 35 × contradicted − 50 × (unsupported ⁄ total claims)</span>
          <span class="f">composite = Σ(dimension × weight) × (0.70 + 0.30 × integrity⁄100)</span>
          Integrity counts twice on purpose — as a dimension <i>and</i> as a trust multiplier:
          a founder who inflates one number inflates others.
          Bands: <b>≥70 INVEST</b> · <b>50–70 INVEST WITH CONDITIONS</b> · <b>&lt;50 DECLINE</b>.
        </div>
      </div>

      <div class="card">
        <div class="card-head">Raw decision data <span class="sub">
          <a id="dl" download="decision.json">download ⭳</a></span></div>
        <pre id="raw">// run an audit to populate</pre>
      </div>
    </div>
  </div>

</div>
<script>
const SAMPLE = __SAMPLE__;
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ICON = {verified:'✓', corroborated:'◐', unsupported:'!', contradicted:'✕'};
const sid = id => String(id).split('-')[0];  // "C01-70a5" → "C01" for display
let T0 = null, RESULT = null, FILTER = '', FILES = [], sampleMode = false;

/* ---------- layers ---------- */
function showLayer(n) {
  for (const i of [1,2,3]) {
    $('layer'+i).classList.toggle('on', i === n);
    $('lb'+i).classList.toggle('on', i === n);
  }
  window.scrollTo({top:0});
}
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === '1') showLayer(1);
  if (e.key === '2' && !$('lb2').disabled) showLayer(2);
  if (e.key === '3') showLayer(3);
});

/* ---------- files ---------- */
const drop = $('drop'), fin = $('file-in');
drop.onclick = () => fin.click();
drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
drop.ondragleave = () => drop.classList.remove('over');
drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over');
                     addFiles(e.dataTransfer.files); };
fin.onchange = () => addFiles(fin.files);
function addFiles(list) {
  sampleMode = false;
  for (const f of list) FILES.push(f);
  renderChips();
}
function typeOf(name) {
  const ext = name.split('.').pop().toUpperCase();
  return ext.length <= 4 ? ext : 'FILE';
}
function renderChips() {
  $('chips').innerHTML = FILES.map((f, i) =>
    '<span class="fchip"><span class="type">' + typeOf(f.name) + '</span>' + esc(f.name) +
    '<button class="x" onclick="rmFile(' + i + ')" title="remove">×</button></span>').join('') +
    (sampleMode ? ['deck.md','metrics.json','revenue.csv','qa.json'].map(n =>
      '<span class="fchip"><span class="type">SAMPLE</span>' + n + '</span>').join('') : '');
}
function rmFile(i) { FILES.splice(i, 1); renderChips(); }

$('load').onclick = () => {
  sampleMode = true; FILES = [];
  $('company').value = SAMPLE.company.company;
  $('one_liner').value = SAMPLE.company.one_liner;
  $('ask').value = SAMPLE.company.ask;
  renderChips();
};

/* ---------- console ---------- */
function ts() {
  const s = (performance.now() - T0) / 1000;
  return '[' + s.toFixed(1).padStart(5, '0') + 's]';
}
function cline(html, cls) {
  const c = $('console');
  const d = document.createElement('div');
  if (cls) d.className = cls;
  d.innerHTML = '<span class="t">' + ts() + '</span>' + html;
  c.appendChild(d);
  c.scrollTop = c.scrollHeight;
}

/* ---------- progress ---------- */
const ORDER = ['ingest','claims','evidence','scoring','memo'];
function setStage(s) {
  const i = ORDER.indexOf(s);
  if (i < 0) return;
  document.querySelectorAll('.stepp').forEach((el, j) => {
    el.classList.toggle('act', j === i);
    el.classList.toggle('did', j < i);
    if (j < i) el.querySelector('.bub').textContent = '✓';
  });
}

/* ---------- run ---------- */
$('run').onclick = async () => {
  if (!sampleMode && !FILES.length) {
    drop.classList.add('over');
    setTimeout(() => drop.classList.remove('over'), 900);
    return;
  }
  $('run').disabled = true;
  $('run').textContent = 'Auditing…';
  $('console').innerHTML = '';
  $('out').innerHTML = '';
  $('progress').style.display = 'block';
  document.querySelectorAll('.stepp').forEach((el, j) => {
    el.classList.remove('act','did');
    el.querySelector('.bub').textContent = j + 1;
  });
  $('lb2').disabled = true;
  T0 = performance.now();

  const fd = new FormData();
  for (const k of ['company','one_liner','ask']) fd.append(k, $(k).value);
  if (sampleMode) fd.append('use_sample', '1');
  else for (const f of FILES) fd.append('files', f, f.name);

  const r = await fetch('/api/run', {method:'POST', body: fd});
  const {run_id} = await r.json();
  const es = new EventSource('/api/stream/' + run_id);

  es.addEventListener('log', e => {
    const d = JSON.parse(e.data);
    setStage(d.stage);
    $('lastline').textContent = d.msg;
    const hi = /contradiction|composite|claims extracted/.test(d.msg) ? ' msg-hi' : '';
    cline('<span class="stage-tag">' + d.stage.toUpperCase() + '</span><span class="msg' + hi + '">' + esc(d.msg) + '</span>');
  });
  es.addEventListener('claim', e => {
    const d = JSON.parse(e.data);
    setStage('evidence');
    const bad = d.status === 'contradicted';
    $('lastline').innerHTML = '<span class="st st-' + d.status + '">' + ICON[d.status] + ' ' +
      d.status + '</span> — ' + esc(d.text);
    cline('<span class="stage-tag">EVIDENCE</span>' +
         '<span class="st st-' + d.status + '">' + ICON[d.status] + ' ' +
         d.status.toUpperCase().padEnd(12,' ') + '</span> ' +
         '<span class="msg' + (bad ? ' msg-hi' : '') + '">' + esc(sid(d.id)) + ' — ' + esc(d.text) + '</span>',
         bad ? 'flash-bad' : '');
  });
  es.addEventListener('done', async e => {
    const d = JSON.parse(e.data);
    es.close();
    setStage('memo');
    document.querySelectorAll('.stepp').forEach(el => {
      el.classList.remove('act'); el.classList.add('did');
      el.querySelector('.bub').textContent = '✓'; });
    RESULT = await (await fetch(d.data_url)).json();
    $('run').disabled = false;
    $('run').textContent = 'Run audit →';
    setTimeout(() => { $('progress').style.display = 'none'; renderL1(); }, 500);
    $('lb2').disabled = false;
    renderL2(FILTER = '');
    renderL3();
  });
  es.addEventListener('fail', e => {
    es.close();
    $('run').disabled = false;
    $('run').textContent = 'Run audit →';
    $('lastline').innerHTML = '<span class="st st-contradicted">Error: ' +
      esc(JSON.parse(e.data).msg) + '</span>';
  });
};

/* ---------- layer 1 render ---------- */
function counts() {
  const c = {verified:0, corroborated:0, unsupported:0, contradicted:0};
  for (const e of RESULT.evidence) c[e.status]++;
  return c;
}
function toneOf(d) { return d === 'INVEST' ? 'good' : d === 'DECLINE' ? 'crit' : 'warn'; }
function ringColor(t) { return t === 'good' ? 'var(--good)' : t === 'crit' ? 'var(--crit)' : 'var(--warn)'; }

function renderL1() {
  const D = RESULT.decision, c = counts(), tone = toneOf(D.decision);
  const evById = Object.fromEntries(RESULT.evidence.map(e => [e.claim_id, e]));
  const bad = RESULT.claims.filter(cl => evById[cl.id].status === 'contradicted');
  const R = 74, CIRC = 2 * Math.PI * R;

  const tiles = [['', 'Claims audited', RESULT.claims.length],
    ['verified','Verified',c.verified], ['corroborated','Corroborated',c.corroborated],
    ['unsupported','Unsupported',c.unsupported], ['contradicted','Contradicted',c.contradicted]]
    .map(([s, lab, v], i) =>
      '<button class="tile pop" style="animation-delay:' + (0.5 + i*0.07) + 's" onclick="gotoEvidence(\'' + s + '\')">' +
      '<div class="lab">' + lab + '</div><div class="val">' + v + '</div>' +
      '<div class="go">See evidence →</div></button>').join('');

  const dims = D.dimensions.map(d =>
    '<div class="dim" onclick="gotoEvidence(\'\')" title="Full rationale in layer 2">' +
    '<span class="name">' + esc(d.dimension) + '</span>' +
    '<span class="track2"><span class="fill" data-w="' + d.score + '"></span></span>' +
    '<span class="num">' + Math.round(d.score) + '<i> /100 · w' + Math.round(d.weight*100) + '%</i></span>' +
    '</div>').join('');

  const findings = bad.map(cl => {
    const e = evById[cl.id];
    const delta = e.stated_value ?
      '<div class="delta">stated ' + esc(e.stated_value) + ' → found ' + esc(e.computed_value) + '</div>' : '';
    return '<div class="finding pop" style="animation-delay:.9s" onclick="gotoEvidence(\'contradicted\')">' +
      '<span class="chip chip-contradicted">✕ CONTRADICTED</span>' +
      '<div class="body"><b>' + esc(cl.text) + '</b>' + esc(e.detail) + delta +
      '<div class="hint" style="margin-top:6px">Tap for the full evidence →</div></div></div>';
  }).join('');

  $('out').innerHTML =
    '<div class="hero">' +
      '<div class="ring pop">' +
        '<svg width="168" height="168" viewBox="0 0 168 168">' +
        '<circle class="track" cx="84" cy="84" r="' + R + '" fill="none" stroke-width="11"/>' +
        '<circle class="arc" id="arc" cx="84" cy="84" r="' + R + '" fill="none" stroke-width="11" ' +
        'stroke="' + ringColor(tone) + '" stroke-dasharray="' + CIRC + '" stroke-dashoffset="' + CIRC + '"/>' +
        '</svg>' +
        '<div class="mid"><div><div class="val" id="odo">0.0</div>' +
        '<div class="cap">COMPOSITE / 100</div></div></div>' +
      '</div>' +
      '<div class="verdict-side">' +
        '<div class="stamp tone-' + tone + '" id="stamp">' + D.decision.replaceAll('_',' ') + '</div>' +
        '<div class="v-meta"><b>' + esc(RESULT.company) + '</b> · asked ' + esc(RESULT.ask) +
        (D.check_size ? '<br>Check on approval: <b>$' + D.check_size.toLocaleString() + '</b>' :
                        '<br>No check at this score.') +
        '<br>Integrity multiplier ×' + D.integrity_multiplier + '</div>' +
      '</div>' +
    '</div>' +
    '<div class="summary pop" style="animation-delay:.35s">' + esc(D.summary) + '</div>' +
    '<div class="tiles">' + tiles + '</div>' +
    '<div class="dims">' + dims + '</div>' +
    findings +
    '<div class="hint" style="padding:0 20px 20px">Deep-dive: ' +
    '<a href="#" onclick="showLayer(2);return false">layer 2 — evidence</a> · ' +
    '<a href="#" onclick="showLayer(3);return false">layer 3 — engine</a> · ' +
    '<a href="' + RESULT.memo_url + '" target="_blank">standalone memo ↗</a></div>';

  // animations: ring sweep + odometer + meters + stamp
  const target = D.composite;
  requestAnimationFrame(() => {
    $('arc').style.transition = 'stroke-dashoffset 1.4s cubic-bezier(.3,.7,.3,1)';
    $('arc').style.strokeDashoffset = CIRC * (1 - target / 100);
    document.querySelectorAll('.fill').forEach(f => f.style.width = f.dataset.w + '%');
  });
  const t0 = performance.now(), dur = 1400;
  (function tick(now) {
    const p = Math.min(1, (now - t0) / dur);
    $('odo').textContent = (target * (1 - Math.pow(1 - p, 3))).toFixed(1);
    if (p < 1) requestAnimationFrame(tick);
  })(t0);
  $('stamp').classList.add('on');
}
function gotoEvidence(f) { renderL2(FILTER = f); showLayer(2); }

/* ---------- layer 2 render ---------- */
function chartSVG() {
  const S = RESULT.revenue_series;
  if (!S || S.length < 2) return '<div class="hint">No revenue series submitted — nothing to recompute against.</div>';
  const W=940,H=250,PL=58,PR=90,PT=20,PB=32;
  const revs = S.map(p => p.revenue), top = Math.max(...revs) * 1.15, n = S.length;
  const x = i => PL + (W-PL-PR) * (i/(n-1));
  const y = v => PT + (H-PT-PB) * (1 - v/top);
  const step = top > 30000 ? 10000 : 5000;
  let grid = '', ticks = '';
  for (let g = step; g < top; g += step) {
    grid += '<line x1="'+PL+'" y1="'+y(g)+'" x2="'+(W-PR)+'" y2="'+y(g)+'" stroke="var(--line)" stroke-width="1"/>';
    ticks += '<text x="'+(PL-8)+'" y="'+(y(g)+4)+'" fill="var(--faint)" font-size="11" text-anchor="end" font-family="var(--mono)">'+(g/1000)+'K</text>';
  }
  const xl = S.map((p,i) => '<text x="'+x(i)+'" y="'+(H-8)+'" fill="var(--faint)" font-size="10.5" text-anchor="middle" font-family="var(--mono)">'+esc(p.month)+'</text>').join('');
  const pts = S.map((p,i) => x(i)+','+y(p.revenue)).join(' ');
  let claimed = '', legendClaimed = '';
  const g = RESULT.evidence.find(e => e.status === 'contradicted' &&
      e.method.startsWith('recomputed') && e.stated_value);
  if (g) {
    const pct = parseFloat(g.stated_value), r = 1 + pct/100;
    let cpts = [], exit = null;
    for (let i = 0; i < n; i++) {
      const v = revs[0] * Math.pow(r, i);
      if (v <= top) cpts.push([x(i), y(v)]);
      else {
        const prev = revs[0] * Math.pow(r, i-1);
        const f = (top - prev) / (v - prev);
        exit = [x(i-1) + f*(x(i)-x(i-1)), PT];
        cpts.push(exit); break;
      }
    }
    const line = cpts.map(p => p[0]+','+p[1]).join(' ');
    const lab = exit
      ? '<text x="'+Math.min(exit[0]+8, W-6)+'" y="'+(PT+12)+'" fill="var(--dim)" font-size="11" font-weight="650" font-family="var(--mono)">claimed '+pct+'%/mo — off the chart</text>'
      : '';
    claimed = '<polyline points="'+line+'" fill="none" stroke="var(--claimed)" stroke-width="2" opacity=".85"/>' + lab;
    legendClaimed = '<span class="key"><span class="swatch" style="background:var(--claimed)"></span>claimed trajectory ('+pct+'% MoM)</span>';
  }
  return '<div class="legend"><span class="key"><span class="swatch" style="background:var(--blue)"></span>actual (submitted)</span>' + legendClaimed + '</div>' +
    '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Actual revenue vs claimed trajectory" style="width:100%;height:auto;display:block">' +
    grid + '<line x1="'+PL+'" y1="'+(H-PB)+'" x2="'+(W-PR)+'" y2="'+(H-PB)+'" stroke="var(--line)" stroke-width="1"/>' +
    ticks + xl + claimed +
    '<polyline points="'+pts+'" fill="none" stroke="var(--blue)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>' +
    '<circle cx="'+x(n-1)+'" cy="'+y(revs[n-1])+'" r="5.5" fill="var(--blue)" stroke="var(--card)" stroke-width="2"/>' +
    '<text x="'+(x(n-1)+11)+'" y="'+(y(revs[n-1])+4)+'" fill="var(--ink)" font-size="12" font-weight="700" font-family="var(--mono)">$'+revs[n-1].toLocaleString()+'</text></svg>';
}

function renderL2(filter) {
  const D = RESULT.decision;
  const evById = Object.fromEntries(RESULT.evidence.map(e => [e.claim_id, e]));
  const statuses = ['','verified','corroborated','unsupported','contradicted'];
  const fbtns = statuses.map(s =>
    '<button class="fbtn' + (s === filter ? ' on' : '') + '" onclick="renderL2(FILTER=\'' + s + '\')">' +
    (s ? ICON[s] + ' ' + s[0].toUpperCase() + s.slice(1) : 'All') + '</button>').join('');

  const rows = RESULT.claims
    .filter(cl => !filter || evById[cl.id].status === filter)
    .map(cl => {
      const e = evById[cl.id];
      const sv = e.stated_value ?
        '<div class="sv">stated <b>' + esc(e.stated_value) + '</b> · found <b>' + esc(e.computed_value) + '</b></div>' : '';
      const cites = (e.citations || []).length ?
        '<div class="cites">' + e.citations.slice(0,4).map(c =>
          '<a href="' + esc(c.url) + '" target="_blank" rel="noopener">' +
          esc((c.title || c.url).slice(0,52)) + ' ↗</a>').join('') + '</div>' : '';
      return '<tr' + (e.status === 'contradicted' ? ' class="row-bad"' : '') + '>' +
        '<td class="cid">' + esc(sid(cl.id)) + '</td>' +
        '<td><div class="claim-text">' + esc(cl.text) + '</div>' +
        '<div class="prov">' + esc(cl.provenance) + '</div></td>' +
        '<td><span class="chip chip-' + e.status + '">' + ICON[e.status] + ' ' +
        e.status.toUpperCase() + '</span><div class="conf">confidence ' +
        Math.round(e.confidence*100) + '%</div></td>' +
        '<td><div class="detail">' + esc(e.detail) + '</div>' + sv + cites +
        '<div class="prov">' + esc(e.method) + '</div></td></tr>';
    }).join('') ||
    '<tr><td colspan="4" class="hint" style="padding:20px 0">No claims with this status.</td></tr>';

  const rats = D.dimensions.map(d =>
    '<details class="rat"><summary>' +
    '<span style="font-size:12.5px;font-weight:650;color:var(--dim);text-transform:capitalize">' + esc(d.dimension) + '</span>' +
    '<span class="track2"><span class="fill" style="width:' + d.score + '%"></span></span>' +
    '<span class="num" style="font-family:var(--mono);font-size:12px;font-weight:700;text-align:right">' +
    Math.round(d.score) + '<i style="color:var(--faint);font-style:normal;font-size:9.5px;font-weight:500"> /100 · w' +
    Math.round(d.weight*100) + '%</i></span></summary>' +
    '<ul>' + d.rationale.map(r => '<li>' + esc(r) + '</li>').join('') + '</ul></details>').join('');

  $('l2body').innerHTML =
    '<div class="card pop"><div class="card-head">Claim-by-claim audit <span class="sub">every verdict traceable</span></div>' +
    '<div class="filters">' + fbtns + '</div>' +
    '<div class="card-body"><table><thead><tr><th>id</th><th>claim</th><th>status</th><th>evidence</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table></div></div>' +
    '<div class="card pop" style="animation-delay:.08s"><div class="card-head">Claimed vs actual <span class="sub">the chart is the evidence</span></div>' +
    '<div class="card-body">' + chartSVG() + '</div></div>' +
    '<div class="card pop" style="animation-delay:.14s"><div class="card-head">Score rationale by dimension</div>' +
    '<div class="card-body">' + rats + '</div></div>' +
    '<div class="card pop" style="animation-delay:.2s"><div class="card-head">Conditions <span class="sub">auto-generated founder question list</span></div>' +
    '<div class="card-body"><ol class="conds">' +
    (D.conditions.map(x => '<li>' + esc(x) + '</li>').join('') || '<li>None.</li>') + '</ol></div></div>' +
    '<div class="card pop" style="animation-delay:.26s"><div class="card-head">Key risks</div>' +
    '<div class="card-body"><ul class="risks">' +
    (D.key_risks.map(x => '<li>' + esc(x) + '</li>').join('') || '<li>None identified.</li>') + '</ul></div></div>';
}

/* ---------- layer 3 render ---------- */
function renderL3() {
  const txt = JSON.stringify(RESULT, null, 2);
  $('raw').textContent = txt;
  $('dl').href = URL.createObjectURL(new Blob([txt], {type:'application/json'}));
}
</script>
</body></html>"""
