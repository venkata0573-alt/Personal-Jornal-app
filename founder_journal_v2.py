#!/usr/bin/env python3
"""
THE FOUNDER'S JOURNAL v2 — Self-Awareness Edition
==================================================
Local browser-based journal designed to expose subconscious patterns, not
collect feelings. Based on the 10-question framework that asks WHERE your
brain escapes and WHAT you avoid.

Usage:
    python3 founder_journal_v2.py

Opens http://localhost:8765 in your browser.
Data: ~/founder_journal_data/entries_v2.json   (separate from old data)
Press Ctrl+C to stop.
"""

import http.server, json, os, sys, webbrowser, threading, urllib.parse
from pathlib import Path
from datetime import datetime, timedelta

PORT = 8765
DATA_DIR = Path.home() / "founder_journal_data"
DATA_FILE = DATA_DIR / "entries_v2.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────────
# THE 10 QUESTIONS (with tooltip sample answers)
# ─────────────────────────────────────────────────────────────────
QUESTIONS = [
    # MORNING (5)
    {
        "id": "m1", "phase": "morning", "n": 1,
        "label": "Most important area to move today",
        "type": "select",
        "options": ["Money", "Skill", "Health", "Relationships", "Systems", "Research", "Execution", "Discipline", "Recovery"],
        "hint": "Pick ONE. Not 'all of them'. Force a single priority.",
        "examples": [
            "Money — follow up on Hilton lawn-mowing quote",
            "Skill — learn pricing/estimation before sending another quote",
            "Systems — organize my workflow so I stop wasting morning",
            "Execution — stop researching, ship the SOP today"
        ]
    },
    {
        "id": "m2", "phase": "morning", "n": 2,
        "label": "Why is this the highest priority today?",
        "type": "text",
        "hint": "Force your brain to justify the priority. If you can't justify it in 1 sentence, it's not the priority.",
        "examples": [
            "Because cash pressure is real and I need pipeline clarity",
            "Because without this skill I keep guessing on quotes",
            "Because my day collapses without structure"
        ]
    },
    {
        "id": "m3", "phase": "morning", "n": 3,
        "label": "One task I will REGRET not doing tonight",
        "type": "text",
        "hint": "Regret reveals truth. This is sharper than 'today's goal'. Write the thing that will sting at 10pm if undone.",
        "examples": [
            "I'll regret not sending the Ramada quote",
            "I'll regret not calling 3 hotel managers",
            "I'll regret reading more but not applying anything"
        ]
    },
    {
        "id": "m4", "phase": "morning", "n": 4,
        "label": "Emotion that may control me today if I don't watch it",
        "type": "select",
        "options": ["Fear", "Laziness", "Excitement", "Ego", "Anxiety", "Loneliness", "Boredom", "Impatience", "Anger", "Lust", "Overconfidence"],
        "hint": "Bad decisions are emotional first, logical later. Predict the hijacker.",
        "examples": [
            "Anxiety — I may keep checking email for replies",
            "Boredom — I may open YouTube during slow stretches",
            "Lust — I may slip during the afternoon break",
            "Ego — I may try to look smart instead of doing simple work"
        ]
    },
    {
        "id": "m5", "phase": "morning", "n": 5,
        "label": "My RULE when that emotion appears",
        "type": "text",
        "hint": "Turn awareness into a pre-committed action. Format: 'If X appears, I will Y.'",
        "examples": [
            "If anxiety appears, I will not check phone for 30 minutes",
            "If boredom appears, I walk 5 min then return to task",
            "If lust appears, I do 20 pushups and leave the room",
            "If overthinking appears, I take the next physical action"
        ]
    },
    # EVENING (5)
    {
        "id": "e1", "phase": "evening", "n": 6,
        "label": "What did I ACTUALLY do today? (no story, just facts)",
        "type": "text",
        "hint": "List actual events. No narrative. No 'I tried to'. Just timestamps and actions.",
        "examples": [
            "Gym 1hr, 1hr work, 2hr scrolling, read 20 pages, avoided second call",
            "Wake 6:30, gym, 9-11 deep work, lunch, 1hr nap, 2 sales calls, dinner, reading"
        ]
    },
    {
        "id": "e2", "phase": "evening", "n": 7,
        "label": "Where did my brain AUTOMATICALLY escape today?",
        "type": "text",
        "hint": "The moment task got hard or unclear, where did you flee to? This is the most important question.",
        "examples": [
            "When task became unclear, I opened YouTube",
            "When I had to call, I started 'researching' instead",
            "When I felt tired, I checked Instagram",
            "When pressure hit, I started thinking about a new business idea"
        ]
    },
    {
        "id": "e3", "phase": "evening", "n": 8,
        "label": "What was I AVOIDING underneath the distraction?",
        "type": "text",
        "hint": "Go one layer deeper than the behavior. The distraction is the symptom — what's the discomfort?",
        "examples": [
            "I was avoiding rejection",
            "I was avoiding not knowing how to price",
            "I was avoiding the feeling of being behind",
            "I was avoiding the discomfort of starting",
            "I was avoiding the fear that I may not be good enough"
        ]
    },
    {
        "id": "e4", "phase": "evening", "n": 9,
        "label": "Did my actions match my claimed priority?",
        "type": "select",
        "options": ["Yes", "Partially", "No"],
        "hint": "Brutal check on self-deception. Compare evening (e1) against morning (m1).",
        "examples": [
            "No. I said money was priority but I read more than I acted",
            "Partially. I worked on skill but avoided outreach",
            "Yes. I completed the task I said mattered"
        ]
    },
    {
        "id": "e5", "phase": "evening", "n": 10,
        "label": "Pattern that repeated today + RULE for tomorrow",
        "type": "text",
        "hint": "Name the loop. Write the rule. Format: 'Pattern: X. Rule: When X happens tomorrow, I will Y.'",
        "examples": [
            "Pattern: I stop after one uncomfortable action. Rule: Tomorrow do 2 uncomfortable actions before any learning",
            "Pattern: I confuse research with progress. Rule: 30min execution before any reading",
            "Pattern: I check phone when uncertain. Rule: Write next action on paper instead"
        ]
    },
]

# ─────────────────────────────────────────────────────────────────
# METRICS & HABITS (output-focused, not aesthetic)
# ─────────────────────────────────────────────────────────────────
METRICS = [
    {"id": "wake", "label": "Wake time", "type": "time"},
    {"id": "sleep", "label": "Sleep time", "type": "time"},
    {"id": "rev_hours", "label": "Revenue Hours (0-8)", "type": "number", "max": 8},
    {"id": "deep_work", "label": "Deep Work hours", "type": "number", "max": 12, "step": 0.5},
    {"id": "shipped", "label": "Shipped something today?", "type": "yesno"},
    {"id": "phone_free", "label": "Phone-free deep work block?", "type": "yesno"},
]

HABITS = [
    {"id": "gym", "name": "Gym", "ico": "💪"},
    {"id": "reading", "name": "Reading <30m", "ico": "📚"},
    {"id": "outreach", "name": "5+ outreach", "ico": "📞"},
    {"id": "bed_1030", "name": "Bed by 10:30", "ico": "🌙"},
    {"id": "no_porn", "name": "No porn/scroll", "ico": "🧠"},
    {"id": "clean_eat", "name": "Clean eating", "ico": "🥗"},
]

# ─────────────────────────────────────────────────────────────────
# Storage helpers
# ─────────────────────────────────────────────────────────────────
def load_entries():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_entries(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────────────────────────
def get_html():
    entries = load_entries()
    return r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Founder's Journal — Self-Awareness</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;1,400&family=JetBrains+Mono:wght@400;600&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0a0b; --panel:#131316; --panel2:#1a1a1f; --border:#27272a;
  --ink:#e7e5e0; --muted:#71717a; --dim:#52525b;
  --gold:#c9a55a; --gold2:#e8d5a0;
  --red:#ef4444; --green:#22c55e; --amber:#f59e0b; --blue:#3b82f6; --violet:#8b5cf6;
  --morning:#f59e0b; --evening:#8b5cf6;
}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--ink);min-height:100vh;-webkit-font-smoothing:antialiased;line-height:1.5}
.wrap{max-width:780px;margin:0 auto;padding:0 20px 140px}
header{padding:48px 0 24px;text-align:center;border-bottom:1px solid var(--border);margin-bottom:24px}
header h1{font-family:'Playfair Display',serif;font-size:38px;font-weight:400;font-style:italic;color:var(--gold2);letter-spacing:-0.5px}
header .sub{font-size:11px;color:var(--muted);letter-spacing:3px;text-transform:uppercase;margin-top:8px}

/* Date nav */
.datenav{display:flex;align-items:center;justify-content:center;gap:18px;margin:20px 0 28px}
.datenav button{background:var(--panel);border:1px solid var(--border);color:var(--ink);width:38px;height:38px;border-radius:50%;cursor:pointer;font-size:16px;transition:all .15s}
.datenav button:hover{background:var(--gold);color:var(--bg);border-color:var(--gold)}
.datelabel{text-align:center;min-width:240px}
.datelabel .d1{font-family:'Playfair Display',serif;font-size:22px;font-style:italic;color:var(--gold2)}
.datelabel .d2{font-size:10px;color:var(--muted);letter-spacing:2px;text-transform:uppercase;margin-top:3px}

/* Tabs */
.tabs{display:flex;gap:6px;margin-bottom:24px;overflow-x:auto;padding-bottom:2px;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tabs button{padding:10px 18px;border-radius:24px;font-size:11px;font-weight:600;letter-spacing:1px;text-transform:uppercase;cursor:pointer;background:transparent;color:var(--muted);border:1px solid var(--border);white-space:nowrap;transition:all .15s;font-family:inherit}
.tabs button.on{background:var(--gold);color:var(--bg);border-color:var(--gold)}
.tabs button:hover:not(.on){border-color:var(--gold);color:var(--gold2)}

.page{display:none;animation:fade .25s ease}
.page.on{display:block}
@keyframes fade{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}

/* Phase header */
.phase{display:flex;align-items:center;gap:12px;margin:28px 0 14px;padding-bottom:10px;border-bottom:1px dashed var(--border)}
.phase .badge{font-size:9px;font-weight:800;letter-spacing:2px;padding:5px 10px;border-radius:4px;text-transform:uppercase}
.phase.morning .badge{background:rgba(245,158,11,.12);color:var(--morning);border:1px solid rgba(245,158,11,.3)}
.phase.evening .badge{background:rgba(139,92,246,.12);color:var(--evening);border:1px solid rgba(139,92,246,.3)}
.phase h2{font-family:'Playfair Display',serif;font-style:italic;font-size:20px;color:var(--ink);font-weight:400}
.phase .desc{font-size:11px;color:var(--muted);margin-left:auto}

/* Question cards */
.q{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:10px;transition:border-color .2s;position:relative}
.q:focus-within{border-color:var(--gold)}
.q .head{display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}
.q .num{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--gold);font-weight:600;background:rgba(201,165,90,.1);padding:3px 8px;border-radius:4px;flex-shrink:0}
.q .label{font-size:14px;font-weight:600;color:var(--ink);flex:1;line-height:1.4}
.q .info{cursor:help;color:var(--dim);font-size:13px;transition:color .2s;position:relative;display:inline-block;width:18px;height:18px;border:1px solid var(--border);border-radius:50%;text-align:center;line-height:16px;font-weight:700;flex-shrink:0}
.q .info:hover{color:var(--gold);border-color:var(--gold)}
.q .hint{font-size:12px;color:var(--muted);margin-bottom:10px;font-style:italic;line-height:1.5}

/* Tooltip */
.tip{display:none;position:absolute;top:100%;right:0;margin-top:8px;background:#0d0d10;border:1px solid var(--gold);border-radius:8px;padding:12px 14px;width:320px;z-index:100;box-shadow:0 10px 40px rgba(0,0,0,.6)}
.info:hover + .tip,.tip:hover{display:block}
.tip .ttitle{font-size:10px;font-weight:700;color:var(--gold);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px}
.tip .ex{font-size:12px;color:var(--ink);margin-bottom:6px;padding-left:10px;border-left:2px solid var(--gold);line-height:1.5}
.tip .ex:last-child{margin-bottom:0}

/* Inputs */
textarea{width:100%;background:transparent;border:none;color:var(--ink);font-family:'Inter',sans-serif;font-size:14px;line-height:1.65;resize:none;outline:none;min-height:50px}
textarea::placeholder{color:var(--dim)}
select,input[type=time],input[type=number]{background:var(--panel2);border:1px solid var(--border);color:var(--ink);padding:9px 12px;border-radius:8px;font-family:inherit;font-size:14px;width:100%;outline:none;transition:border-color .15s}
select:focus,input:focus{border-color:var(--gold)}

.yesno{display:flex;gap:8px}
.yesno button{flex:1;padding:9px;background:transparent;border:1px solid var(--border);border-radius:8px;color:var(--muted);font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;letter-spacing:1px;text-transform:uppercase;transition:all .15s}
.yesno button.yes{background:rgba(34,197,94,.1);border-color:var(--green);color:var(--green)}
.yesno button.no{background:rgba(239,68,68,.1);border-color:var(--red);color:var(--red)}

/* Metrics */
.mgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:14px}
.mrow{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px}
.mrow .ml{font-size:10px;color:var(--muted);letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;font-weight:600}

/* Habits */
.hgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px}
.hb{border-radius:10px;padding:14px 8px;cursor:pointer;text-align:center;border:1.5px solid var(--border);background:var(--panel);transition:all .2s}
.hb .ico{font-size:22px;margin-bottom:4px}
.hb .nm{font-size:10px;font-weight:600;color:var(--muted);letter-spacing:0.5px}
.hb.yes{background:rgba(34,197,94,.08);border-color:rgba(34,197,94,.4)}
.hb.yes .nm{color:var(--green)}
.hb.no{background:rgba(239,68,68,.08);border-color:rgba(239,68,68,.4)}
.hb.no .nm{color:var(--red)}

/* Save indicator */
#save{position:fixed;bottom:24px;right:24px;background:var(--green);color:#000;padding:10px 18px;border-radius:24px;font-size:12px;font-weight:600;opacity:0;pointer-events:none;transition:opacity .3s;z-index:1000}
#save.on{opacity:1}

/* Analytics */
.kpi{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:20px}
.kp{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 10px;text-align:center}
.kp .kl{font-size:9px;color:var(--muted);letter-spacing:1.2px;text-transform:uppercase}
.kp .kv{font-family:'Playfair Display',serif;font-style:italic;font-size:26px;color:var(--gold2);margin-top:4px}
.chartbox{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px;margin-bottom:14px}
.chartbox h3{font-size:11px;color:var(--gold);letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;font-weight:700}
.chartbox canvas{max-height:240px}

/* Patterns view */
.pattern{background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--red);border-radius:8px;padding:14px 16px;margin-bottom:8px}
.pattern .pdate{font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-bottom:4px}
.pattern .ptxt{font-size:13px;color:var(--ink);line-height:1.55}

/* History */
.histday{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin-bottom:8px;cursor:pointer;transition:border-color .15s}
.histday:hover{border-color:var(--gold)}
.histday .hdate{font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--gold)}
.histday .hpri{font-size:13px;color:var(--ink);margin-top:4px}
.histday .hesc{font-size:12px;color:var(--red);margin-top:6px;font-style:italic}
.histday .halign{display:inline-block;font-size:9px;font-weight:700;padding:2px 8px;border-radius:10px;margin-left:8px;letter-spacing:1px}
.halign.yes{background:rgba(34,197,94,.15);color:var(--green)}
.halign.partially{background:rgba(245,158,11,.15);color:var(--amber)}
.halign.no{background:rgba(239,68,68,.15);color:var(--red)}

footer{text-align:center;padding:30px 0;font-size:10px;color:var(--dim);letter-spacing:2px;text-transform:uppercase}

/* Export */
.exrow{display:flex;gap:8px;margin-top:16px;flex-wrap:wrap}
.exrow button{padding:10px 18px;background:var(--panel);border:1px solid var(--border);color:var(--ink);border-radius:8px;font-family:inherit;font-size:11px;font-weight:600;cursor:pointer;letter-spacing:1px;text-transform:uppercase;transition:all .15s}
.exrow button:hover{border-color:var(--gold);color:var(--gold2)}

@media(max-width:600px){
  header h1{font-size:30px}
  .mgrid{grid-template-columns:1fr}
  .kpi{grid-template-columns:repeat(2,1fr)}
  .tip{width:260px;right:-100px}
}
</style></head><body>
<div class="wrap">
  <header>
    <h1>The Founder's Journal</h1>
    <div class="sub">Self-Awareness · Pattern Detection · Output</div>
  </header>

  <div class="datenav">
    <button onclick="navDate(-1)">‹</button>
    <div class="datelabel"><div class="d1" id="dlabel"></div><div class="d2" id="dsub"></div></div>
    <button onclick="navDate(1)">›</button>
  </div>

  <div class="tabs">
    <button data-tab="today" class="on" onclick="show('today')">Today</button>
    <button data-tab="metrics" onclick="show('metrics')">Metrics & Habits</button>
    <button data-tab="patterns" onclick="show('patterns')">Patterns</button>
    <button data-tab="analytics" onclick="show('analytics')">Analytics</button>
    <button data-tab="history" onclick="show('history')">History</button>
  </div>

  <div id="today" class="page on"></div>
  <div id="metrics" class="page"></div>
  <div id="patterns" class="page"></div>
  <div id="analytics" class="page"></div>
  <div id="history" class="page"></div>

  <footer>v2 · Local · Your data never leaves this machine</footer>
</div>
<div id="save">✓ Saved</div>

<script>
const QS = """ + json.dumps(QUESTIONS) + r""";
const METRICS = """ + json.dumps(METRICS) + r""";
const HABITS = """ + json.dumps(HABITS) + r""";
let entries = """ + json.dumps(entries) + r""";
let cur = todayKey();
let saveTimer = null;

function todayKey(){const d=new Date();return d.toISOString().slice(0,10)}
function fmtDate(k){const d=new Date(k+'T12:00:00');return d.toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'})}
function fmtSub(k){const d=new Date(k+'T12:00:00');return d.toLocaleDateString('en-US',{year:'numeric',month:'short',day:'2-digit'}).toUpperCase()}

function navDate(delta){
  const d=new Date(cur+'T12:00:00');d.setDate(d.getDate()+delta);cur=d.toISOString().slice(0,10);render()
}

function show(tab){
  document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.tab===tab));
  document.querySelectorAll('.page').forEach(p=>p.classList.toggle('on',p.id===tab));
  render();
}

function ensure(){
  if(!entries[cur]) entries[cur]={journal:{},habits:{},metrics:{}};
  return entries[cur];
}

function save(){
  clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>{
    fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(entries)})
      .then(()=>{const s=document.getElementById('save');s.classList.add('on');setTimeout(()=>s.classList.remove('on'),1200)});
  },400);
}

function setJ(qid,val){ensure().journal[qid]=val;save()}
function setM(mid,val){ensure().metrics[mid]=val;save();renderMetrics()}
function setH(hid,val){const e=ensure();e.habits[hid]=e.habits[hid]===val?'':val;save();renderMetrics()}

function escapeHtml(s){return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}

function renderToday(){
  const e=ensure();
  const j=e.journal||{};
  const morning=QS.filter(q=>q.phase==='morning');
  const evening=QS.filter(q=>q.phase==='evening');
  let h='';
  h+=`<div class="phase morning"><span class="badge">Morning</span><h2>Direction before the brain escapes</h2><span class="desc">5 questions · 4 min</span></div>`;
  morning.forEach(q=>h+=renderQ(q,j[q.id]||''));
  h+=`<div class="phase evening"><span class="badge">Evening</span><h2>Uncover the subconscious pattern</h2><span class="desc">5 questions · 6 min</span></div>`;
  evening.forEach(q=>h+=renderQ(q,j[q.id]||''));
  document.getElementById('today').innerHTML=h;
}

function renderQ(q,val){
  let input='';
  if(q.type==='select'){
    input=`<select onchange="setJ('${q.id}',this.value)"><option value="">— choose —</option>`+
      q.options.map(o=>`<option ${val===o?'selected':''}>${o}</option>`).join('')+`</select>`;
  } else {
    input=`<textarea placeholder="Your answer in 1-2 sentences..." onblur="setJ('${q.id}',this.value)" oninput="setJ('${q.id}',this.value)">${escapeHtml(val)}</textarea>`;
  }
  const examples=q.examples.map(e=>`<div class="ex">${escapeHtml(e)}</div>`).join('');
  return `<div class="q">
    <div class="head">
      <span class="num">Q${q.n}</span>
      <span class="label">${q.label}</span>
      <span class="info">?</span>
      <div class="tip"><div class="ttitle">Sample answers</div>${examples}</div>
    </div>
    <div class="hint">${q.hint}</div>
    ${input}
  </div>`;
}

function renderMetrics(){
  const e=ensure();
  const m=e.metrics||{};
  const ha=e.habits||{};
  let h='<div class="phase morning"><span class="badge">Habits</span><h2>The 6 that predict output</h2></div>';
  h+='<div class="hgrid">';
  HABITS.forEach(hab=>{
    const v=ha[hab.id]||'';
    h+=`<div class="hb ${v}" onclick="cycleHabit('${hab.id}')">
      <div class="ico">${hab.ico}</div>
      <div class="nm">${hab.name}</div>
    </div>`;
  });
  h+='</div>';
  h+='<div class="phase evening"><span class="badge">Metrics</span><h2>What actually moved</h2></div>';
  h+='<div class="mgrid">';
  METRICS.forEach(mt=>{
    const v=m[mt.id]||'';
    h+=`<div class="mrow"><div class="ml">${mt.label}</div>`;
    if(mt.type==='time') h+=`<input type="time" value="${v}" onchange="setM('${mt.id}',this.value)">`;
    else if(mt.type==='number') h+=`<input type="number" min="0" max="${mt.max||10}" step="${mt.step||1}" value="${v}" onchange="setM('${mt.id}',this.value)">`;
    else if(mt.type==='yesno') h+=`<div class="yesno">
      <button class="${v==='yes'?'yes':''}" onclick="setM('${mt.id}','${v==='yes'?'':'yes'}')">Yes</button>
      <button class="${v==='no'?'no':''}" onclick="setM('${mt.id}','${v==='no'?'':'no'}')">No</button>
    </div>`;
    h+='</div>';
  });
  h+='</div>';
  document.getElementById('metrics').innerHTML=h;
}

function cycleHabit(id){
  const e=ensure();
  const cur=e.habits[id]||'';
  const next=cur===''?'yes':cur==='yes'?'no':'';
  e.habits[id]=next;save();renderMetrics();
}

function filledDays(){return Object.keys(entries).filter(k=>{const e=entries[k];return e.journal&&Object.values(e.journal).some(v=>v&&v.trim&&v.trim().length>3)}).sort()}

function renderPatterns(){
  const days=filledDays().slice(-30);
  let h='<div class="phase evening"><span class="badge">Patterns</span><h2>Where your brain escapes — last 30 days</h2></div>';
  // Escape patterns (e2)
  const escapes=days.map(k=>({k,v:entries[k].journal.e2||''})).filter(x=>x.v.trim().length>3);
  const avoids=days.map(k=>({k,v:entries[k].journal.e3||''})).filter(x=>x.v.trim().length>3);
  const rules=days.map(k=>({k,v:entries[k].journal.e5||''})).filter(x=>x.v.trim().length>3);
  if(!escapes.length){h+='<div class="q"><div class="hint">No pattern data yet. Fill the evening questions for a few days.</div></div>';document.getElementById('patterns').innerHTML=h;return}
  h+='<h3 style="font-size:11px;color:var(--red);letter-spacing:2px;text-transform:uppercase;margin:20px 0 10px;font-weight:700">Escapes</h3>';
  escapes.slice(-10).reverse().forEach(x=>{
    h+=`<div class="pattern"><div class="pdate">${x.k}</div><div class="ptxt">${escapeHtml(x.v)}</div></div>`;
  });
  h+='<h3 style="font-size:11px;color:var(--amber);letter-spacing:2px;text-transform:uppercase;margin:24px 0 10px;font-weight:700">What you were avoiding</h3>';
  avoids.slice(-10).reverse().forEach(x=>{
    h+=`<div class="pattern" style="border-left-color:var(--amber)"><div class="pdate">${x.k}</div><div class="ptxt">${escapeHtml(x.v)}</div></div>`;
  });
  h+='<h3 style="font-size:11px;color:var(--green);letter-spacing:2px;text-transform:uppercase;margin:24px 0 10px;font-weight:700">Rules you committed to</h3>';
  rules.slice(-10).reverse().forEach(x=>{
    h+=`<div class="pattern" style="border-left-color:var(--green)"><div class="pdate">${x.k}</div><div class="ptxt">${escapeHtml(x.v)}</div></div>`;
  });
  document.getElementById('patterns').innerHTML=h;
}

function renderAnalytics(){
  const days=filledDays();
  const total=days.length;
  if(!total){document.getElementById('analytics').innerHTML='<div class="q"><div class="hint">No data yet.</div></div>';return}
  // KPIs
  const revH=days.map(k=>parseFloat(entries[k].metrics?.rev_hours||0)).filter(v=>v>0);
  const dwH=days.map(k=>parseFloat(entries[k].metrics?.deep_work||0)).filter(v=>v>0);
  const aligned=days.filter(k=>entries[k].journal?.e4==='Yes').length;
  const shipped=days.filter(k=>entries[k].metrics?.shipped==='yes').length;
  const avgRev=revH.length?(revH.reduce((a,b)=>a+b,0)/revH.length).toFixed(1):'—';
  const avgDw=dwH.length?(dwH.reduce((a,b)=>a+b,0)/dwH.length).toFixed(1):'—';
  let h=`<div class="kpi">
    <div class="kp"><div class="kl">Days logged</div><div class="kv">${total}</div></div>
    <div class="kp"><div class="kl">Avg Rev Hrs</div><div class="kv">${avgRev}</div></div>
    <div class="kp"><div class="kl">Avg Deep Wk</div><div class="kv">${avgDw}</div></div>
    <div class="kp"><div class="kl">Alignment %</div><div class="kv">${Math.round(aligned/total*100)}</div></div>
  </div>`;
  h+='<div class="chartbox"><h3>Revenue Hours · last 21 days</h3><canvas id="revChart"></canvas></div>';
  h+='<div class="chartbox"><h3>Habit Consistency</h3><canvas id="habChart"></canvas></div>';
  h+='<div class="chartbox"><h3>Priority Areas — what you said mattered</h3><canvas id="priChart"></canvas></div>';
  h+='<div class="chartbox"><h3>Emotion that controlled you</h3><canvas id="emoChart"></canvas></div>';
  h+='<div class="chartbox"><h3>Alignment over time (priority vs action)</h3><canvas id="alignChart"></canvas></div>';
  h+=`<div class="exrow">
    <button onclick="exportJSON()">⬇ Export JSON</button>
    <button onclick="exportCSV()">⬇ Export CSV</button>
  </div>`;
  document.getElementById('analytics').innerHTML=h;
  drawCharts(days);
}

function drawCharts(days){
  const recent=days.slice(-21);
  const labels=recent.map(k=>k.slice(5));
  // Revenue Hours
  const revData=recent.map(k=>parseFloat(entries[k].metrics?.rev_hours||0));
  const ctx1=document.getElementById('revChart');
  if(ctx1) new Chart(ctx1,{type:'bar',data:{labels,datasets:[{label:'Rev Hrs',data:revData,
    backgroundColor:revData.map(v=>v>=4?'rgba(34,197,94,.7)':v>=2?'rgba(245,158,11,.7)':'rgba(239,68,68,.7)'),
    borderRadius:4}]},
    options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#71717a',font:{size:9}},grid:{display:false}},y:{beginAtZero:true,max:8,ticks:{color:'#71717a'},grid:{color:'rgba(255,255,255,.04)'}}},maintainAspectRatio:false}});
  // Habits
  const habCounts=HABITS.map(h=>days.filter(k=>entries[k].habits?.[h.id]==='yes').length);
  const habPct=habCounts.map(c=>Math.round(c/Math.max(days.length,1)*100));
  const ctx2=document.getElementById('habChart');
  if(ctx2) new Chart(ctx2,{type:'bar',data:{labels:HABITS.map(h=>h.name),datasets:[{label:'% days',data:habPct,
    backgroundColor:habPct.map(v=>v>=70?'rgba(34,197,94,.7)':v>=40?'rgba(245,158,11,.7)':'rgba(239,68,68,.7)'),
    borderRadius:4}]},
    options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{beginAtZero:true,max:100,ticks:{color:'#71717a',callback:v=>v+'%'},grid:{color:'rgba(255,255,255,.04)'}},y:{ticks:{color:'#a1a1aa',font:{size:11}},grid:{display:false}}},maintainAspectRatio:false}});
  // Priority pie
  const priCounts={};days.forEach(k=>{const p=entries[k].journal?.m1;if(p)priCounts[p]=(priCounts[p]||0)+1});
  const ctx3=document.getElementById('priChart');
  if(ctx3) new Chart(ctx3,{type:'doughnut',data:{labels:Object.keys(priCounts),datasets:[{data:Object.values(priCounts),
    backgroundColor:['#c9a55a','#8b5cf6','#22c55e','#f59e0b','#3b82f6','#ef4444','#06b6d4','#ec4899','#a855f7'],borderWidth:0}]},
    options:{plugins:{legend:{position:'bottom',labels:{color:'#a1a1aa',font:{size:11},padding:12,usePointStyle:true}}},cutout:'55%',maintainAspectRatio:false}});
  // Emotion bar
  const emoCounts={};days.forEach(k=>{const e=entries[k].journal?.m4;if(e)emoCounts[e]=(emoCounts[e]||0)+1});
  const ctx4=document.getElementById('emoChart');
  if(ctx4) new Chart(ctx4,{type:'bar',data:{labels:Object.keys(emoCounts),datasets:[{label:'Times',data:Object.values(emoCounts),
    backgroundColor:'rgba(139,92,246,.6)',borderRadius:4}]},
    options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#71717a',font:{size:10}},grid:{display:false}},y:{beginAtZero:true,ticks:{color:'#71717a',stepSize:1},grid:{color:'rgba(255,255,255,.04)'}}},maintainAspectRatio:false}});
  // Alignment
  const alignData=recent.map(k=>{const a=entries[k].journal?.e4;return a==='Yes'?2:a==='Partially'?1:a==='No'?0:null});
  const ctx5=document.getElementById('alignChart');
  if(ctx5) new Chart(ctx5,{type:'line',data:{labels,datasets:[{label:'Alignment',data:alignData,
    borderColor:'#c9a55a',backgroundColor:'rgba(201,165,90,.1)',tension:.3,fill:true,pointRadius:4,
    pointBackgroundColor:alignData.map(v=>v===2?'#22c55e':v===1?'#f59e0b':v===0?'#ef4444':'#52525b')}]},
    options:{plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#71717a',font:{size:9}},grid:{display:false}},y:{min:-.2,max:2.2,ticks:{color:'#71717a',stepSize:1,callback:v=>v===2?'Yes':v===1?'Part':v===0?'No':''},grid:{color:'rgba(255,255,255,.04)'}}},maintainAspectRatio:false}});
}

function renderHistory(){
  const days=filledDays().reverse();
  let h='<div class="phase morning"><span class="badge">History</span><h2>All entries</h2></div>';
  if(!days.length){h+='<div class="q"><div class="hint">No entries yet.</div></div>';document.getElementById('history').innerHTML=h;return}
  days.forEach(k=>{
    const e=entries[k];
    const pri=e.journal?.m1||'';
    const why=e.journal?.m2||'';
    const esc=e.journal?.e2||'';
    const al=e.journal?.e4||'';
    h+=`<div class="histday" onclick="cur='${k}';show('today')">
      <div class="hdate">${k} ${al?`<span class="halign ${al.toLowerCase()}">${al}</span>`:''}</div>
      <div class="hpri"><b>${pri||'No priority set'}</b>${why?' — '+escapeHtml(why.slice(0,80)):''}</div>
      ${esc?`<div class="hesc">Escape: ${escapeHtml(esc.slice(0,100))}</div>`:''}
    </div>`;
  });
  document.getElementById('history').innerHTML=h;
}

function exportJSON(){
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([JSON.stringify(entries,null,2)],{type:'application/json'}));
  a.download='founder_journal_v2_backup.json';a.click();
}
function exportCSV(){
  const days=filledDays();if(!days.length)return;
  const headers=['Date',...QS.map(q=>'Q'+q.n+': '+q.label),...METRICS.map(m=>m.label),...HABITS.map(h=>h.name)];
  let csv=headers.map(h=>'"'+h.replace(/"/g,'""')+'"').join(',')+'\n';
  days.forEach(k=>{
    const e=entries[k];
    const row=[k,...QS.map(q=>e.journal?.[q.id]||''),...METRICS.map(m=>e.metrics?.[m.id]||''),...HABITS.map(h=>e.habits?.[h.id]||'')];
    csv+=row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')+'\n';
  });
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'}));
  a.download='founder_journal_v2.csv';a.click();
}

function render(){
  document.getElementById('dlabel').textContent=fmtDate(cur);
  document.getElementById('dsub').textContent=fmtSub(cur);
  const activeTab=document.querySelector('.tabs button.on')?.dataset.tab||'today';
  if(activeTab==='today')renderToday();
  if(activeTab==='metrics')renderMetrics();
  if(activeTab==='patterns')renderPatterns();
  if(activeTab==='analytics')renderAnalytics();
  if(activeTab==='history')renderHistory();
}

render();
</script>
</body></html>"""

# ─────────────────────────────────────────────────────────────────
# HTTP Server
# ─────────────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a, **k): pass

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            html = get_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        if self.path == "/save":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                save_entries(data)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok":true}')
            except Exception as e:
                self.send_response(500); self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404); self.end_headers()

def open_browser():
    import time; time.sleep(0.6)
    webbrowser.open(f"http://localhost:{PORT}")

if __name__ == "__main__":
    print(f"\n  🟡  Founder's Journal v2")
    print(f"  📂  Data: {DATA_FILE}")
    print(f"  🌐  http://localhost:{PORT}")
    print(f"  ⏹   Ctrl+C to stop\n")
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        http.server.HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\n  ✓ Stopped. Data saved.\n")
