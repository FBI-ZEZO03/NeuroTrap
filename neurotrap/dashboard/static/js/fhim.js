'use strict';

const FLAGS = { EG:'🇪🇬', US:'🇺🇸', DE:'🇩🇪', SA:'🇸🇦', GB:'🇬🇧', FR:'🇫🇷', CN:'🇨🇳', AU:'🇦🇺', JP:'🇯🇵' };

document.addEventListener('DOMContentLoaded', loadAll);

async function loadAll() {
  await Promise.allSettled([loadNodes(), loadRounds()]);
}

async function loadNodes() {
  const res  = await fetch('/api/fhim/nodes').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  const nodes = data.nodes || [];
  const f1    = data.global_f1 || 0;

  document.getElementById('kpi-nodes').textContent    = nodes.length;
  document.getElementById('kpi-global-f1').textContent = (f1 * 100).toFixed(1) + '%';
  const totalSamples = nodes.reduce((a, n) => a + (n.samples_contributed || 0), 0);
  document.getElementById('kpi-samples').textContent  = totalSamples.toLocaleString();

  renderNodes(nodes);
}

async function loadRounds() {
  const res  = await fetch('/api/fhim/rounds').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  renderRounds(data.rounds || []);
}

function renderNodes(nodes) {
  const el = document.getElementById('fhim-nodes-container');
  if (!el) return;
  if (!nodes.length) {
    el.innerHTML = '<div class="preview-placeholder" style="padding:40px">No nodes registered in the mesh</div>';
    return;
  }
  el.innerHTML = '';
  nodes.forEach(n => {
    const flag    = FLAGS[n.location] || '🌐';
    const f1Pct   = ((n.f1_score || 0) * 100).toFixed(1);
    const last    = n.last_round ? timeSince(n.last_round) : 'never';
    const card    = document.createElement('div');
    card.className = 'fhim-node-full-card';
    card.innerHTML = `
      <div class="fhim-node-full-header">
        <span class="fhim-node-flag">${flag}</span>
        <div>
          <div class="fhim-node-name">${n.org_name}</div>
          <div class="fhim-node-id-small">${n.node_id}</div>
        </div>
        <span class="fhim-status-pill ${n.status}">${n.status}</span>
      </div>
      <div class="fhim-node-stats-grid">
        <div class="fhim-node-stat">
          <div class="fhim-node-stat-val">${f1Pct}%</div>
          <div class="fhim-node-stat-lbl">Local F1</div>
        </div>
        <div class="fhim-node-stat">
          <div class="fhim-node-stat-val">${n.rounds_total || 0}</div>
          <div class="fhim-node-stat-lbl">Rounds</div>
        </div>
        <div class="fhim-node-stat">
          <div class="fhim-node-stat-val" style="font-size:14px">${(n.samples_contributed || 0).toLocaleString()}</div>
          <div class="fhim-node-stat-lbl">Samples</div>
        </div>
        <div class="fhim-node-stat">
          <div class="fhim-node-stat-val" style="font-size:14px;color:${n.status==='synced'?'#10b981':'#64748b'}">${n.status}</div>
          <div class="fhim-node-stat-lbl">Status</div>
        </div>
      </div>
      <div class="fhim-node-last">
        <i class="fa-regular fa-clock" style="margin-right:4px"></i>Last round: ${last}
        &nbsp;·&nbsp; Location: ${n.location || 'Unknown'}
      </div>
    `;
    el.appendChild(card);
  });
}

function renderRounds(rounds) {
  const el = document.getElementById('fhim-rounds-container');
  if (!el) return;
  if (!rounds.length) {
    el.innerHTML = '<div style="color:var(--text-muted);font-size:11px;text-align:center;padding:16px">No aggregation rounds yet</div>';
    return;
  }
  el.innerHTML = '';
  rounds.slice(0, 10).forEach(r => {
    const item = document.createElement('div');
    item.className = 'fhim-round-item';
    const ts = r.timestamp ? timeSince(r.timestamp) : '—';
    const f1 = ((r.global_f1_after || 0) * 100).toFixed(1);
    item.innerHTML = `
      <span class="fhim-round-f1">${f1}%</span>
      <span style="color:var(--text-dim)">F1</span>
      <span style="color:var(--text)">${r.participants || '—'} nodes</span>
      <span style="color:var(--text-dim)">·</span>
      <span style="color:var(--text)">${(r.total_samples||0).toLocaleString()} samples</span>
      <span style="margin-left:auto;color:var(--text-muted)">${ts}</span>
    `;
    el.appendChild(item);
  });
}

function timeSince(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}
