'use strict';

document.addEventListener('DOMContentLoaded', loadAll);

async function loadAll() {
  await Promise.allSettled([loadReports(), loadPatches()]);
}

async function loadReports() {
  const res  = await fetch('/api/ashrta/reports').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  const reports = data.reports || [];
  if (reports.length) {
    updateKPIs(reports[0]);
    drawMainGauge(reports[0].hardening_score || 0);
    renderScoreMeta(reports[0]);
    renderTrendBars(reports);
  }
}

async function loadPatches() {
  const res  = await fetch('/api/ashrta/patches').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  renderPatches(data.patches || []);
}

function updateKPIs(r) {
  document.getElementById('kpi-score').textContent   = (r.hardening_score || 0).toFixed(0) + '%';
  document.getElementById('kpi-passed').textContent  = `${r.checks_passed||0} / ${r.checks_total||10}`;
  document.getElementById('kpi-critical').textContent= r.critical_weaknesses || 0;
  document.getElementById('kpi-patches').textContent = r.patches_applied || 0;
  document.getElementById('kpi-score').style.color   = scoreColor(r.hardening_score || 0);
}

function scoreColor(s) {
  return s >= 85 ? '#10b981' : s >= 70 ? '#f59e0b' : '#ef4444';
}

function drawMainGauge(score) {
  const canvas = document.getElementById('ashrta-main-gauge');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  canvas.width  = 240 * dpr; canvas.height = 130 * dpr;
  canvas.style.width = '240px'; canvas.style.height = '130px';
  ctx.scale(dpr, dpr);

  const cx = 120, cy = 120, r = 90;

  // Track
  ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, 2*Math.PI);
  ctx.lineWidth = 16; ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineCap = 'round'; ctx.stroke();

  // Colored arc
  if (score > 0) {
    const color = scoreColor(score);
    const glow  = score >= 85 ? 'rgba(16,185,129,0.4)' : score >= 70 ? 'rgba(245,158,11,0.4)' : 'rgba(239,68,68,0.4)';
    ctx.shadowBlur = 14; ctx.shadowColor = glow;
    ctx.beginPath(); ctx.arc(cx, cy, r, Math.PI, Math.PI + (score/100)*Math.PI);
    ctx.lineWidth = 16; ctx.strokeStyle = color; ctx.lineCap = 'round'; ctx.stroke();
    ctx.shadowBlur = 0;

    // Tick marks
    for (let i = 0; i <= 10; i++) {
      const a = Math.PI + (i/10)*Math.PI;
      const x1 = cx + (r-22)*Math.cos(a), y1 = cy + (r-22)*Math.sin(a);
      const x2 = cx + (r-28)*Math.cos(a), y2 = cy + (r-28)*Math.sin(a);
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2);
      ctx.strokeStyle = 'rgba(255,255,255,0.12)'; ctx.lineWidth = 1.5; ctx.stroke();
    }
  }

  const scoreEl = document.getElementById('gauge-score-val');
  if (scoreEl) {
    scoreEl.textContent = score.toFixed(0) + '%';
    scoreEl.style.color = scoreColor(score);
  }
}

function renderScoreMeta(r) {
  const el = document.getElementById('ashrta-score-meta');
  if (!el) return;
  const rows = [
    ['Checks Passed',    `${r.checks_passed||0} / ${r.checks_total||10}`, r.checks_passed >= r.checks_total ? '#10b981' : '#f59e0b'],
    ['Critical Issues',  r.critical_weaknesses||0, (r.critical_weaknesses||0) > 0 ? '#ef4444' : '#10b981'],
    ['Patches Generated',r.patches_generated||0, '#8b5cf6'],
    ['Patches Applied',  r.patches_applied||0, '#10b981'],
    ['Report ID',        r.report_id || '—', 'var(--text-dim)'],
  ];
  el.innerHTML = rows.map(([label, val, color]) =>
    `<div class="ashrta-meta-row"><span class="ashrta-meta-label">${label}</span><span class="ashrta-meta-val" style="color:${color}">${val}</span></div>`
  ).join('');
}

function renderTrendBars(reports) {
  const el = document.getElementById('ashrta-trend-bars');
  if (!el) return;
  el.innerHTML = '';
  const ordered = [...reports].reverse();
  ordered.forEach(r => {
    const score = r.hardening_score || 0;
    const color = scoreColor(score);
    const bar   = document.createElement('div');
    bar.className = 'ashrta-trend-bar';
    bar.style.height     = `${Math.max((score / 100) * 60, 3)}px`;
    bar.style.background = color;
    bar.dataset.tip = `${score.toFixed(0)}%${r.timestamp ? ' — ' + timeSince(r.timestamp) : ''}`;
    el.appendChild(bar);
  });
}

async function runCycle() {
  const btn = document.getElementById('run-btn');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running Red Team…';

  try {
    const res  = await fetch('/api/ashrta/run', { method: 'POST' });
    const data = await res.json();
    updateKPIs(data);
    drawMainGauge(data.hardening_score || 0);
    renderScoreMeta(data);
    if (data.full_results) renderChecks(data.full_results);
    await loadAll();
  } catch (e) {
    console.error(e);
  }

  btn.disabled = false;
  btn.innerHTML = '<i class="fa-solid fa-play"></i> Run Red Team Cycle';
}

function renderChecks(results) {
  const el = document.getElementById('checks-container');
  const summary = document.getElementById('checks-summary');
  if (!el) return;
  const passed = results.filter(r => r.passed).length;
  if (summary) summary.textContent = `${passed}/${results.length} passed`;
  el.innerHTML = '';
  results.forEach(r => {
    const card = document.createElement('div');
    card.className = `ashrta-check-card ${r.passed ? 'passed' : 'failed'}`;
    card.innerHTML = `
      <div class="ashrta-check-status">
        <i class="fa-solid ${r.passed ? 'fa-check' : 'fa-xmark'}" style="color:${r.passed?'#10b981':'#ef4444'}"></i>
      </div>
      <div class="ashrta-check-content">
        <div class="ashrta-check-title">
          ${(r.check_name||'').replace(/_/g,' ')}
          <span class="ashrta-sev ${r.severity}">${r.severity}</span>
          <span class="conf-pill">conf: ${((r.confidence||0)*100).toFixed(0)}%</span>
        </div>
        <div class="ashrta-check-desc">${r.description || ''}</div>
        ${!r.passed && r.recommendation ? `<div class="ashrta-check-rec"><i class="fa-solid fa-wrench" style="margin-right:4px"></i>${r.recommendation}</div>` : ''}
      </div>
    `;
    el.appendChild(card);
  });
}

function renderPatches(patches) {
  const el = document.getElementById('patches-container');
  if (!el) return;
  if (!patches.length) {
    el.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px">No patches yet — run a cycle</div>';
    return;
  }
  el.innerHTML = '';
  patches.forEach(p => {
    const sevColor = p.severity==='critical'?'#ef4444':p.severity==='high'?'#f59e0b':p.severity==='medium'?'#8b5cf6':'#64748b';
    const card = document.createElement('div');
    card.className = 'ashrta-patch-card';
    card.innerHTML = `
      <div class="ashrta-patch-header">
        <i class="fa-solid fa-wrench" style="color:#10b981;font-size:12px"></i>
        <span class="ashrta-patch-name">${(p.weakness||'').replace(/_/g,' ')}</span>
        <span style="font-size:9px;font-weight:800;color:${sevColor};text-transform:uppercase;letter-spacing:1px">${p.severity}</span>
        <span class="ashrta-patch-target">${p.config_target||''}</span>
        <span style="margin-left:auto;color:#10b981;font-size:10px"><i class="fa-solid fa-check"></i> Applied</span>
      </div>
      <div class="ashrta-patch-diff">
        <div>
          <div class="ashrta-patch-label">Before</div>
          <div class="ashrta-patch-before">${p.before||''}</div>
        </div>
        <div>
          <div class="ashrta-patch-label">After</div>
          <div class="ashrta-patch-after">${p.after||''}</div>
        </div>
      </div>
    `;
    el.appendChild(card);
  });
}

function timeSince(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}
