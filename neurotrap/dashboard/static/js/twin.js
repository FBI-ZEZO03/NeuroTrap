'use strict';
/* ════════════════════════════════════════════════════════════
   NeuroTrap CADN — Innovation 05 · Attacker Digital Twin (ADT)
   Loaded after app.js; uses the shared `state`, setText, timeSince.
════════════════════════════════════════════════════════════ */

const TWIN_TIER_META = {
  beginner:       {label:'Beginner',      color:'#10b981', icon:'fa-seedling'},
  automated_bot:  {label:'Automated Bot',  color:'#f59e0b', icon:'fa-robot'},
  advanced_human: {label:'Advanced Human', color:'#f43f5e', icon:'fa-user-secret'},
};
const KC_STAGES = ['Reconnaissance','Weaponization','Delivery','Exploitation','Installation','Command & Control','Actions on Objectives'];

async function loadTwin(){
  try {
    const d = await (await fetch('/api/twin/list')).json();
    state.twins = d.twins || [];
  } catch { state.twins = []; }
  renderTwinKPIs();
  renderTwinList();
  if (state.twins.length) selectTwin(state.twins[0].src_ip);
}

async function twinRefresh(){
  const btn = document.getElementById('twin-refresh-btn');
  if (btn){ btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Building…'; }
  try { await fetch('/api/twin/build', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'}); } catch {}
  await loadTwin();
  if (btn){ btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Refresh Twins'; }
}

function renderTwinKPIs(){
  const t = state.twins;
  setText('twin-kpi-count', t.length || '—');
  setText('twin-kpi-threat', t.length ? Math.round(Math.max.apply(null, t.map(x=>x.threat_score||0))) : '—');
  setText('twin-kpi-conf', t.length ? Math.round(t.reduce((a,x)=>a+(x.confidence||0),0)/t.length*100)+'%' : '—');
  setText('twin-kpi-impact', t.filter(x=>(x.kill_chain||{}).current_stage==='Actions on Objectives').length || '0');
}

function renderTwinList(){
  const el = document.getElementById('twin-list'); if(!el) return;
  if(!state.twins.length){ el.innerHTML = '<div style="color:var(--t4);text-align:center;padding:32px;font-size:12px">No twins yet — attack a honeypot, then Refresh.</div>'; return; }
  el.innerHTML = state.twins.map(t=>{
    const tm = TWIN_TIER_META[t.attacker_tier] || TWIN_TIER_META.beginner;
    const sel = state.selectedTwin===t.src_ip ? 'border-color:#38bdf8;background:rgba(56,189,248,0.08)' : '';
    const sev = t.threat_score>=70?'#f43f5e':t.threat_score>=40?'#f59e0b':'#10b981';
    return '<div onclick="selectTwin(\'' + t.src_ip + '\')" style="cursor:pointer;border:1px solid var(--bd);border-radius:10px;padding:10px 12px;margin-bottom:8px;transition:.15s;' + sel + '">'
      + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">'
      + '<i class="fa-solid ' + tm.icon + '" style="color:' + tm.color + '"></i>'
      + '<span style="font-family:var(--mono);font-size:12px;font-weight:600;color:var(--t1)">' + t.src_ip + '</span>'
      + '<span style="margin-left:auto;font-size:10px;font-weight:700;color:' + sev + '">' + Math.round(t.threat_score||0) + '</span>'
      + '</div>'
      + '<div style="display:flex;align-items:center;gap:6px;font-size:10px;color:var(--t3)">'
      + '<span style="color:' + tm.color + '">' + tm.label + '</span><span>·</span>'
      + '<span>' + ((t.kill_chain||{}).current_stage||'—') + '</span></div>'
      + '<div style="margin-top:6px;height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">'
      + '<div style="height:100%;width:' + Math.round(((t.kill_chain||{}).progress||0)*100) + '%;background:linear-gradient(90deg,#38bdf8,#f43f5e)"></div></div></div>';
  }).join('');
}

function selectTwin(ip){
  state.selectedTwin = ip;
  const t = state.twins.find(x=>x.src_ip===ip);
  renderTwinList();
  if(!t) return;
  setText('twin-sel-ip', t.src_ip);
  setText('twin-sel-conf', 'model confidence ' + Math.round((t.confidence||0)*100) + '% · fidelity ' + Math.round((t.fidelity||0)*100) + '%');
  renderTwinDetail(t); renderKillChain(t); renderPredictions(t); renderReco(t);
  document.getElementById('twin-sim-out').innerHTML = '<div style="color:var(--t4);text-align:center;padding:24px;font-size:12px">Run a simulation to forecast this attacker\'s likely path.</div>';
}

function chip(txt, color){
  return '<span style="display:inline-block;font-size:10px;font-family:var(--mono);padding:3px 8px;border-radius:6px;margin:2px;background:' + color + '1a;color:' + color + ';border:1px solid ' + color + '33">' + txt + '</span>';
}

function renderTwinDetail(t){
  const el = document.getElementById('twin-detail'); if(!el) return;
  const tm = TWIN_TIER_META[t.attacker_tier] || TWIN_TIER_META.beginner;
  const psych = t.psychology || {};
  const stat = (label,val,color)=>'<div><div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--t4);margin-bottom:3px">' + label + '</div><div style="font-size:16px;font-weight:700;color:' + (color||'var(--t1)') + '">' + val + '</div></div>';
  let html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:14px">'
    + stat('Tier', '<span style="color:' + tm.color + '">' + tm.label + '</span>')
    + stat('Intent', (t.classified_intent||'unknown').replace(/_/g,' '))
    + stat('Threat', Math.round(t.threat_score||0), t.threat_score>=70?'#f43f5e':'#f59e0b')
    + stat('Observations', t.observation_count||0)
    + '</div>'
    + '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:14px">'
    + stat('Automation', Math.round(t.automation_score||0)+'%', tm.color)
    + stat('Sophistication', Math.round(t.sophistication||0)+'%', '#a855f7')
    + stat('Last Seen', timeSince(t.last_seen))
    + '</div>'
    + '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--t4);margin:8px 0 4px">Tooling Fingerprint</div>'
    + '<div>' + ((t.tools||[]).length ? t.tools.map(x=>chip(x,'#f43f5e')).join('') : '<span style="color:var(--t4);font-size:11px">none detected</span>') + '</div>'
    + '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--t4);margin:10px 0 4px">Honeypots Touched</div>'
    + '<div>' + ((t.honeypots_touched||[]).map(x=>chip(x.toUpperCase(),'#38bdf8')).join('') || '<span style="color:var(--t4);font-size:11px">—</span>') + '</div>'
    + '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--t4);margin:10px 0 4px">Tactics Observed</div>'
    + '<div>' + ((t.tactics_observed||[]).map(x=>chip(x,'#10b981')).join('') || '<span style="color:var(--t4);font-size:11px">—</span>') + '</div>';
  if(psych.dominant){
    html += '<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--t4);margin:10px 0 4px">Psychological Lever (CBEE)</div>'
      + '<div>' + chip((psych.dominant||'').replace(/_/g,' '), '#a855f7') + (psych.overall?chip('bias '+Math.round(psych.overall),'#a855f7'):'') + '</div>';
  }
  el.innerHTML = html;
}

function renderKillChain(t){
  const el = document.getElementById('twin-killchain'); if(!el) return;
  const kc = t.kill_chain || {}; const cur = kc.current_index||0;
  const reached = new Set((kc.stages||[]).filter(s=>s.reached).map(s=>s.index));
  let cells = '';
  KC_STAGES.forEach((s,i)=>{
    const done = reached.has(i), isCur = i===cur;
    const bg = done ? (isCur?'#f43f5e':'#38bdf8') : 'rgba(255,255,255,0.05)';
    const col = done ? '#fff' : 'var(--t4)';
    cells += '<div style="flex:1;text-align:center">'
      + '<div style="height:34px;border-radius:6px;background:' + bg + ';display:flex;align-items:center;justify-content:center;' + (isCur?'box-shadow:0 0 0 2px rgba(244,63,94,.4)':'') + '">'
      + '<span style="font-size:11px;font-weight:700;color:' + col + '">' + (done?'<i class="fa-solid fa-check"></i>':(i+1)) + '</span></div>'
      + '<div style="font-size:8.5px;color:' + (isCur?'#fda4af':col) + ';margin-top:4px;line-height:1.2">' + s + '</div></div>';
    if(i<KC_STAGES.length-1) cells += '<div style="display:flex;align-items:center;color:var(--t4);font-size:10px">›</div>';
  });
  el.innerHTML = '<div style="display:flex;align-items:stretch;gap:4px;margin-bottom:10px">' + cells + '</div>'
    + '<div style="display:flex;justify-content:space-between;font-size:11px;color:var(--t3)">'
    + '<span>Current: <b style="color:#fda4af">' + (kc.current_stage||'—') + '</b></span>'
    + '<span>Depth ' + (kc.depth||0) + '/7 · <b style="color:#38bdf8">' + Math.round((kc.progress||0)*100) + '%</b> through chain</span></div>';
}

function renderPredictions(t){
  const el = document.getElementById('twin-predictions'); if(!el) return;
  const preds = t.predicted_next || [];
  if(!preds.length){ el.innerHTML = '<div style="color:var(--t4);text-align:center;padding:24px;font-size:12px">—</div>'; return; }
  el.innerHTML = preds.map((p,i)=>{
    const pct = Math.round((p.probability||0)*100);
    return '<div style="margin-bottom:' + (i<preds.length-1?'12':'0') + 'px">'
      + '<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">'
      + (i===0?'<i class="fa-solid fa-crosshairs" style="color:#f59e0b"></i>':'<span style="width:14px;display:inline-block"></span>')
      + '<span style="font-size:12px;font-weight:600;color:var(--t1)">' + p.tactic + '</span>'
      + '<span style="margin-left:auto;font-size:12px;font-weight:700;color:#f59e0b">' + pct + '%</span></div>'
      + '<div style="height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden;margin-bottom:3px">'
      + '<div style="height:100%;width:' + pct + '%;background:#f59e0b"></div></div>'
      + '<div style="font-size:10px;color:var(--t3);font-family:var(--mono)">' + p.technique_id + ' · ' + p.technique_name + '</div></div>';
  }).join('');
}

function renderReco(t){
  const el = document.getElementById('twin-reco'); if(!el) return;
  const r = t.recommendation || {};
  const uc = {high:'#f43f5e',medium:'#f59e0b',low:'#10b981'}[r.urgency] || '#10b981';
  el.innerHTML = '<div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">'
    + '<span style="font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:' + uc + ';border:1px solid ' + uc + '55;border-radius:5px;padding:2px 8px">' + (r.urgency||'low') + ' urgency</span>'
    + '<span style="font-size:11px;color:var(--t3)">anticipates <b style="color:#fda4af">' + (r.anticipated_tactic||'—') + '</b></span></div>'
    + '<div style="font-size:12px;color:var(--t1);line-height:1.5;margin-bottom:10px">' + (r.action||'—') + '</div>'
    + '<div style="display:flex;gap:8px;flex-wrap:wrap">'
    + (r.suggested_env_tier?chip('env: '+r.suggested_env_tier,'#38bdf8'):'')
    + (r.bias_lever?chip('lever: '+String(r.bias_lever).replace(/_/g,' '),'#a855f7'):'') + '</div>';
}

async function twinSimulate(){
  if(!state.selectedTwin) return;
  const out = document.getElementById('twin-sim-out');
  const steps = parseInt(document.getElementById('twin-sim-steps').value) || 6;
  out.innerHTML = '<div style="color:var(--t4);text-align:center;padding:20px;font-size:12px"><i class="fa-solid fa-spinner fa-spin"></i> Running attacker forward…</div>';
  let d;
  try { d = await (await fetch('/api/twin/simulate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({src_ip:state.selectedTwin,steps:steps})})).json(); }
  catch { out.innerHTML = '<div style="color:#f43f5e;text-align:center;padding:20px;font-size:12px">Simulation failed</div>'; return; }
  const fc = d.forecast || [];
  let chain = '';
  fc.forEach((s,i)=>{
    chain += '<div style="border:1px solid var(--bd);border-radius:8px;padding:8px 10px;background:rgba(56,189,248,0.04);min-width:130px">'
      + '<div style="font-size:9px;color:var(--t4);margin-bottom:2px">STEP ' + s.step + ' · ' + Math.round((s.probability||0)*100) + '%</div>'
      + '<div style="font-size:12px;font-weight:600;color:var(--t1)">' + s.tactic + '</div>'
      + '<div style="font-size:9.5px;color:var(--t3);font-family:var(--mono)">' + s.technique_id + '</div></div>';
    if(i<fc.length-1) chain += '<i class="fa-solid fa-arrow-right" style="color:#38bdf8;font-size:11px"></i>';
  });
  out.innerHTML = '<div style="font-size:11px;color:var(--t3);margin-bottom:12px">Starting from <b style="color:#38bdf8">' + (d.current||'unknown') + '</b>, the twin\'s most likely path over the next ' + fc.length + ' moves:</div>'
    + '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px">' + chain + '</div>'
    + '<div style="font-size:10px;color:var(--t4);margin-top:12px"><i class="fa-solid fa-lightbulb" style="color:#f59e0b"></i> The deception engine can pre-stage traps for these stages before the attacker reaches them.</div>';
}
