'use strict';

const ASHRTA_POLL_MS   = 5 * 60 * 1000;
const ASHRTA_STALE_SEC = 6 * 3600;

let _ashrtaTimer = null;

async function loadASHRTA() {
  await Promise.allSettled([_ashrtaLoadReports(), _ashrtaLoadPatches()]);
  clearInterval(_ashrtaTimer);
  _ashrtaTimer = setInterval(() => Promise.allSettled([_ashrtaLoadReports(), _ashrtaLoadPatches()]), ASHRTA_POLL_MS);
}

async function _ashrtaLoadReports() {
  const res     = await fetch('/api/ashrta/reports').catch(() => null);
  const data    = res ? await res.json().catch(() => ({})) : {};
  const reports = data.reports || [];

  if (reports.length) {
    _ashrtaUpdateKPIs(reports[0]);
    drawGauge('ashrta-gauge', reports[0].hardening_score || 0, 220, 120);
    _ashrtaRenderMeta(reports[0]);
    _ashrtaRenderTrend(reports);
    _ashrtaRenderChecks(reports[0].full_results || []);
    _ashrtaSetStatus('idle', reports[0]);
    const age = Date.now() / 1000 - (reports[0].timestamp || 0);
    if (age > ASHRTA_STALE_SEC) _ashrtaTriggerCycle();
  } else {
    _ashrtaSetStatus('running');
    _ashrtaTriggerCycle();
  }
}

async function _ashrtaLoadPatches() {
  const res  = await fetch('/api/ashrta/patches').catch(() => null);
  const data = res ? await res.json().catch(() => ({})) : {};
  _ashrtaRenderPatches(data.patches || []);
}

async function _ashrtaTriggerCycle() {
  _ashrtaSetStatus('running');
  try {
    const res  = await fetch('/api/ashrta/run', { method: 'POST' });
    const data = await res.json();
    _ashrtaUpdateKPIs(data);
    drawGauge('ashrta-gauge', data.hardening_score || 0, 220, 120);
    _ashrtaRenderMeta(data);
    if (data.full_results) _ashrtaRenderChecks(data.full_results);
    await _ashrtaLoadPatches();
    _ashrtaSetStatus('idle', data);
  } catch (e) {
    _ashrtaSetStatus('error');
  }
}

function _ashrtaSetStatus(state, report) {
  const el = document.getElementById('ashrta-status');
  if (!el) return;
  if (state === 'running') {
    el.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Running…';
    el.style.color = 'var(--t3)';
  } else if (state === 'error') {
    el.innerHTML = '<i class="fa-solid fa-circle-exclamation"></i> Unavailable';
    el.style.color = '#f43f5e';
  } else {
    const ago = report?.timestamp ? timeSince(report.timestamp) : '';
    el.innerHTML = `<i class="fa-solid fa-check" style="color:#10b981"></i> Last run ${ago}`;
    el.style.color = 'var(--t3)';
  }
}

function _ashrtaScoreColor(s) {
  return s >= 85 ? '#10b981' : s >= 70 ? '#f59e0b' : '#ef4444';
}

function _ashrtaUpdateKPIs(r) {
  const score = r.hardening_score || 0;
  const el = document.getElementById('ashrta-kpi-score');
  if (el) { el.textContent = score.toFixed(0) + '%'; el.style.color = _ashrtaScoreColor(score); }
  setText('ashrta-kpi-passed',  `${r.checks_passed||0} / ${r.checks_total||10}`);
  setText('ashrta-kpi-crit',    r.critical_weaknesses ?? '—');
  setText('ashrta-kpi-patches', r.patches_applied ?? '—');

  const scoreVal = document.getElementById('ashrta-score-val');
  if (scoreVal) { scoreVal.textContent = score.toFixed(0) + '%'; scoreVal.style.color = _ashrtaScoreColor(score); }
}

function _ashrtaRenderMeta(r) {
  const el = document.getElementById('ashrta-meta');
  if (!el) return;
  const rows = [
    ['Checks Passed',    `${r.checks_passed||0} / ${r.checks_total||10}`, r.checks_passed >= r.checks_total ? '#10b981' : '#f59e0b'],
    ['Critical Issues',  r.critical_weaknesses ?? 0, (r.critical_weaknesses||0) > 0 ? '#ef4444' : '#10b981'],
    ['Patches Generated',r.patches_generated ?? 0, '#8b5cf6'],
    ['Patches Applied',  r.patches_applied ?? 0, '#10b981'],
    ['Report ID',        r.report_id || '—', 'var(--t4)'],
  ];
  el.innerHTML = rows.map(([l, v, c]) =>
    `<div class="ashrta-meta-row"><span class="ashrta-meta-label">${l}</span><span class="ashrta-meta-val" style="color:${c}">${v}</span></div>`
  ).join('');
}

function _ashrtaRenderTrend(reports) {
  const el = document.getElementById('ashrta-trend');
  if (!el) return;
  el.innerHTML = '';
  [...reports].reverse().forEach(r => {
    const s   = r.hardening_score || 0;
    const bar = document.createElement('div');
    bar.className        = 'ashrta-trend-bar';
    bar.style.height     = `${Math.max((s / 100) * 60, 3)}px`;
    bar.style.background = _ashrtaScoreColor(s);
    bar.dataset.tip      = `${s.toFixed(0)}%${r.timestamp ? ' — ' + timeSince(r.timestamp) : ''}`;
    el.appendChild(bar);
  });
}

function _ashrtaRenderChecks(results) {
  const el      = document.getElementById('ashrta-checks');
  const summary = document.getElementById('ashrta-checks-sum');
  if (!el) return;
  if (!results.length) {
    el.innerHTML = '<div style="color:var(--t4);text-align:center;padding:32px;font-size:12px">No check results yet — cycle running…</div>';
    return;
  }
  const passed = results.filter(r => r.passed).length;
  if (summary) summary.textContent = `${passed}/${results.length} passed`;
  el.innerHTML = results.map(r => {
    const sevColor = {critical:'#f43f5e',high:'#f59e0b',medium:'#a855f7',low:'#64748b'}[r.severity] || '#64748b';
    return `
    <div class="ashrta-check-card ${r.passed ? 'passed' : 'failed'}">
      <div class="ashrta-check-status">
        <i class="fa-solid ${r.passed ? 'fa-check' : 'fa-xmark'}" style="color:${r.passed ? '#10b981' : '#ef4444'}"></i>
      </div>
      <div class="ashrta-check-content">
        <div class="ashrta-check-title">
          ${(r.check_name||'').replace(/_/g,' ')}
          <span class="ashrta-sev" style="background:${sevColor}22;color:${sevColor}">${r.severity}</span>
          <span class="conf-pill">conf: ${((r.confidence||0)*100).toFixed(0)}%</span>
        </div>
        <div class="ashrta-check-desc">${r.description || ''}</div>
        ${!r.passed && r.recommendation ? `<div class="ashrta-check-rec"><i class="fa-solid fa-wrench" style="margin-right:4px"></i>${r.recommendation}</div>` : ''}
      </div>
    </div>`;
  }).join('');
}

function _ashrtaRenderPatches(patches) {
  const el = document.getElementById('ashrta-patches');
  if (!el) return;
  if (!patches.length) {
    el.innerHTML = '<div style="color:var(--t4);text-align:center;padding:32px;font-size:12px">No patches yet</div>';
    return;
  }
  el.innerHTML = patches.map(p => {
    const sevColor = {critical:'#ef4444',high:'#f59e0b',medium:'#a855f7',low:'#64748b'}[p.severity] || '#64748b';
    return `
    <div class="ashrta-patch-card">
      <div class="ashrta-patch-header">
        <i class="fa-solid fa-wrench" style="color:#10b981;font-size:12px"></i>
        <span class="ashrta-patch-name">${(p.weakness||'').replace(/_/g,' ')}</span>
        <span style="font-size:9px;font-weight:800;color:${sevColor};text-transform:uppercase;letter-spacing:1px">${p.severity}</span>
        <span class="ashrta-patch-target">${p.config_target||''}</span>
        <span style="margin-left:auto;color:#10b981;font-size:10px"><i class="fa-solid fa-check"></i> Applied</span>
      </div>
      <div class="ashrta-patch-diff">
        <div><div class="ashrta-patch-label">Before</div><div class="ashrta-patch-before">${p.before||''}</div></div>
        <div><div class="ashrta-patch-label">After</div><div class="ashrta-patch-after">${p.after||''}</div></div>
      </div>
    </div>`;
  }).join('');
}
