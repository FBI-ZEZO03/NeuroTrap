'use strict';

const INTENT_META = {
  reconnaissance:        { label: 'Reconnaissance',     color: '#22d3ee', icon: 'fa-magnifying-glass' },
  credential_harvesting: { label: 'Cred Harvesting',    color: '#f59e0b', icon: 'fa-key' },
  malware_deployment:    { label: 'Malware Deployment', color: '#f43f5e', icon: 'fa-virus' },
  lateral_movement:      { label: 'Lateral Movement',   color: '#a855f7', icon: 'fa-arrows-left-right' },
  cryptomining:          { label: 'Cryptomining',       color: '#10b981', icon: 'fa-microchip' },
  bot_enrollment:        { label: 'Bot Enrollment',     color: '#6366f1', icon: 'fa-robot' },
  unknown:               { label: 'Unknown',            color: '#475569', icon: 'fa-question' },
};

const TIER_META = {
  beginner:       { label: 'Beginner',       color: '#22d3ee', icon: 'fa-user',       desc: 'Opportunistic scanners, low skill' },
  automated_bot:  { label: 'Automated Bot',  color: '#f59e0b', icon: 'fa-robot',      desc: 'Script-driven, high-volume attacks' },
  advanced_human: { label: 'Advanced Human', color: '#f43f5e', icon: 'fa-user-ninja', desc: 'Skilled operator, targeted intrusion' },
};

const ATTACK_ICONS = {
  brute_force: 'fa-key', port_scan: 'fa-radar', command_injection: 'fa-terminal',
  malware_upload: 'fa-virus', protocol_anomaly: 'fa-triangle-exclamation',
  tool_fingerprint: 'fa-fingerprint', data_exfiltration: 'fa-file-export',
  lateral_movement: 'fa-arrows-left-right', unknown: 'fa-circle-question',
};

let _behaviorAttackers = [];
let _behaviorSort = { key: 'threat_score', dir: -1 };

/* ── Main loader ─────────────────────────────────────────────────────────── */

function _fetchWithTimeout(url, ms = 10000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  return fetch(url, { signal: ctrl.signal })
    .then(r => r.json())
    .catch(() => ({}))
    .finally(() => clearTimeout(timer));
}

async function loadBehavior() {
  try {
    const [atkRes, statsRes] = await Promise.allSettled([
      _fetchWithTimeout('/api/attackers?limit=500'),
      _fetchWithTimeout('/api/events/stats'),
    ]);

    const attackers = atkRes.status    === 'fulfilled' ? (atkRes.value.attackers || []) : [];
    const stats     = statsRes.status  === 'fulfilled' ? statsRes.value                 : {};

    _behaviorAttackers = attackers;

    renderBehKPIs(attackers, stats);
    renderIntentDist(attackers);
    renderTierBreakdown(attackers);
    renderAttackVectors(stats.by_attack_type || []);
    renderTopCommands(attackers);
    renderConfidenceDist(attackers);
    renderBehaviorTable();
  } catch (err) {
    ['beh-intent-dist','beh-tiers','beh-attack-vectors','beh-top-commands','beh-confidence-dist'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = '<div class="feed-empty">Failed to load data — click Refresh to retry.</div>';
    });
    const tbody = document.getElementById('beh-profile-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:28px">Failed to load — click Refresh to retry.</td></tr>';
  }
}

/* ── KPIs ────────────────────────────────────────────────────────────────── */

function renderBehKPIs(attackers, stats) {
  const _s = (id, v) => { const e = document.getElementById(id); if (e) e.textContent = v; };

  const totalSessions  = attackers.reduce((s, a) => s + (a.session_count || 0), 0);
  const totalCommands  = attackers.reduce((s, a) => s + (a.total_commands || 0), 0);

  let totalConf = 0, confCount = 0;
  attackers.forEach(a => {
    (a.sessions || []).forEach(sess => {
      if (sess.confidence != null) { totalConf += sess.confidence; confCount++; }
    });
  });
  const avgConf = confCount > 0 ? (totalConf / confCount * 100).toFixed(1) + '%' : '—';

  _s('beh-kpi-profiles',   attackers.length || '—');
  _s('beh-kpi-sessions',   totalSessions ? totalSessions.toLocaleString() : '—');
  _s('beh-kpi-commands',   totalCommands ? totalCommands.toLocaleString() : '—');
  _s('beh-kpi-confidence', avgConf);
}

/* ── Intent Distribution ─────────────────────────────────────────────────── */

function renderIntentDist(attackers) {
  const el = document.getElementById('beh-intent-dist');
  if (!el) return;

  const counts = {};
  attackers.forEach(a => { const k = a.classified_intent || 'unknown'; counts[k] = (counts[k] || 0) + 1; });

  const total  = attackers.length || 1;
  const sorted = Object.entries(INTENT_META)
    .map(([k, meta]) => ({ k, meta, count: counts[k] || 0 }))
    .sort((a, b) => b.count - a.count);

  el.innerHTML = sorted.map(({ k, meta, count }) => {
    const pct = Math.round((count / total) * 100);
    const dim = count === 0;
    return `<div style="display:flex;align-items:center;gap:12px;margin-bottom:15px">
      <div style="width:34px;height:34px;border-radius:9px;background:${meta.color}${dim?'0d':'1a'};border:1px solid ${meta.color}${dim?'22':'44'};display:flex;align-items:center;justify-content:center;flex-shrink:0">
        <i class="fa-solid ${meta.icon}" style="color:${dim?'var(--border-dim)':meta.color};font-size:13px"></i>
      </div>
      <div style="flex:1;min-width:0">
        <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:5px">
          <span style="font-size:12px;color:${dim?'var(--text-muted)':'var(--text-primary)'};font-weight:${dim?'400':'600'}">${meta.label}</span>
          <span style="font-size:11px;color:${dim?'var(--border-dim)':meta.color};font-weight:700;font-family:var(--font-mono)">
            ${count} <span style="font-size:10px;color:var(--text-muted);font-weight:400">${pct}%</span>
          </span>
        </div>
        <div style="height:5px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden">
          <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,${meta.color}66,${meta.color});border-radius:3px;transition:width .6s ease-out"></div>
        </div>
      </div>
    </div>`;
  }).join('');
}

/* ── Tier Breakdown ──────────────────────────────────────────────────────── */

function renderTierBreakdown(attackers) {
  const el = document.getElementById('beh-tiers');
  if (!el) return;

  const counts = {};
  attackers.forEach(a => { const k = a.attacker_tier || 'beginner'; counts[k] = (counts[k] || 0) + 1; });
  const total = attackers.length || 1;

  el.innerHTML = Object.entries(TIER_META).map(([k, meta]) => {
    const count = counts[k] || 0;
    const pct   = Math.round((count / total) * 100);
    const dim   = count === 0;
    return `<div style="background:${meta.color}${dim?'08':'0e'};border:1px solid ${meta.color}${dim?'22':'33'};border-radius:10px;padding:14px 16px;margin-bottom:10px">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
        <div style="width:40px;height:40px;border-radius:10px;background:${meta.color}${dim?'0d':'1a'};border:1px solid ${meta.color}${dim?'22':'44'};display:flex;align-items:center;justify-content:center;flex-shrink:0">
          <i class="fa-solid ${meta.icon}" style="color:${dim?'var(--border-dim)':meta.color};font-size:16px"></i>
        </div>
        <div style="flex:1;min-width:0">
          <div style="font-size:13px;font-weight:700;color:${dim?'var(--text-muted)':meta.color}">${meta.label}</div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px;line-height:1.3">${meta.desc}</div>
        </div>
        <div style="text-align:right;flex-shrink:0">
          <div style="font-size:26px;font-weight:800;color:${dim?'var(--border-dim)':meta.color};font-family:var(--font-mono);line-height:1">${count}</div>
          <div style="font-size:10px;color:var(--text-muted)">${pct}%</div>
        </div>
      </div>
      <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${meta.color};border-radius:2px;transition:width .6s ease-out"></div>
      </div>
    </div>`;
  }).join('');
}

/* ── Attack Vectors ──────────────────────────────────────────────────────── */

function renderAttackVectors(byType) {
  const el = document.getElementById('beh-attack-vectors');
  if (!el) return;

  if (!byType.length) {
    el.innerHTML = '<div class="feed-empty">No event data yet</div>';
    return;
  }

  const total  = byType.reduce((s, t) => s + (t.count || 0), 0) || 1;
  const max    = byType[0]?.count || 1;
  const colors = ['#f43f5e','#f59e0b','#a855f7','#22d3ee','#10b981','#6366f1','#ec4899','#64748b'];

  el.innerHTML = byType.map((t, i) => {
    const key    = t._id || t.type || 'unknown';
    const pct    = Math.round((t.count / max) * 100);
    const share  = Math.round((t.count / total) * 100);
    const color  = colors[i % colors.length];
    const icon   = ATTACK_ICONS[key] || 'fa-bolt';
    const label  = key.replace(/_/g, ' ');
    return `<div style="display:flex;align-items:center;gap:10px;margin-bottom:13px">
      <i class="fa-solid ${icon}" style="color:${color};width:14px;text-align:center;font-size:11px;flex-shrink:0"></i>
      <span style="font-size:11px;color:var(--text-primary);width:148px;text-transform:capitalize;flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${label}</span>
      <div style="flex:1;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,${color}55,${color});border-radius:3px;transition:width .5s"></div>
      </div>
      <span style="font-size:10px;color:${color};font-weight:700;font-family:var(--font-mono);width:44px;text-align:right;flex-shrink:0">${(t.count||0).toLocaleString()}</span>
      <span style="font-size:10px;color:var(--text-muted);width:28px;text-align:right;flex-shrink:0">${share}%</span>
    </div>`;
  }).join('');
}

/* ── Top Commands ────────────────────────────────────────────────────────── */

function renderTopCommands(attackers) {
  const el = document.getElementById('beh-top-commands');
  if (!el) return;

  const freq = {};
  const cmdToIPs = {};
  attackers.forEach(a => {
    (a.sessions || []).forEach(sess => {
      (sess.commands || []).forEach(cmd => {
        const c = cmd.trim();
        if (!c) return;
        freq[c] = (freq[c] || 0) + 1;
        if (!cmdToIPs[c]) cmdToIPs[c] = new Set();
        cmdToIPs[c].add(a.src_ip);
      });
    });
  });

  const sorted = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 15);

  if (!sorted.length) {
    el.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-terminal" style="font-size:22px;color:var(--border-dim)"></i>No commands captured yet</div>';
    return;
  }

  const maxCount = sorted[0][1];

  el.innerHTML = sorted.map(([cmd, count], i) => {
    const pct   = Math.round((count / maxCount) * 100);
    const ips   = cmdToIPs[cmd]?.size || 0;
    const color = i < 3 ? '#f43f5e' : i < 7 ? '#f59e0b' : '#475569';
    const trunc = cmd.length > 42 ? cmd.slice(0, 42) + '…' : cmd;
    return `<div style="margin-bottom:10px" title="${cmd.replace(/"/g,'&quot;')}">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
        <code style="font-family:var(--font-mono);font-size:10px;color:#10b981;background:rgba(16,185,129,0.08);padding:3px 8px;border-radius:4px;border:1px solid rgba(16,185,129,0.2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${trunc}</code>
        <span style="font-size:9px;color:var(--text-muted);flex-shrink:0">${ips} IP${ips!==1?'s':''}</span>
        <span style="font-size:11px;color:${color};font-weight:800;font-family:var(--font-mono);flex-shrink:0">${count}×</span>
      </div>
      <div style="height:3px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:linear-gradient(90deg,${color}55,${color});border-radius:2px;transition:width .5s"></div>
      </div>
    </div>`;
  }).join('');
}

/* ── Confidence Distribution ─────────────────────────────────────────────── */

function renderConfidenceDist(attackers) {
  const el = document.getElementById('beh-confidence-dist');
  if (!el) return;

  const buckets = new Array(10).fill(0);
  let total = 0;
  attackers.forEach(a => {
    (a.sessions || []).forEach(sess => {
      if (sess.confidence != null) {
        buckets[Math.min(9, Math.floor(sess.confidence * 10))]++;
        total++;
      }
    });
  });

  if (!total) {
    el.innerHTML = '<div class="feed-empty">No session confidence data yet</div>';
    return;
  }

  const maxB   = Math.max(...buckets, 1);
  const colors = ['#475569','#64748b','#64748b','#6366f1','#6366f1','#a855f7','#f59e0b','#f59e0b','#10b981','#10b981'];
  const labels = ['0','10','20','30','40','50','60','70','80','90'];

  // Summary stats
  let hi = 0, hiPct = '';
  buckets.forEach((v, i) => { if (v > hi) { hi = v; hiPct = `${labels[i]}–${+labels[i]+10}%`; } });

  el.innerHTML = `
    <div style="display:flex;align-items:flex-end;gap:5px;height:120px">
      ${buckets.map((count, i) => {
        const h     = maxB > 0 ? Math.max(count > 0 ? 4 : 0, Math.round((count / maxB) * 100)) : 0;
        const color = colors[i];
        const share = Math.round((count / total) * 100);
        return `<div style="flex:1;display:flex;flex-direction:column;align-items:center;gap:2px" title="${labels[i]}–${+labels[i]+10}% confidence: ${count} sessions (${share}%)">
          <span style="font-size:8px;color:${count>0?color:'transparent'};font-weight:700;font-family:var(--font-mono)">${count||''}</span>
          <div style="width:100%;height:${h}px;background:linear-gradient(to top,${color}44,${color});border-radius:3px 3px 0 0;min-height:${count>0?4:0}px;transition:height .5s ease-out;position:relative">
            ${count>0&&h>20?`<div style="position:absolute;bottom:-1px;left:0;right:0;height:1px;background:${color};box-shadow:0 0 6px ${color}"></div>`:''}
          </div>
        </div>`;
      }).join('')}
    </div>
    <div style="display:flex;justify-content:space-between;padding:4px 0 2px;margin-top:2px">
      ${labels.map(l => `<span style="flex:1;text-align:center;font-size:8px;color:var(--text-muted);font-family:var(--font-mono)">${l}%</span>`).join('')}
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:10px;padding-top:10px;border-top:1px solid var(--border-dim)">
      <span style="font-size:11px;color:var(--text-muted)">${total.toLocaleString()} sessions analyzed</span>
      <span style="font-size:11px;color:var(--text-muted)">Peak confidence bucket: <span style="color:#10b981;font-weight:600">${hiPct}</span></span>
    </div>`;
}

/* ── Profiles Table ──────────────────────────────────────────────────────── */

function renderBehaviorTable() {
  const tbody = document.getElementById('beh-profile-tbody');
  const countEl = document.getElementById('beh-table-count');
  if (!tbody) return;

  const sorted = [..._behaviorAttackers].sort((a, b) => {
    const av = _behSortVal(a, _behaviorSort.key);
    const bv = _behSortVal(b, _behaviorSort.key);
    return av < bv ? -_behaviorSort.dir : av > bv ? _behaviorSort.dir : 0;
  });

  if (countEl) countEl.textContent = `${sorted.length} profiles`;

  if (!sorted.length) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-muted);padding:28px">No profiles yet</td></tr>';
    return;
  }

  tbody.innerHTML = sorted.map(a => {
    const intent = a.classified_intent || 'unknown';
    const tier   = a.attacker_tier     || 'beginner';
    const iMeta  = INTENT_META[intent] || INTENT_META.unknown;
    const tMeta  = TIER_META[tier]     || TIER_META.beginner;
    const score  = a.threat_score || 0;
    const sColor = score >= 70 ? '#f43f5e' : score >= 40 ? '#f59e0b' : '#64748b';

    const sessions  = a.sessions || [];
    const confVals  = sessions.map(s => s.confidence).filter(c => c != null);
    const avgConf   = confVals.length ? confVals.reduce((s, v) => s + v, 0) / confVals.length : 0;
    const cColor    = avgConf >= 0.8 ? '#10b981' : avgConf >= 0.5 ? '#f59e0b' : '#64748b';

    return `<tr onclick="openModal('${a.src_ip}')" style="cursor:pointer"
        onmouseover="this.style.background='rgba(255,255,255,0.03)'"
        onmouseout="this.style.background=''">
      <td style="font-family:var(--font-mono);color:var(--accent);border-left:3px solid ${iMeta.color}">${a.src_ip}</td>
      <td style="color:var(--text-muted)">${a.country || '—'}</td>
      <td>
        <span style="display:inline-flex;align-items:center;gap:5px;background:${iMeta.color}1a;border:1px solid ${iMeta.color}44;border-radius:20px;padding:3px 9px 3px 7px">
          <i class="fa-solid ${iMeta.icon}" style="color:${iMeta.color};font-size:9px"></i>
          <span style="font-size:10px;color:${iMeta.color};font-weight:700">${iMeta.label}</span>
        </span>
      </td>
      <td>
        <span style="display:inline-flex;align-items:center;gap:5px;background:${tMeta.color}1a;border:1px solid ${tMeta.color}44;border-radius:20px;padding:3px 9px 3px 7px">
          <i class="fa-solid ${tMeta.icon}" style="color:${tMeta.color};font-size:9px"></i>
          <span style="font-size:10px;color:${tMeta.color};font-weight:600">${tMeta.label}</span>
        </span>
      </td>
      <td>
        <div style="display:flex;align-items:center;gap:7px">
          <div style="width:52px;height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden">
            <div style="height:100%;width:${Math.round(avgConf*100)}%;background:${cColor};border-radius:2px"></div>
          </div>
          <span style="font-size:10px;color:${cColor};font-weight:700;font-family:var(--font-mono)">${(avgConf*100).toFixed(0)}%</span>
        </div>
      </td>
      <td style="color:var(--text-primary);font-family:var(--font-mono)">${(a.session_count||0).toLocaleString()}</td>
      <td style="color:var(--text-primary);font-family:var(--font-mono)">${(a.total_commands||0).toLocaleString()}</td>
      <td>
        <span style="color:${sColor};font-weight:800;font-family:var(--font-mono)">${score.toFixed(1)}</span>
        <div style="width:36px;height:3px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden;display:inline-block;margin-left:6px;vertical-align:middle">
          <div style="height:100%;width:${Math.round(score)}%;background:${sColor};border-radius:2px"></div>
        </div>
      </td>
      <td style="color:var(--text-muted);font-size:11px">${fmtTs(a.first_seen)}</td>
      <td style="color:var(--text-muted);font-size:11px">${fmtTs(a.last_seen)}</td>
    </tr>`;
  }).join('');

  // Highlight active sort column header
  document.querySelectorAll('[data-beh-sort]').forEach(th => {
    const key = th.dataset.behSort;
    const arrow = th.querySelector('.sort-arrow');
    if (key === _behaviorSort.key) {
      th.style.color = 'var(--accent)';
      if (arrow) arrow.textContent = _behaviorSort.dir === 1 ? ' ↑' : ' ↓';
    } else {
      th.style.color = '';
      if (arrow) arrow.textContent = '';
    }
  });
}

function _behSortVal(a, key) {
  if (key === 'avg_confidence') {
    const vals = (a.sessions || []).map(s => s.confidence).filter(c => c != null);
    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
  }
  return a[key] ?? '';
}

function sortBehavior(key) {
  const numericDesc = ['threat_score','session_count','total_commands','avg_confidence','last_seen','first_seen'];
  if (_behaviorSort.key === key) {
    _behaviorSort.dir *= -1;
  } else {
    _behaviorSort.key = key;
    _behaviorSort.dir = numericDesc.includes(key) ? -1 : 1;
  }
  renderBehaviorTable();
}
