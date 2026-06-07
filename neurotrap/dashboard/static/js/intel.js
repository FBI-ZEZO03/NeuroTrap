'use strict';

const INTENT_COLORS = {
  reconnaissance:      '#22d3ee',
  credential_harvesting:'#f59e0b',
  malware_deployment:  '#f43f5e',
  lateral_movement:    '#a855f7',
  cryptomining:        '#10b981',
  bot_enrollment:      '#6366f1',
  unknown:             '#64748b',
};

const SEVERITY_ORDER = ['critical','high','medium','low'];

async function loadIntel() {
  const [intelRes, attackersRes] = await Promise.allSettled([
    fetch('/api/intel').then(r => r.json()).catch(() => ({})),
    fetch('/api/attackers?limit=5').then(r => r.json()).catch(() => ({})),
  ]);

  const data = intelRes.status === 'fulfilled' ? intelRes.value : {};

  renderKPIs(data.summary || {});
  renderIOCTable(data.iocs || []);
  renderCountries(data.top_countries || []);
  renderPorts(data.top_ports || []);
  renderAttackDist(data.attack_type_dist || []);
  renderDashTopCountries(data.top_countries || []);

}

// ── KPIs ──────────────────────────────────────────────────────────────────────

function renderKPIs(s) {
  setText('intel-kpi-iocs', s.total_iocs ?? '—');
  setText('intel-kpi-countries', s.countries_seen ?? '—');
  setText('intel-kpi-top', s.top_threat ?? '—');
}

// ── IOC Table ─────────────────────────────────────────────────────────────────

function renderIOCTable(iocs) {
  const tbody = document.getElementById('intel-ioc-tbody');
  if (!tbody) return;
  if (!iocs.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--t4);padding:28px">No IOCs collected yet</td></tr>';
    return;
  }
  tbody.innerHTML = iocs.slice(0, 30).map(ioc => {
    const color = INTENT_COLORS[ioc.intent] || INTENT_COLORS.unknown;
    const score = ioc.threat_score || 0;
    const scoreColor = score >= 70 ? '#f43f5e' : score >= 40 ? '#f59e0b' : '#64748b';
    const blocked = ioc.is_blocked
      ? '<span style="color:#f43f5e;font-size:10px;font-weight:700">BLOCKED</span>'
      : '<span style="color:#10b981;font-size:10px">Active</span>';
    return `<tr>
      <td style="font-family:var(--font-mono);color:var(--accent)">${ioc.ip}</td>
      <td><span style="color:${scoreColor};font-weight:700">${score}</span></td>
      <td><span style="color:${color};font-size:10px;font-weight:600;text-transform:uppercase">${(ioc.intent||'unknown').replace(/_/g,' ')}</span></td>
      <td style="color:var(--t3)">${ioc.country || '—'}</td>
      <td style="color:var(--t3)">${ioc.session_count || 0}</td>
      <td style="color:var(--t3)">${ioc.ttp_count || 0}</td>
      <td>${blocked}</td>
    </tr>`;
  }).join('');
}

// ── Country Breakdown ─────────────────────────────────────────────────────────

function renderCountries(countries) {
  const el = document.getElementById('intel-countries');
  if (!el) return;
  if (!countries.length) {
    el.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-globe"></i>No data yet</div>';
    return;
  }
  const max = countries[0]?.count || 1;
  el.innerHTML = countries.map((c, i) => {
    const pct = Math.round((c.count / max) * 100);
    const rank_color = i === 0 ? '#f43f5e' : i === 1 ? '#f59e0b' : i === 2 ? '#a855f7' : '#475569';
    return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)">
      <span style="color:${rank_color};font-weight:700;font-size:11px;width:18px;text-align:right">${i+1}</span>
      <span style="flex:1;color:var(--text);font-size:12px">${c.country}</span>
      <div style="width:90px;height:5px;background:var(--border2);border-radius:3px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${rank_color};border-radius:3px"></div>
      </div>
      <span style="color:var(--t3);font-size:11px;width:28px;text-align:right">${c.count}</span>
    </div>`;
  }).join('');
}

// ── Top Ports ────────────────────────────────────────────────────────────────

const PORT_NAMES = { 22:'SSH', 23:'Telnet', 21:'FTP', 80:'HTTP', 443:'HTTPS',
  3306:'MySQL', 3389:'RDP', 5900:'VNC', 1433:'MSSQL', 445:'SMB',
  2222:'SSH-HC', 2323:'Telnet-HC', 8080:'HTTP-alt', 8443:'HTTPS-alt' };

function renderPorts(ports) {
  const el = document.getElementById('intel-ports');
  if (!el) return;
  if (!ports.length) {
    el.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-ethernet"></i>No data yet</div>';
    return;
  }
  const max = ports[0]?.count || 1;
  el.innerHTML = ports.map(p => {
    const pct = Math.round((p.count / max) * 100);
    const name = PORT_NAMES[p.port] || '';
    return `<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--border)">
      <span style="font-family:var(--font-mono);color:#22d3ee;font-size:11px;width:42px">:${p.port}</span>
      <span style="color:var(--t3);font-size:10px;width:48px">${name}</span>
      <div style="flex:1;height:4px;background:var(--border2);border-radius:2px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:#22d3ee;border-radius:2px"></div>
      </div>
      <span style="color:var(--t3);font-size:11px;width:28px;text-align:right">${p.count}</span>
    </div>`;
  }).join('');
}

// ── Attack Type Distribution ──────────────────────────────────────────────────

function renderAttackDist(dist) {
  const el = document.getElementById('intel-attack-dist');
  if (!el) return;
  if (!dist.length) {
    el.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-chart-simple"></i>No events yet</div>';
    return;
  }
  const total = dist.reduce((s, d) => s + d.count, 0) || 1;
  const colors = ['#22d3ee','#f59e0b','#f43f5e','#a855f7','#10b981','#6366f1','#ec4899','#64748b'];
  el.innerHTML = dist.map((d, i) => {
    const pct = Math.round((d.count / total) * 100);
    const color = colors[i % colors.length];
    return `<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
      <span style="color:${color};font-size:10px;font-weight:700;text-transform:uppercase;width:130px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${(d.type||'unknown').replace(/_/g,' ')}</span>
      <div style="flex:1;height:6px;background:var(--border2);border-radius:3px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${color};border-radius:3px;transition:width .4s"></div>
      </div>
      <span style="color:var(--t3);font-size:11px;width:36px;text-align:right">${pct}%</span>
      <span style="color:var(--t4);font-size:10px;width:28px;text-align:right">${d.count}</span>
    </div>`;
  }).join('');
}

// ── Dashboard mini top-countries widget ───────────────────────────────────────

function renderDashTopCountries(countries) {
  const el = document.getElementById('dash-top-countries');
  if (!el) return;
  if (!countries.length) {
    el.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-globe" style="font-size:22px;color:var(--border2)"></i>No attacker data yet</div>';
    return;
  }
  const max = countries[0]?.count || 1;
  el.innerHTML = countries.slice(0, 10).map((c, i) => {
    const pct = Math.round((c.count / max) * 100);
    const rank_color = i === 0 ? '#f43f5e' : i === 1 ? '#f59e0b' : i < 4 ? '#a855f7' : '#475569';
    return `<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid var(--border)">
      <span style="color:${rank_color};font-weight:700;font-size:11px;width:18px;text-align:right">${i+1}</span>
      <span style="flex:1;color:var(--text);font-size:12px">${c.country}</span>
      <div style="width:70px;height:5px;background:var(--border2);border-radius:3px;overflow:hidden">
        <div style="height:100%;width:${pct}%;background:${rank_color};border-radius:3px"></div>
      </div>
      <span style="color:var(--t3);font-size:11px;width:24px;text-align:right">${c.count}</span>
    </div>`;
  }).join('');
}

async function loadDashTopCountries() {
  const data = await fetch('/api/intel').then(r => r.json()).catch(() => ({}));
  renderDashTopCountries(data.top_countries || []);
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
