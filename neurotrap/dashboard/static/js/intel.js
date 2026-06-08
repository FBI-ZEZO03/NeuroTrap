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
  const data = await fetch('/api/intel').then(r => r.json()).catch(() => ({}));
  renderKPIs(data.summary || {});
  renderIOCTable(data.iocs || []);
  renderCountries(data.top_countries || []);
  renderPorts(data.top_ports || []);
  renderAttackDist(data.attack_type_dist || []);
  renderDashTopCountries(data.top_countries || []);
}

// ── MITRE ATT&CK section ─────────────────────────────────────────────────────

async function loadMitre() {
  const heatmapEl = document.getElementById('mitre-heatmap');
  const listEl    = document.getElementById('mitre-technique-list');
  if (heatmapEl) heatmapEl.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-circle-notch fa-spin"></i>Loading…</div>';
  if (listEl)    listEl.innerHTML    = '<div class="feed-empty"><i class="fa-solid fa-circle-notch fa-spin"></i>Loading…</div>';

  const d = await fetch('/api/attackers?limit=500').then(r => r.json()).catch(() => ({}));
  const attackers = d.attackers || [];
  renderMitreHeatmap(attackers);
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

// ── MITRE ATT&CK rendering ────────────────────────────────────────────────────

const MITRE_TACTICS = [
  { id:'reconnaissance',       label:'Reconnaissance',     short:'Recon',      color:'#22d3ee' },
  { id:'resource-development', label:'Resource Development',short:'Res Dev',    color:'#06b6d4' },
  { id:'initial-access',       label:'Initial Access',     short:'Init Access', color:'#f59e0b' },
  { id:'execution',            label:'Execution',          short:'Execution',   color:'#f97316' },
  { id:'persistence',          label:'Persistence',        short:'Persist',     color:'#ef4444' },
  { id:'privilege-escalation', label:'Privilege Escalation',short:'Priv Esc',  color:'#f43f5e' },
  { id:'defense-evasion',      label:'Defense Evasion',    short:'Def Evasion', color:'#e879f9' },
  { id:'credential-access',    label:'Credential Access',  short:'Cred Access', color:'#a855f7' },
  { id:'discovery',            label:'Discovery',          short:'Discovery',   color:'#6366f1' },
  { id:'lateral-movement',     label:'Lateral Movement',   short:'Lateral',     color:'#3b82f6' },
  { id:'collection',           label:'Collection',         short:'Collection',  color:'#10b981' },
  { id:'command-and-control',  label:'Command & Control',  short:'C2',          color:'#14b8a6' },
  { id:'exfiltration',         label:'Exfiltration',       short:'Exfil',       color:'#84cc16' },
  { id:'impact',               label:'Impact',             short:'Impact',      color:'#dc2626' },
];

function _normalizeTactic(raw) {
  if (!raw) return 'unknown';
  return raw.toLowerCase().replace(/\s+/g, '-').replace(/_/g, '-');
}

// Global store for detail panel
let _mitreData = { tacticMap:{}, techCounts:{}, attackersByTech:{} };

function renderMitreHeatmap(attackers) {
  const heatmapEl = document.getElementById('mitre-heatmap');
  const listEl    = document.getElementById('mitre-technique-list');
  if (!heatmapEl) return;

  // Aggregate
  const tacticMap      = {};
  const techCounts     = {};
  const attackersByTech = {};

  attackers.forEach(a => {
    (a.ttps || []).forEach(t => {
      const tac   = _normalizeTactic(t.tactic);
      const tid   = t.technique_id || 'T????';
      const tname = t.technique_name || tid;

      if (!tacticMap[tac]) tacticMap[tac] = {};
      if (!tacticMap[tac][tid]) tacticMap[tac][tid] = { name:tname, tactic:t.tactic||tac, count:0, commands:[] };
      tacticMap[tac][tid].count++;
      if (t.matched_command && !tacticMap[tac][tid].commands.includes(t.matched_command))
        tacticMap[tac][tid].commands.push(t.matched_command);

      if (!techCounts[tid]) techCounts[tid] = { name:tname, tactic:t.tactic||tac, count:0 };
      techCounts[tid].count++;

      if (!attackersByTech[tid]) attackersByTech[tid] = new Set();
      attackersByTech[tid].add(a.src_ip);
    });
  });

  _mitreData = { tacticMap, techCounts, attackersByTech };

  const totalTechs  = Object.keys(techCounts).length;
  const totalHits   = Object.values(techCounts).reduce((s,v)=>s+v.count,0);
  const activeTacs  = MITRE_TACTICS.filter(t => tacticMap[t.id] && Object.keys(tacticMap[t.id]).length > 0).length;
  const topTacEntry = MITRE_TACTICS.map(t => ({
    label: t.short,
    hits:  Object.values(tacticMap[t.id] || {}).reduce((s,v)=>s+v.count,0),
  })).sort((a,b)=>b.hits-a.hits)[0];

  // KPIs
  const setText = (id, v) => { const e=document.getElementById(id); if(e) e.textContent=v; };
  setText('mitre-kpi-techs',  totalTechs || '—');
  setText('mitre-kpi-tactics', activeTacs ? `${activeTacs} / 14` : '—');
  setText('mitre-kpi-hits',   totalHits  || '—');
  setText('mitre-kpi-top',    topTacEntry?.hits ? topTacEntry.label : '—');
  const upd = document.getElementById('mitre-last-updated');
  if (upd) upd.textContent = `Updated ${new Date().toLocaleTimeString('en-GB')}`;

  if (!totalTechs) {
    heatmapEl.innerHTML = `<div class="feed-empty" style="flex-direction:column;gap:10px;padding:40px 0">
      <i class="fa-solid fa-shield-halved" style="font-size:32px;color:var(--border-dim)"></i>
      <span>No TTP data yet</span>
      <span style="font-size:11px;color:var(--text-muted)">Attackers need active sessions with shell commands to generate MITRE mappings</span>
    </div>`;
    if (listEl) listEl.innerHTML = '';
    return;
  }

  // ── Navigator heatmap ────────────────────────────────────────────────────────
  const maxCount = Math.max(...Object.values(tacticMap).flatMap(t=>Object.values(t).map(v=>v.count)), 1);

  const activeTacList   = MITRE_TACTICS.filter(t => tacticMap[t.id] && Object.keys(tacticMap[t.id]).length > 0);
  const inactiveTacList = MITRE_TACTICS.filter(t => !tacticMap[t.id] || Object.keys(tacticMap[t.id]).length === 0);

  const cols = activeTacList.map(tac => {
    const techs    = tacticMap[tac.id] || {};
    const techList = Object.entries(techs).sort((a,b)=>b[1].count-a[1].count);
    const tacHits  = Object.values(techs).reduce((s,v)=>s+v.count,0);

    const cells = techList.map(([tid, tv]) => {
      const norm  = Math.max(0.15, tv.count / maxCount);
      const alpha = Math.round(norm * 220).toString(16).padStart(2,'0');
      const bg    = `${tac.color}${alpha}`;
      const bdr   = `${tac.color}${Math.round(norm * 160).toString(16).padStart(2,'0')}`;
      const attackerCount = (attackersByTech[tid]||new Set()).size;
      return `<div
          onclick="showMitreDetail('${tid}')"
          style="background:${bg};border:1px solid ${bdr};border-radius:5px;padding:7px 9px;margin-bottom:4px;cursor:pointer;transition:all .15s"
          onmouseover="this.style.filter='brightness(1.3)';this.style.transform='translateY(-1px)'"
          onmouseout="this.style.filter='';this.style.transform=''">
        <div style="font-family:var(--font-mono,'JetBrains Mono',monospace);font-size:10px;color:${tac.color};font-weight:800;letter-spacing:.03em">${tid}</div>
        <div style="font-size:9px;color:rgba(248,250,252,0.9);margin-top:3px;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">${tv.name}</div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-top:5px">
          <span style="font-size:8.5px;color:rgba(100,116,139,0.9)">${attackerCount} IP</span>
          <span style="font-size:10.5px;color:${tac.color};font-weight:800">${tv.count}×</span>
        </div>
      </div>`;
    }).join('');

    return `<div style="flex:1;min-width:160px;max-width:280px;display:flex;flex-direction:column">
      <div style="background:${tac.color}20;border:1px solid ${tac.color}55;border-radius:7px 7px 0 0;padding:9px 12px;text-align:center;margin-bottom:5px">
        <div style="font-size:10px;font-weight:800;color:${tac.color};text-transform:uppercase;letter-spacing:.08em">${tac.short}</div>
        <div style="font-size:8.5px;color:rgba(100,116,139,0.9);margin-top:3px">${techList.length} tech · <span style="color:${tac.color};font-weight:700">${tacHits}</span> hits</div>
      </div>
      <div>${cells}</div>
    </div>`;
  }).join('');

  const inactiveBadges = inactiveTacList.map(t =>
    `<span style="font-size:9px;font-weight:600;color:rgba(255,255,255,0.2);background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:4px;padding:3px 8px;text-transform:uppercase;letter-spacing:.05em">${t.short}</span>`
  ).join('');

  heatmapEl.innerHTML = `
    <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start">${cols}</div>
    ${inactiveTacList.length ? `
    <div style="margin-top:14px;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06);display:flex;align-items:center;gap:8px;flex-wrap:wrap">
      <span style="font-size:9px;color:rgba(100,116,139,0.5);font-weight:600;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap">No activity:</span>
      ${inactiveBadges}
    </div>` : ''}
  `;

  // ── Top Techniques ranked list ────────────────────────────────────────────────
  if (!listEl) return;
  const sorted  = Object.entries(techCounts).sort((a,b)=>b[1].count-a[1].count);
  const maxTech = sorted[0]?.[1].count || 1;

  listEl.innerHTML = sorted.map(([tid, tv], i) => {
    const pct     = Math.round((tv.count / maxTech) * 100);
    const tacMeta = MITRE_TACTICS.find(t => _normalizeTactic(tv.tactic) === t.id);
    const color   = tacMeta?.color || '#475569';
    const atkCount= (attackersByTech[tid]||new Set()).size;
    const tacLabel = tacMeta?.short || tv.tactic || '—';
    return `<div onclick="showMitreDetail('${tid}')"
        style="display:grid;grid-template-columns:52px 1fr 110px 90px 44px;gap:0;align-items:center;padding:7px 0;border-bottom:1px solid var(--border-dim);cursor:pointer;transition:background .12s;border-radius:2px"
        onmouseover="this.style.background='rgba(255,255,255,0.03)'" onmouseout="this.style.background=''">
      <span style="font-family:var(--font-mono,'JetBrains Mono',monospace);font-size:10px;color:${color};font-weight:800">${tid}</span>
      <span style="font-size:11px;color:var(--text-primary,#f8fafc);padding-right:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
        ${tv.name}
        <span style="font-size:9px;color:var(--text-muted,#64748b);margin-left:5px">${atkCount}IP</span>
      </span>
      <span style="font-size:9.5px;color:${color};padding-right:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-weight:600">${tacLabel}</span>
      <div style="height:4px;background:rgba(255,255,255,0.06);border-radius:2px;overflow:hidden;margin-right:8px">
        <div style="height:100%;width:${pct}%;background:${color};border-radius:2px;transition:width .4s"></div>
      </div>
      <span style="font-size:11px;color:${color};font-weight:700;text-align:right">${tv.count}</span>
    </div>`;
  }).join('');

  // Auto-show first technique in detail panel
  if (sorted.length) showMitreDetail(sorted[0][0]);
}

function showMitreDetail(tid) {
  const panel = document.getElementById('mitre-detail-panel');
  if (!panel) return;

  const { tacticMap, techCounts, attackersByTech } = _mitreData;
  const tech = techCounts[tid];
  if (!tech) return;

  const tacMeta  = MITRE_TACTICS.find(t => _normalizeTactic(tech.tactic) === t.id);
  const color    = tacMeta?.color || '#475569';
  const ips      = [...(attackersByTech[tid] || [])];
  const tacNorm  = _normalizeTactic(tech.tactic);
  const commands = (tacticMap[tacNorm]?.[tid]?.commands || []);

  const ipRows = ips.slice(0, 8).map(ip =>
    `<div style="font-family:var(--font-mono);font-size:11px;color:var(--accent);padding:3px 0;border-bottom:1px solid var(--border-dim);cursor:pointer"
         onclick="openModal('${ip}')">${ip}</div>`
  ).join('') || `<div style="font-size:11px;color:var(--text-muted);font-style:italic">No IPs</div>`;

  const cmdRows = commands.slice(0, 6).map(c =>
    `<div style="font-family:var(--font-mono);font-size:10px;color:#10b981;background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);border-radius:4px;padding:4px 8px;margin-bottom:4px;word-break:break-all">${c}</div>`
  ).join('') || `<div style="font-size:11px;color:var(--text-muted);font-style:italic">No commands captured</div>`;

  panel.innerHTML = `
    <div style="display:flex;align-items:flex-start;gap:20px;flex-wrap:wrap;margin-bottom:16px">
      <div style="flex:1;min-width:200px">
        <div style="font-family:var(--font-mono);font-size:20px;font-weight:800;color:${color}">${tid}</div>
        <div style="font-size:15px;color:var(--text-primary);font-weight:600;margin-top:4px">${tech.name}</div>
        <div style="display:inline-block;margin-top:8px;background:${color}1a;border:1px solid ${color}44;border-radius:20px;padding:3px 10px;font-size:10px;font-weight:700;color:${color};text-transform:uppercase;letter-spacing:.06em">${tech.tactic}</div>
      </div>
      <div style="display:flex;gap:12px;flex-shrink:0">
        <div style="background:rgba(255,255,255,0.04);border:1px solid var(--border-dim);border-radius:6px;padding:14px 20px;text-align:center">
          <div style="font-size:26px;font-weight:800;color:${color}">${tech.count}</div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px">Total Hits</div>
        </div>
        <div style="background:rgba(255,255,255,0.04);border:1px solid var(--border-dim);border-radius:6px;padding:14px 20px;text-align:center">
          <div style="font-size:26px;font-weight:800;color:${color}">${ips.length}</div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:2px">Unique IPs</div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
      <div>
        <div style="font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">
          <i class="fa-solid fa-terminal" style="color:#10b981;margin-right:4px"></i>Matched Commands
        </div>
        ${cmdRows}
      </div>
      <div>
        <div style="font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px">
          <i class="fa-solid fa-crosshairs" style="color:var(--accent);margin-right:4px"></i>Attacker IPs (${ips.length})
        </div>
        ${ipRows}
        ${ips.length > 8 ? `<div style="font-size:10px;color:var(--text-muted);margin-top:4px">+${ips.length-8} more</div>` : ''}
      </div>
    </div>
  `;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
