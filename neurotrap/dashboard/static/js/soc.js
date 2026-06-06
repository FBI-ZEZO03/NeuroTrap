'use strict';
/* ════════════════════════════════════════════════════════════
   NeuroTrap CADN — Innovation 06 · AI SOC Analyst
   Loaded after app.js; uses the shared `state`, setText, timeSince.
════════════════════════════════════════════════════════════ */

state.socQueue = [];
state.socSelected = null;

const SOC_RISK = {
  critical: {c:'#f43f5e', label:'CRITICAL'},
  high:     {c:'#fb7185', label:'HIGH'},
  elevated: {c:'#f59e0b', label:'ELEVATED'},
  low:      {c:'#10b981', label:'LOW'},
};
const SOC_ACTION = {
  block:   {c:'#f43f5e', icon:'fa-ban',          label:'Block'},
  isolate: {c:'#fb7185', icon:'fa-lock',         label:'Isolate'},
  slow:    {c:'#f59e0b', icon:'fa-hourglass-half',label:'Slow'},
  monitor: {c:'#10b981', icon:'fa-eye',          label:'Monitor'},
};

async function loadSOC(){
  await Promise.all([socLoadSummary(), socLoadQueue()]);
  if (state.socQueue.length && !state.socSelected) socSelect(state.socQueue[0].src_ip);
  if (!document.getElementById('soc-chat-log').childElementCount){
    socPush('analyst', 'Hi — I\'m your AI SOC analyst. Ask about the top threats, a specific IP, or what to block.');
  }
}

async function socRefresh(){
  const btn = document.getElementById('soc-refresh-btn');
  if (btn){ btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Refreshing…'; }
  state.socSelected = null;
  await loadSOC();
  if (btn){ btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Refresh'; }
}

async function socLoadSummary(){
  let s = {};
  try { s = await (await fetch('/api/soc/summary')).json(); } catch {}
  setText('soc-kpi-actors', s.actors_tracked ?? '—');
  setText('soc-kpi-action', s.needs_action ?? '—');
  setText('soc-kpi-events', s.events_in_window ?? '—');
  let reps = 0;
  try { reps = (await (await fetch('/api/soc/reports')).json()).reports.length; } catch {}
  setText('soc-kpi-reports', reps);
  const badge = document.getElementById('soc-llm-badge');
  if (badge){
    if (s.llm_enabled){ badge.style.color = '#10b981'; badge.innerHTML = '<i class="fa-solid fa-circle" style="font-size:7px"></i> Anthropic LLM active'; }
    else { badge.style.color = '#f59e0b'; badge.innerHTML = '<i class="fa-solid fa-circle" style="font-size:7px"></i> Heuristic mode (set ANTHROPIC_API_KEY)'; }
  }
}

async function socLoadQueue(){
  try { state.socQueue = (await (await fetch('/api/soc/triage')).json()).queue || []; }
  catch { state.socQueue = []; }
  socRenderQueue();
}

function socRenderQueue(){
  const el = document.getElementById('soc-queue'); if(!el) return;
  if(!state.socQueue.length){ el.innerHTML = '<div style="color:var(--t4);text-align:center;padding:32px;font-size:12px">Queue empty — attack a honeypot, then Refresh.</div>'; return; }
  el.innerHTML = state.socQueue.map(t=>{
    const r = SOC_RISK[t.risk] || SOC_RISK.low;
    const a = SOC_ACTION[t.recommended_action] || SOC_ACTION.monitor;
    const sel = state.socSelected===t.src_ip ? 'border-color:#a855f7;background:rgba(168,85,247,0.08)' : '';
    return '<div onclick="socSelect(\'' + t.src_ip + '\')" style="cursor:pointer;border:1px solid var(--bd);border-radius:10px;padding:10px 12px;margin-bottom:8px;transition:.15s;' + sel + '">'
      + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
      + '<span style="font-family:var(--mono);font-size:12px;font-weight:600;color:var(--t1)">' + t.src_ip + '</span>'
      + '<span style="margin-left:auto;font-size:9px;font-weight:700;letter-spacing:.5px;color:' + r.c + ';background:' + r.c + '1a;border:1px solid ' + r.c + '33;padding:2px 6px;border-radius:5px">' + r.label + '</span>'
      + '</div>'
      + '<div style="display:flex;align-items:center;gap:6px;font-size:10px;color:var(--t3);margin-bottom:6px">'
      + '<span>' + (t.intent||'unknown').replace(/_/g,' ') + '</span><span>·</span><span>score ' + t.threat_score + '</span></div>'
      + '<div style="display:flex;align-items:center;gap:6px">'
      + '<span style="font-size:10px;font-weight:700;color:' + a.c + '"><i class="fa-solid ' + a.icon + '"></i> ' + a.label + '</span>'
      + '<span style="margin-left:auto;font-size:9px;color:var(--t4)">' + timeSince(t.last_seen) + '</span></div></div>';
  }).join('');
}

async function socSelect(ip){
  state.socSelected = ip;
  socRenderQueue();
  setText('soc-report-ip', ip);
  const box = document.getElementById('soc-report');
  box.innerHTML = '<div style="color:var(--t4);text-align:center;padding:48px;font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Generating incident report for ' + ip + '…</div>';
  setText('soc-report-src', '');
  let r;
  try { r = await (await fetch('/api/soc/report', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({src_ip:ip})})).json(); }
  catch { box.innerHTML = '<div style="color:var(--t4);text-align:center;padding:40px">Report failed.</div>'; return; }
  socRenderReport(r);
  socLoadSummary();  // refresh "reports filed" count
}

function socRenderReport(r){
  const box = document.getElementById('soc-report'); if(!box) return;
  const a = SOC_ACTION[r.recommended_action] || SOC_ACTION.monitor;
  const rk = SOC_RISK[r.risk] || SOC_RISK.low;
  const srcBadge = r.source==='anthropic'
    ? '<span style="color:#10b981"><i class="fa-solid fa-robot"></i> Anthropic</span>'
    : '<span style="color:#f59e0b"><i class="fa-solid fa-gears"></i> Heuristic</span>';
  setText('soc-report-src', '');
  document.getElementById('soc-report-src').innerHTML = srcBadge;
  const banner = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px">'
    + '<span style="font-size:11px;font-weight:700;color:' + rk.c + ';background:' + rk.c + '1a;border:1px solid ' + rk.c + '33;padding:4px 10px;border-radius:6px">' + rk.label + ' · ' + r.threat_score + '/100</span>'
    + '<span style="font-size:11px;font-weight:700;color:' + a.c + ';background:' + a.c + '1a;border:1px solid ' + a.c + '33;padding:4px 10px;border-radius:6px"><i class="fa-solid ' + a.icon + '"></i> ' + a.label + '</span>'
    + '<button class="btn btn-sm btn-danger" style="margin-left:auto" onclick="socBlock(\'' + r.src_ip + '\')"><i class="fa-solid fa-ban"></i> Block ' + r.src_ip + '</button></div>';
  box.innerHTML = banner + '<div class="soc-md" style="font-size:12.5px;line-height:1.6;color:var(--t2)">' + socMarkdown(r.report_md) + '</div>';
}

// Minimal Markdown → HTML for the report body (headings, bold, code, lists).
function socMarkdown(md){
  if(!md) return '';
  const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const lines = md.split('\n'); let html=''; let inList=false;
  for(let raw of lines){
    let line = raw.trimEnd();
    if(/^#{1,6}\s/.test(line)){
      if(inList){html+='</ul>';inList=false;}
      const txt = line.replace(/^#{1,6}\s/,'');
      html += '<div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#d8b4fe;margin:14px 0 6px">' + inline(esc(txt)) + '</div>';
    } else if(/^[-*]\s/.test(line)){
      if(!inList){html+='<ul style="margin:4px 0 4px 18px;padding:0">';inList=true;}
      html += '<li style="margin:2px 0">' + inline(esc(line.replace(/^[-*]\s/,''))) + '</li>';
    } else if(line===''){
      if(inList){html+='</ul>';inList=false;}
    } else {
      if(inList){html+='</ul>';inList=false;}
      html += '<p style="margin:4px 0">' + inline(esc(line)) + '</p>';
    }
  }
  if(inList) html+='</ul>';
  function inline(s){
    return s.replace(/`([^`]+)`/g,'<code style="font-family:var(--mono);background:rgba(255,255,255,0.06);padding:1px 5px;border-radius:4px;font-size:11px">$1</code>')
            .replace(/\*\*([^*]+)\*\*/g,'<strong style="color:var(--t1)">$1</strong>');
  }
  return html;
}

async function socBlock(ip){
  try { await fetch('/api/response/block', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({src_ip:ip})}); } catch {}
  socPush('analyst', 'Block action submitted for ' + ip + ' (logged to response engine).');
}

// ── Analyst chat ─────────────────────────────────────────────────────────────
function socPush(who, text){
  const log = document.getElementById('soc-chat-log'); if(!log) return;
  const mine = who==='you';
  const bubble = document.createElement('div');
  bubble.style.cssText = 'max-width:85%;padding:8px 12px;border-radius:10px;font-size:12px;line-height:1.5;'
    + (mine ? 'align-self:flex-end;background:rgba(168,85,247,0.15);border:1px solid rgba(168,85,247,0.3);color:var(--t1)'
            : 'align-self:flex-start;background:var(--bg3,rgba(255,255,255,0.04));border:1px solid var(--bd);color:var(--t2)');
  bubble.innerHTML = (mine?'':'<i class="fa-solid fa-user-shield" style="color:#a855f7;margin-right:6px"></i>') + text;
  log.appendChild(bubble);
  log.scrollTop = log.scrollHeight;
}

async function socAsk(){
  const input = document.getElementById('soc-chat-input');
  const q = (input.value||'').trim(); if(!q) return;
  input.value = '';
  socPush('you', q.replace(/</g,'&lt;'));
  const thinking = document.createElement('div');
  thinking.id='soc-thinking';
  thinking.style.cssText='align-self:flex-start;color:var(--t4);font-size:11px;padding:4px 8px';
  thinking.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> analyzing…';
  document.getElementById('soc-chat-log').appendChild(thinking);
  let res;
  try { res = await (await fetch('/api/soc/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question:q})})).json(); }
  catch { res = {answer:'Sorry — the analyst is unreachable.'}; }
  thinking.remove();
  socPush('analyst', (res.answer||'No answer.').replace(/</g,'&lt;'));
}
