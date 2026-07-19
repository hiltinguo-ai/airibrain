"""The AiriBrain app — three layers, warm and human.

Layer 1 · DECISION — drop in a deck (PDF) + financials (Excel/CSV), get a verdict.
Layer 2 · EVIDENCE — the proof behind the verdict.
Layer 3 · ENGINE   — the algorithm, the live log, the raw data.

Design: warm paper, editorial serif headlines (Fraunces), handwritten notes
(Caveat), tactile press-down buttons, sticky-note tiles with a slight tilt,
playful spring animations (disabled under prefers-reduced-motion). The engine
log is the one intentionally dark element — a real terminal inside a human page.
"""

PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AiriBrain — evidence-backed decisions</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect x='2' y='2' width='60' height='60' rx='15' fill='%232f5fe0'/%3E%3Cpath d='M19 45 L32 17 L45 45' fill='none' stroke='%23fff8ec' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3Cpath d='M25.5 36.5 H38.5' fill='none' stroke='%23fff8ec' stroke-width='5' stroke-linecap='round'/%3E%3Ccircle cx='32' cy='17' r='4.2' fill='%23fff8ec'/%3E%3Ccircle cx='19' cy='45' r='4.2' fill='%23fff8ec'/%3E%3Ccircle cx='45' cy='45' r='4.2' fill='%23fff8ec'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500..900;1,9..144,500..900&family=Caveat:wght@500;700&display=swap" rel="stylesheet">
<style>
  :root {
    color-scheme: light;
    --paper:#f7f2e8; --card:#fffdf7; --card-2:#f4eee0;
    --line:#e5dcc8; --line-2:#d4c8ac;
    --ink:#2a251c; --dim:#6b6355; --faint:#a39a87;
    --blue:#2f5fe0; --blue-deep:#1f45b8; --blue-track:#e9e2cf;
    --grad:#2f5fe0;
    --good:#217a45; --warn:#b3781a; --crit:#c2402d; --claimed:#d95926;
    --serif:"Fraunces", Georgia, serif;
    --hand:"Caveat", cursive;
    --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
    --r:18px;
    --shadow:0 1px 2px rgba(60,50,30,.06), 0 8px 24px -12px rgba(60,50,30,.18);
  }
  * { box-sizing:border-box; margin:0; }
  html { scroll-behavior:smooth; }
  body { font-family:system-ui,-apple-system,"Segoe UI",sans-serif;
         background:var(--paper); color:var(--ink); min-height:100vh;
         padding:26px 20px 80px; }
  .wrap { max-width:1180px; margin:0 auto; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation:none !important; transition:none !important; }
  }

  /* ---------- top bar ---------- */
  .topbar { display:flex; align-items:center; gap:16px; flex-wrap:wrap;
            padding:6px 4px 20px; margin-bottom:8px;
            border-bottom:2px solid var(--ink); }
  .logo { display:flex; align-items:center; gap:11px; font-family:var(--serif);
          font-weight:700; font-size:21px; letter-spacing:-.01em; }
  .logo svg { transition:transform .4s cubic-bezier(.3,1.6,.4,1); }
  .logo:hover svg { transform:rotate(-8deg) scale(1.06); }
  .mode { display:flex; align-items:center; gap:7px; font-family:var(--hand);
          font-size:16px; color:var(--dim); transform:rotate(-1.5deg); }
  .led { width:9px; height:9px; border-radius:50%; }
  .led-live { background:var(--good); animation:blink 2.4s ease-in-out infinite; }
  .led-mock { background:var(--warn); }
  @keyframes blink { 50% { opacity:.35; } }

  .layers { margin-left:auto; display:flex; gap:6px; }
  .lbtn { font:inherit; font-size:13.5px; font-weight:650; padding:9px 16px 11px;
          border:none; background:transparent; color:var(--dim); cursor:pointer;
          border-radius:10px; position:relative; transition:color .2s; }
  .lbtn:hover:not(:disabled):not(.on) { color:var(--ink); }
  .lbtn.on { color:var(--ink);
    background-image:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 8" preserveAspectRatio="none"><path d="M2 5 Q 15 1, 28 5 T 52 5 T 76 5 T 98 4" fill="none" stroke="%232f5fe0" stroke-width="2.6" stroke-linecap="round"/></svg>');
    background-repeat:no-repeat; background-position:center bottom 2px; background-size:92% 7px; }
  .lbtn:disabled { opacity:.35; cursor:default; }

  .layer { display:none; }
  .layer.on { display:block; animation:fadein .35s ease-out; }
  @keyframes fadein { from { opacity:0; transform:translateY(10px);} to { opacity:1; } }

  /* ---------- hero ---------- */
  .hello { padding:34px 4px 26px; }
  .hello h1 { font-family:var(--serif); font-weight:640; font-size:clamp(30px,4.6vw,46px);
              line-height:1.12; letter-spacing:-.015em; max-width:640px; }
  .hello h1 em { font-style:italic; font-weight:600; color:var(--blue);
                 position:relative; white-space:nowrap; }
  .hello h1 em::after { content:""; position:absolute; left:0; right:0; bottom:-6px; height:8px;
    background:url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 10" preserveAspectRatio="none"><path d="M3 6 Q 25 2, 50 6 T 100 6 T 150 6 T 197 5" fill="none" stroke="%232f5fe0" stroke-width="3" stroke-linecap="round" opacity=".55"/></svg>') no-repeat center/100% 100%;
    transform:scaleX(0); transform-origin:left; animation:draw .7s ease-out .5s forwards; }
  @keyframes draw { to { transform:scaleX(1); } }
  .hello .tag { font-family:var(--hand); font-size:19px; color:var(--dim);
                margin-top:12px; transform:rotate(-1deg); display:inline-block; }

  /* ---------- cards ---------- */
  .card { background:var(--card); border:1.5px solid var(--line-2); border-radius:var(--r);
          box-shadow:var(--shadow); }
  .stack > * + * { margin-top:16px; }
  .card-head { display:flex; align-items:baseline; gap:10px; padding:16px 22px 13px;
               border-bottom:1.5px dashed var(--line); font-family:var(--serif);
               font-weight:650; font-size:17px; letter-spacing:-.01em; }
  .card-head .sub { margin-left:auto; font-family:var(--hand); font-size:15px;
                    color:var(--faint); font-weight:500; }
  .card-body { padding:18px 22px; }
  .pop { animation:pop .5s cubic-bezier(.25,1.4,.4,1) backwards; }
  @keyframes pop { from { opacity:0; transform:scale(.97) translateY(10px);} to { opacity:1; } }

  /* ---------- layer 1 ---------- */
  .cockpit { display:grid; grid-template-columns:5fr 7fr; gap:16px; align-items:start; }
  @media (max-width:980px) { .cockpit { grid-template-columns:1fr; } }
  label { display:block; font-size:12px; font-weight:650; color:var(--dim);
          margin:14px 0 6px; }
  input { width:100%; background:#fff; color:var(--ink);
      border:1.5px solid var(--line-2); border-radius:11px; padding:10px 13px;
      font:inherit; font-size:14px; transition:all .2s; }
  input:focus { outline:none; border-color:var(--blue);
      box-shadow:0 0 0 3px rgba(47,95,224,.14); }
  .grid2 { display:grid; grid-template-columns:1.4fr 1fr; gap:0 12px; }

  .drop { margin-top:18px; border:2px dashed var(--line-2); border-radius:14px;
          padding:26px 18px; text-align:center; cursor:pointer; transition:all .25s;
          background:var(--card-2); }
  .drop:hover, .drop.over { border-color:var(--blue); background:#eef2ff; }
  .drop.over { transform:scale(1.015) rotate(.4deg); }
  .drop .big { font-size:14.5px; font-weight:650; }
  .drop .small { font-size:12.5px; color:var(--dim); margin-top:5px; line-height:1.5; }
  .drop .icon { font-size:26px; margin-bottom:8px; display:inline-block;
                animation:bob 2.6s ease-in-out infinite; }
  @keyframes bob { 50% { transform:translateY(-5px); } }
  .drop:hover .icon { animation:wiggle .5s ease-in-out; }
  @keyframes wiggle { 25% { transform:rotate(-9deg);} 75% { transform:rotate(9deg);} }
  .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
  .fchip { display:inline-flex; align-items:center; gap:8px; font-size:12.5px;
           background:#fff; border:1.5px solid var(--line-2); border-radius:999px;
           padding:6px 7px 6px 8px; animation:pop .35s backwards; }
  .fchip:nth-child(odd) { transform:rotate(-.6deg); }
  .fchip:nth-child(even) { transform:rotate(.6deg); }
  .fchip .type { font-family:var(--mono); font-size:9px; font-weight:800; color:#fff;
                 background:var(--blue); border-radius:6px; padding:3px 6px; }
  .fchip .x { width:18px; height:18px; border-radius:50%; border:none; cursor:pointer;
              background:var(--line); color:var(--dim); font-size:11px; line-height:1;
              display:grid; place-items:center; transition:all .15s; }
  .fchip .x:hover { background:var(--crit); color:#fff; transform:scale(1.15); }

  .row { display:flex; gap:12px; margin-top:20px; align-items:center; flex-wrap:wrap; }
  .btn { font:inherit; font-size:14px; font-weight:700; border-radius:12px;
         padding:12px 22px; cursor:pointer; transition:all .12s ease-out; }
  .btn-primary { background:var(--blue); border:none; color:#fff;
                 box-shadow:0 4px 0 var(--blue-deep); }
  .btn-primary:hover:not(:disabled) { transform:translateY(-2px);
                 box-shadow:0 6px 0 var(--blue-deep); }
  .btn-primary:active:not(:disabled) { transform:translateY(3px); box-shadow:0 1px 0 var(--blue-deep); }
  .btn:not(.btn-primary) { background:#fff; color:var(--ink); border:1.5px solid var(--ink);
                 box-shadow:0 3px 0 var(--ink); }
  .btn:not(.btn-primary):hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 5px 0 var(--ink); }
  .btn:not(.btn-primary):active:not(:disabled) { transform:translateY(2px); box-shadow:0 1px 0 var(--ink); }
  .btn:disabled { opacity:.5; cursor:default; transform:none !important; }
  .hint { font-size:12px; color:var(--faint); line-height:1.55; }

  /* progress steps */
  .steps { display:flex; gap:0; align-items:center; padding:24px 20px 6px; }
  .stepp { flex:1; text-align:center; position:relative; }
  .stepp .bub { width:36px; height:36px; border-radius:50%; margin:0 auto;
      display:grid; place-items:center; font-size:13.5px; font-weight:700;
      background:#fff; border:2px solid var(--line-2); color:var(--faint);
      transition:all .35s; position:relative; z-index:1; }
  .stepp .lbl { font-size:11px; color:var(--faint); margin-top:7px; font-weight:650; }
  .stepp::before { content:""; position:absolute; top:17px; left:-50%; width:100%;
      height:0; border-top:2.5px dotted var(--line-2); z-index:0; transition:border-color .35s; }
  .stepp:first-child::before { display:none; }
  .stepp.act .bub { border-color:var(--blue); color:var(--blue); background:#eef2ff;
      animation:hop .7s cubic-bezier(.3,1.6,.4,1) infinite alternate; }
  @keyframes hop { from { transform:translateY(0);} to { transform:translateY(-5px);} }
  .stepp.did .bub { background:var(--blue); border-color:var(--blue); color:#fff;
      animation:pip .35s cubic-bezier(.3,1.8,.4,1); }
  @keyframes pip { 50% { transform:scale(1.25); } }
  .stepp.did::before, .stepp.act::before { border-color:var(--blue); }
  .stepp.act .lbl, .stepp.did .lbl { color:var(--ink); }
  .lastline { font-size:13px; color:var(--dim); padding:16px 22px 20px; min-height:46px;
              text-align:center; }

  /* results */
  .placeholder { padding:66px 24px; text-align:center; color:var(--faint); }
  .placeholder .icon { font-size:34px; margin-bottom:12px; display:inline-block;
                       animation:bob 3s ease-in-out infinite; }
  .placeholder .hand-note { font-family:var(--hand); font-size:19px; color:var(--dim);
                            transform:rotate(-1.5deg); display:inline-block; margin-top:4px; }
  .hero { display:flex; align-items:center; justify-content:center; gap:40px;
          padding:30px 20px 6px; flex-wrap:wrap; }
  .ring { position:relative; width:172px; height:172px; }
  .ring svg { transform:rotate(-90deg); }
  .ring .track { stroke:var(--blue-track); }
  .ring .arc { stroke-linecap:round; transition:stroke-dashoffset 1.4s cubic-bezier(.3,.7,.3,1); }
  .ring .mid { position:absolute; inset:0; display:grid; place-items:center; text-align:center; }
  .ring .val { font-family:var(--serif); font-size:42px; font-weight:700; line-height:1;
               font-variant-numeric:tabular-nums; }
  .ring .cap { font-size:10px; color:var(--faint); margin-top:5px; font-weight:700;
               letter-spacing:.08em; }
  .verdict-side { text-align:left; max-width:380px; }
  .stamp { display:inline-block; padding:10px 24px; border:3px solid; border-radius:10px;
           font-family:var(--serif); font-size:19px; font-weight:750; letter-spacing:.03em;
           transform:scale(2.4) rotate(9deg); opacity:0; }
  .stamp.on { animation:stamp .5s cubic-bezier(.2,1.5,.35,1) .9s forwards; }
  @keyframes stamp { to { transform:scale(1) rotate(-2.5deg); opacity:1; } }
  .tone-good { color:var(--good); border-color:var(--good); background:rgba(33,122,69,.07); }
  .tone-warn { color:var(--warn); border-color:var(--warn); background:rgba(179,120,26,.08); }
  .tone-crit { color:var(--crit); border-color:var(--crit); background:rgba(194,64,45,.07); }
  .v-meta { font-size:13px; color:var(--dim); margin-top:14px; line-height:1.65; }
  .summary { font-size:14px; color:var(--dim); text-align:center; padding:16px 30px 4px;
             line-height:1.65; max-width:760px; margin:0 auto; }

  .tiles { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; padding:20px 22px 8px; }
  @media (max-width:760px) { .tiles { grid-template-columns:repeat(2,1fr); } }
  .tile { background:#fffef9; border:1.5px solid var(--line-2); border-radius:12px;
          padding:13px 14px; cursor:pointer; font:inherit; color:inherit; text-align:left;
          transition:all .25s cubic-bezier(.3,1.4,.4,1); box-shadow:0 2px 0 var(--line-2); }
  .tile:nth-child(odd) { transform:rotate(-.8deg); }
  .tile:nth-child(even) { transform:rotate(.8deg); }
  .tile:hover { transform:rotate(0) translateY(-4px); border-color:var(--blue);
                box-shadow:0 6px 0 var(--blue-track); }
  .tile .lab { font-size:11px; font-weight:650; color:var(--dim); }
  .tile .val { font-family:var(--serif); font-size:27px; font-weight:700; margin-top:2px; }
  .tile .go { font-size:10.5px; color:var(--faint); margin-top:4px; transition:color .2s; }
  .tile:hover .go { color:var(--blue); }

  .dims { padding:8px 22px 18px; }
  .dim { display:grid; grid-template-columns:96px 1fr 92px; gap:12px; align-items:center;
         padding:7px 8px; cursor:pointer; border-radius:10px; transition:background .2s; }
  .dim:hover { background:var(--card-2); }
  .dim .name { font-size:13px; font-weight:650; color:var(--dim); text-transform:capitalize; }
  .track2 { display:block; height:10px; border-radius:6px; background:var(--blue-track);
            overflow:hidden; }
  .fill { display:block; height:100%; background:var(--grad); border-radius:6px; width:0;
          transition:width 1s cubic-bezier(.2,.8,.3,1); }
  .dim .num { font-family:var(--mono); font-size:12px; font-weight:700; text-align:right;
              white-space:nowrap; }
  .dim .num i { color:var(--faint); font-style:normal; font-size:9.5px; font-weight:500; }

  .finding { margin:4px 22px 22px; padding:15px 17px; border:1.5px solid rgba(194,64,45,.5);
             border-radius:13px; background:#fdf1ee; cursor:pointer;
             display:flex; gap:12px; align-items:flex-start;
             transition:all .25s cubic-bezier(.3,1.4,.4,1); transform:rotate(-.4deg); }
  .finding:hover { transform:rotate(0) translateY(-3px); box-shadow:0 8px 20px -8px rgba(194,64,45,.35); }
  .finding .body { font-size:13.5px; color:var(--dim); line-height:1.55; }
  .finding .body b { color:var(--ink); display:block; margin-bottom:3px; }
  .finding .delta { color:var(--crit); font-family:var(--mono); font-size:12px; margin-top:4px; }

  /* ---------- chips ---------- */
  .chip { display:inline-flex; align-items:center; gap:5px; font-size:10.5px;
          font-weight:800; padding:3px 10px; border-radius:999px; border:1.5px solid;
          white-space:nowrap; letter-spacing:.03em; background:#fff; }
  .chip-verified     { color:var(--good); border-color:var(--good); }
  .chip-corroborated { color:var(--blue); border-color:var(--blue); }
  .chip-unsupported  { color:var(--warn); border-color:var(--warn); }
  .chip-contradicted { color:var(--crit); border-color:var(--crit); }

  /* ---------- layer 2 ---------- */
  .filters { display:flex; gap:8px; flex-wrap:wrap; padding:16px 22px 4px; }
  .fbtn { font:inherit; font-size:12.5px; font-weight:700; padding:7px 15px; border-radius:999px;
          border:1.5px solid var(--line-2); background:#fff; color:var(--dim);
          cursor:pointer; transition:all .2s; }
  .fbtn:hover { border-color:var(--ink); color:var(--ink); transform:translateY(-1px); }
  .fbtn.on { background:var(--ink); color:var(--paper); border-color:var(--ink); }
  table { width:100%; border-collapse:collapse; font-size:13.5px; }
  th { text-align:left; font-size:10.5px; text-transform:uppercase; letter-spacing:.08em;
       color:var(--faint); font-weight:700; padding:8px 10px 9px 0;
       border-bottom:1.5px solid var(--line); }
  td { padding:14px 10px 14px 0; border-bottom:1px solid var(--line); vertical-align:top; }
  tr:last-child td { border-bottom:none; }
  tbody tr { transition:background .15s; }
  tbody tr:hover { background:var(--card-2); }
  .row-bad { background:#fdf1ee; }
  .cid { font-family:var(--mono); font-size:10.5px; color:var(--faint); }
  .claim-text { font-weight:650; font-size:13.5px; line-height:1.45; }
  .prov { font-size:11px; color:var(--faint); margin-top:4px; }
  .detail { color:var(--dim); font-size:13px; line-height:1.55; }
  .sv { font-family:var(--mono); font-size:11.5px; margin-top:5px; color:var(--dim); }
  .sv b { color:var(--ink); }
  .conf { font-size:10.5px; color:var(--faint); margin-top:5px; }
  .cites { margin-top:7px; display:flex; flex-wrap:wrap; gap:6px; }
  .cites a { font-size:11.5px; font-weight:650; color:var(--blue); text-decoration:none;
             border:1.5px solid var(--line-2); border-radius:999px; padding:3px 11px;
             background:#fff; transition:all .2s; }
  .cites a:hover { border-color:var(--blue); transform:translateY(-1px); }
  details.rat { border-bottom:1px solid var(--line); padding:10px 0; }
  details.rat:last-child { border-bottom:none; }
  details.rat summary { cursor:pointer; display:grid;
      grid-template-columns:96px 1fr 92px; gap:12px; align-items:center; list-style:none; }
  details.rat summary::-webkit-details-marker { display:none; }
  details.rat ul { margin:10px 0 4px 110px; font-size:12.5px; color:var(--dim);
                   display:grid; gap:5px; padding-left:14px; line-height:1.5; }
  .legend { display:flex; gap:18px; font-size:12px; color:var(--dim); padding:0 0 10px; }
  .key { display:inline-flex; align-items:center; gap:7px; }
  .swatch { width:16px; height:4px; border-radius:2px; }
  ol.conds, ul.risks { margin-left:18px; font-size:13.5px; color:var(--dim);
                       display:grid; gap:9px; line-height:1.55; }

  /* ---------- layer 3 ---------- */
  #console { font-family:var(--mono); font-size:11.5px; line-height:1.9;
             padding:16px 18px; min-height:120px; max-height:420px; overflow-y:auto;
             background:#26211a; color:#cfc7b6;
             border-radius:0 0 calc(var(--r) - 2px) calc(var(--r) - 2px); }
  #console .t { color:#7d745f; margin-right:10px; }
  #console .stage-tag { color:#7d745f; display:inline-block; min-width:76px; }
  #console .msg { color:#cfc7b6; }
  #console .msg-hi { color:#fff8ec; }
  #console .hint { color:#7d745f; }
  #console .st-verified { color:#7fd99a; } #console .st-corroborated { color:#8db2ff; }
  #console .st-unsupported { color:#f0b95a; } #console .st-contradicted { color:#ff8a75; }
  #console div { animation:rise .2s ease-out; }
  @keyframes rise { from { opacity:0; transform:translateY(3px);} to { opacity:1; } }
  .st { font-weight:800; }
  .st-verified { color:var(--good); } .st-corroborated { color:var(--blue); }
  .st-unsupported { color:var(--warn); } .st-contradicted { color:var(--crit); }
  .flash-bad { animation:flash .9s ease-out 1; }
  @keyframes flash { 0% { background:rgba(255,90,60,.3);} 100% { background:transparent;} }
  .spec { font-size:13.5px; color:var(--dim); line-height:1.7; }
  .spec b { color:var(--ink); }
  .spec .f { font-family:var(--mono); font-size:12px; color:var(--blue-deep);
             background:var(--card-2); border:1.5px solid var(--line); border-radius:10px;
             padding:11px 15px; margin:9px 0; display:block; }
  .wtable td, .wtable th { padding:6px 12px 6px 0; font-family:var(--mono); font-size:12px;
                           border:none; }
  pre#raw { font-family:var(--mono); font-size:10.5px; line-height:1.5; color:#cfc7b6;
            background:#26211a; padding:16px 18px; overflow:auto; max-height:460px;
            border-radius:0 0 calc(var(--r) - 2px) calc(var(--r) - 2px); }
  .stepsv { counter-reset:s; }
  .stepv { display:flex; gap:14px; padding:10px 0; border-bottom:1px dashed var(--line);
           line-height:1.6; }
  .stepv:last-child { border-bottom:none; }
  .stepv::before { counter-increment:s; content:counter(s);
      min-width:27px; height:27px; border-radius:50%; background:var(--blue);
      color:#fff; display:grid; place-items:center; font-weight:800; font-size:12.5px;
      margin-top:2px; font-family:var(--serif); }
  a { color:var(--blue); }
</style></head>
<body><div class="wrap">

  <div class="topbar pop">
    <div class="logo">
      <svg width="34" height="34" viewBox="0 0 64 64" aria-label="AiriBrain logo">
        <rect x="2" y="2" width="60" height="60" rx="15" fill="#2f5fe0"/>
        <path d="M19 45 L32 17 L45 45" fill="none" stroke="#fff8ec" stroke-width="5"
              stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M25.5 36.5 H38.5" fill="none" stroke="#fff8ec" stroke-width="5" stroke-linecap="round"/>
        <circle cx="32" cy="17" r="4.2" fill="#fff8ec"/><circle cx="19" cy="45" r="4.2" fill="#fff8ec"/>
        <circle cx="45" cy="45" r="4.2" fill="#fff8ec"/>
        <circle cx="32" cy="17" r="1.7" fill="#2f5fe0"/><circle cx="19" cy="45" r="1.7" fill="#2f5fe0"/>
        <circle cx="45" cy="45" r="1.7" fill="#2f5fe0"/>
        <circle cx="49" cy="13.5" r="2.6" fill="#fff8ec" opacity=".95"/>
        <circle cx="54" cy="20" r="1.7" fill="#fff8ec" opacity=".7"/>
      </svg>
      <span>AiriBrain</span></div>
    <div class="mode"><span class="led __LEDCLASS__"></span>__MODE__</div>
    <div class="layers">
      <button class="lbtn on" id="lb1" onclick="showLayer(1)">1 · Decision</button>
      <button class="lbtn" id="lb2" onclick="showLayer(2)" disabled>2 · Evidence</button>
      <button class="lbtn" id="lb3" onclick="showLayer(3)">3 · Engine</button>
    </div>
  </div>

  <!-- ================= LAYER 1 ================= -->
  <div class="layer on" id="layer1">
    <div class="hello pop">
      <h1>Show us the deal.<br>We'll <em>check the math</em>.</h1>
      <div class="tag">every founder claim, audited — no vibes, just receipts ↓</div>
    </div>
    <div class="cockpit">
      <div class="card pop" style="animation-delay:.08s">
        <div class="card-head">Submit a deal <span class="sub">your inputs</span></div>
        <div class="card-body">
          <div class="grid2">
            <div><label>Company</label><input id="company" placeholder="Acme AI"></div>
            <div><label>Ask</label><input id="ask" placeholder="$100,000 SAFE"></div>
          </div>
          <label>One-liner</label><input id="one_liner" placeholder="What does it do?">

          <div class="drop" id="drop">
            <div class="icon">📂</div>
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

      <div class="card pop" style="animation-delay:.16s">
        <div class="card-head">Decision <span class="sub">what comes back</span></div>
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
            <div class="icon">☕️</div>
            <div style="font-weight:650; color:var(--dim)">Nothing to see yet</div>
            <div class="hand-note">run an audit and the verdict lands right here →</div>
            <div class="hint" style="margin-top:10px">the proof goes to layer 2, the machinery to layer 3</div>
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
        <div class="card-head">The scoring model <span class="sub">Claude IC partner · evidence-grounded</span></div>
        <div class="card-body spec">
          In <b>live mode</b>, Claude scores the deal as an investment-committee partner —
          reading the full audited evidence table and hard metrics, then returning six
          weighted dimension scores, an integrity multiplier, conditions, risks, and a
          written summary. The LLM does <i>not</i> get to invent a fourth outcome:
          <table class="wtable"><tr>
            <th>team</th><th>traction</th><th>market</th><th>product</th><th>economics</th><th>integrity</th></tr>
            <tr><td>20%</td><td>25%</td><td>15%</td><td>10%</td><td>20%</td><td>10%</td></tr>
          </table>
          <span class="f">bands enforced in code: ≥70 INVEST · 50–70 CONDITIONS · &lt;50 DECLINE</span>
          <span class="f">integrity_multiplier clamped to 0.70–1.00 · composite from LLM, band from rules</span>
          Mock mode (and any LLM failure) falls back to the deterministic rule scorer —
          same Decision shape, so the demo never dies mid-run.
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
        '<svg width="172" height="172" viewBox="0 0 172 172">' +
        '<circle class="track" cx="86" cy="86" r="' + R + '" fill="none" stroke-width="12"/>' +
        '<circle class="arc" id="arc" cx="86" cy="86" r="' + R + '" fill="none" stroke-width="12" ' +
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
    '<div class="hint" style="padding:0 22px 22px">Deep-dive: ' +
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
    '<span style="font-size:13px;font-weight:650;color:var(--dim);text-transform:capitalize">' + esc(d.dimension) + '</span>' +
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
