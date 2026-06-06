'use strict';

const BIAS_COLORS = {
  curiosity_gap:    '#f59e0b',
  confirmation_bias:'#8b5cf6',
  sunk_cost:        '#10b981',
  authority_signal: '#00d4ff',
  scarcity_framing: '#ef4444',
};
const BIAS_LABELS = {
  curiosity_gap:    'Curiosity Gap',
  confirmation_bias:'Confirmation Bias',
  sunk_cost:        'Sunk Cost Trap',
  authority_signal: 'Authority Signals',
  scarcity_framing: 'Scarcity Framing',
};

document.addEventListener('DOMContentLoaded', loadAll);

async function loadAll() {
  await Promise.allSettled([loadProfiles(), loadInjections()]);
}

async function loadProfiles() {
  const res  = await fetch('/api/cbee/profiles').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  const profiles = data.profiles || [];
  renderProfiles(profiles);

  document.getElementById('kpi-profiles').textContent = profiles.length;
  if (profiles.length) {
    const dominated = profiles.map(p => p.dominant).reduce((acc, v) => (acc[v] = (acc[v]||0)+1, acc), {});
    const topBias   = Object.entries(dominated).sort((a,b)=>b[1]-a[1])[0]?.[0] || '—';
    document.getElementById('kpi-dominant').textContent = BIAS_LABELS[topBias]?.split(' ')[0] || topBias;
  }
}

async function loadInjections() {
  const res  = await fetch('/api/cbee/injections').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  const injections = data.injections || [];
  renderInjections(injections);
  document.getElementById('kpi-injections').textContent = injections.length;
}

function renderProfiles(profiles) {
  const el = document.getElementById('profiles-container');
  if (!el) return;
  if (!profiles.length) {
    el.innerHTML = '<div class="preview-placeholder" style="padding:40px"><i class="fa-solid fa-users" style="font-size:28px;color:rgba(245,158,11,0.3);display:block;margin-bottom:12px"></i>No active attacker sessions being analyzed</div>';
    return;
  }
  el.innerHTML = '';
  profiles.forEach(p => {
    const card = document.createElement('div');
    card.className = 'profile-card';
    const bars = Object.keys(BIAS_LABELS).map(key => {
      const val = Math.round(p[key] || 0);
      const color = BIAS_COLORS[key];
      const isDominant = key === p.dominant;
      return `<div class="profile-bar-row">
        <div class="profile-bar-label" style="${isDominant?'color:var(--text);font-weight:600':''}">${BIAS_LABELS[key]}</div>
        <div class="profile-bar-track"><div class="profile-bar-fill" style="width:${val}%;background:${color};${isDominant?'box-shadow:0 0 6px '+color:''};"></div></div>
        <div class="profile-bar-val" style="${isDominant?'color:'+color:''}">${val}</div>
      </div>`;
    }).join('');
    card.innerHTML = `
      <div class="profile-card-header">
        <span class="profile-ip">${p.src_ip}</span>
        <span class="profile-overall" style="color:${BIAS_COLORS[p.dominant]}">overall: ${(p.overall||0).toFixed(1)}</span>
        <span class="profile-dominant">${(BIAS_LABELS[p.dominant]||p.dominant||'').replace(' ',' ')}</span>
      </div>
      <div class="profile-bars">${bars}</div>
    `;
    el.appendChild(card);
  });
}

function renderInjections(injections) {
  const el = document.getElementById('injections-container');
  if (!el) return;
  if (!injections.length) {
    el.innerHTML = '<div style="color:var(--text-muted);font-size:11px;text-align:center;padding:20px">No bait injections yet</div>';
    return;
  }
  el.innerHTML = '';
  injections.forEach(inj => {
    const card = document.createElement('div');
    card.className = 'injection-card';
    const color = BIAS_COLORS[inj.bias_trigger] || '#64748b';
    const ts = inj.created_at ? timeSince(inj.created_at) : '—';
    card.innerHTML = `
      <div class="injection-header">
        <i class="fa-solid fa-syringe" style="color:${color}"></i>
        <span style="color:var(--accent);font-weight:700">${inj.src_ip}</span>
        <span style="color:${color};font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:1px">${(inj.bias_trigger||'').replace(/_/g,' ')}</span>
        <span style="margin-left:auto;color:var(--text-muted)">${ts}</span>
      </div>
      <div style="color:var(--text-dim)">
        Score: <b style="color:#f59e0b">${(inj.bias_score||0).toFixed(1)}</b>
        &nbsp;·&nbsp; Assets: <b style="color:var(--text)">${(inj.assets||[]).length}</b>
        &nbsp;·&nbsp; <span style="color:${inj.executed?'#10b981':'#64748b'}">${inj.executed?'✓ Injected':'Pending'}</span>
      </div>
    `;
    el.appendChild(card);
  });
}

async function scoreSession() {
  const cmdsRaw = document.getElementById('scorer-cmds').value;
  const duration = parseFloat(document.getElementById('scorer-duration').value) || 0;
  const logins   = parseInt(document.getElementById('scorer-logins').value) || 1;
  const commands = cmdsRaw.split('\n').map(c => c.trim()).filter(Boolean);

  const btn = document.querySelector('.inno-action-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing…';

  try {
    const res  = await fetch('/api/cbee/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ commands, duration_secs: duration, login_attempts: logins }),
    });
    const data = await res.json();
    renderScoreResult(data);
  } catch (e) {
    // Demo fallback
    renderScoreResult({ curiosity_gap:72, confirmation_bias:38, sunk_cost:55, authority_signal:91, scarcity_framing:44, overall:60, dominant:'authority_signal' });
  }
  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-bolt"></i> Analyze Bias';
}

function renderScoreResult(data) {
  const el = document.getElementById('score-result');
  el.classList.remove('hidden');
  el.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
      <b style="font-size:13px">Bias Analysis Result</b>
      <span style="font-family:var(--font-mono);font-size:11px;color:var(--text-dim)">Overall: <b style="color:#f59e0b;font-size:14px">${(data.overall||0).toFixed(1)}</b></span>
    </div>
    ${Object.keys(BIAS_LABELS).map(key => {
      const val = Math.round(data[key] || 0);
      const color = BIAS_COLORS[key];
      const isDom = key === data.dominant;
      return `<div class="score-result-bar" style="${isDom?'background:rgba(255,255,255,0.03);padding:4px 6px;border-radius:4px':''}">
        <div class="score-result-label" style="${isDom?'color:var(--text);font-weight:700':''}">${BIAS_LABELS[key]}${isDom?' ★':''}</div>
        <div class="score-result-track"><div class="score-result-fill" style="width:${val}%;background:${color};${isDom?'box-shadow:0 0 8px '+color:''}"></div></div>
        <div class="score-result-val" style="${isDom?'color:'+color:''}">${val}</div>
      </div>`;
    }).join('')}
    <div style="margin-top:8px;font-size:11px;font-family:var(--font-mono);color:var(--text-dim)">
      Dominant trigger: <b style="color:${BIAS_COLORS[data.dominant]}">${BIAS_LABELS[data.dominant]||data.dominant}</b>
    </div>
  `;
}

function timeSince(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  return `${Math.floor(s/3600)}h ago`;
}
