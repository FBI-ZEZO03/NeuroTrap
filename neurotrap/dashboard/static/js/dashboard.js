/* ── NeuroTrap CADN Dashboard ─────────────────────────────────────────────── */
'use strict';

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  socket: null,
  map: null,
  timelineChart: null,
  breakdownChart: null,
  feedItems: [],
  timelineBuckets: new Array(60).fill(0),
  selectedIP: null,
  totalEvents: 0,
};

// ── Attack type icon map ───────────────────────────────────────────────────────
const ATTACK_ICONS = {
  port_scan:        'fa-magnifying-glass',
  brute_force:      'fa-key',
  malware_upload:   'fa-virus',
  command_injection:'fa-terminal',
  lateral_movement: 'fa-arrows-left-right',
  protocol_anomaly: 'fa-exclamation-triangle',
  data_exfiltration:'fa-file-export',
  tool_fingerprint: 'fa-fingerprint',
  unknown:          'fa-question',
};

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initCharts();
  initWebSocket();
  initControls();
  fetchAll();
  setInterval(fetchAll, 15000);
  loadDashTopCountries();
  // Demo: inject a few synthetic events so the feed isn't empty on first load
  setTimeout(injectDemoEvents, 1200);
});

// ── Clock ─────────────────────────────────────────────────────────────────────
function initClock() {
  const el = document.getElementById('clock');
  function tick() {
    const now = new Date();
    el.textContent = now.toUTCString().replace('GMT', 'UTC');
  }
  tick();
  setInterval(tick, 1000);
}

// ── Demo events (shows UI working without live MongoDB) ───────────────────────
function injectDemoEvents() {
  const demoEvents = [
    { src_ip: '91.234.56.78',  dst_port: 22,   attack_type: 'brute_force',       severity: 'high',     honeypot_source: 'cowrie',  timestamp: Date.now()/1000 - 10 },
    { src_ip: '185.220.101.42',dst_port: 22,   attack_type: 'brute_force',       severity: 'critical', honeypot_source: 'cowrie',  timestamp: Date.now()/1000 - 8  },
    { src_ip: '45.33.32.156',  dst_port: 80,   attack_type: 'port_scan',         severity: 'low',      honeypot_source: 'scapy',   timestamp: Date.now()/1000 - 6  },
    { src_ip: '198.51.100.42', dst_port: 22,   attack_type: 'command_injection',  severity: 'high',     honeypot_source: 'cowrie',  timestamp: Date.now()/1000 - 4  },
    { src_ip: '103.21.244.0',  dst_port: 445,  attack_type: 'malware_upload',    severity: 'critical', honeypot_source: 'dionaea', timestamp: Date.now()/1000 - 2  },
    { src_ip: '2.56.57.90',    dst_port: 3306, attack_type: 'brute_force',       severity: 'medium',   honeypot_source: 'cowrie',  timestamp: Date.now()/1000 - 1  },
  ];
  demoEvents.forEach(e => {
    addFeedItem(e);
    pushTimelineEvent();
  });

  // Demo attackers table
  renderAttackersTable([
    { src_ip:'185.220.101.42', threat_score:94.0, classified_intent:'malware_deployment', attacker_tier:'advanced_human', ttps:[{},{},{},{},{}], last_seen: Date.now()/1000 - 60 },
    { src_ip:'91.234.56.78',   threat_score:78.5, classified_intent:'credential_harvesting', attacker_tier:'automated_bot',  ttps:[{},{},{}], last_seen: Date.now()/1000 - 120 },
    { src_ip:'198.51.100.42',  threat_score:52.0, classified_intent:'reconnaissance',     attacker_tier:'beginner',       ttps:[{}], last_seen: Date.now()/1000 - 240 },
  ]);

  // Demo KPIs
  animateValue('kpi-events',  0, 1247, 800);
  animateValue('kpi-sessions', 0, 3,    600);
  animateValue('kpi-blocked',  0, 8,    700);
  animateValue('kpi-envs',     0, 3,    500);
  document.getElementById('kpi-threat-level').textContent = 'HIGH';
  document.getElementById('kpi-threat-level').style.color = '#ef4444';

  // Demo map markers (real geo coords)
  setTimeout(() => {
    addMapMarker(51.5074, -0.1278, '185.220.101.42', 'critical'); // London
    addMapMarker(40.7128, -74.006, '45.33.32.156',   'low');      // New York
    addMapMarker(35.6762, 139.6503,'103.21.244.0',   'critical'); // Tokyo
    addMapMarker(48.8566,  2.3522, '91.234.56.78',   'high');     // Paris
    addMapMarker(55.7558,  37.6176,'2.56.57.90',     'medium');   // Moscow
  }, 800);
}

function animateValue(id, from, to, duration) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = performance.now();
  function step(now) {
    const t = Math.min((now - start) / duration, 1);
    el.textContent = Math.round(from + (to - from) * easeOut(t)).toLocaleString();
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
const easeOut = t => 1 - Math.pow(1 - t, 3);

// ── Leaflet Map ───────────────────────────────────────────────────────────────
function initMap() {
  state.map = L.map('attack-map', { zoomControl: true, scrollWheelZoom: true, attributionControl: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom: 18 }).addTo(state.map);
  state.map.setView([20, 10], 2);
}

function addMapMarker(lat, lon, srcIp, severity) {
  if (!state.map || !lat || !lon) return;
  const palette = { critical:'#ef4444', high:'#f59e0b', medium:'#8b5cf6', low:'#475569' };
  const color   = palette[severity] || palette.low;
  const radius  = severity === 'critical' ? 9 : severity === 'high' ? 7 : 5;

  // Outer pulse ring
  const ring = L.circleMarker([lat, lon], {
    radius: radius + 5, color, fillColor: 'transparent',
    weight: 1.5, opacity: 0.4,
  }).addTo(state.map);

  // Core dot
  const dot = L.circleMarker([lat, lon], {
    radius, color, fillColor: color, fillOpacity: 0.7, weight: 1,
  }).addTo(state.map);

  dot.bindPopup(`
    <b style="color:${color}">${srcIp}</b><br/>
    <span style="color:#64748b">Severity:</span> ${severity}
  `);

  setTimeout(() => { state.map.removeLayer(ring); state.map.removeLayer(dot); }, 180000);
}

// ── Charts ────────────────────────────────────────────────────────────────────
function initCharts() {
  const gridColor  = 'rgba(255,255,255,0.04)';
  const tickColor  = '#475569';
  const monoFont   = { family: 'JetBrains Mono', size: 10 };

  // Timeline
  const tlCtx = document.getElementById('timeline-chart').getContext('2d');
  const gradient = tlCtx.createLinearGradient(0, 0, 0, 200);
  gradient.addColorStop(0, 'rgba(0,212,255,0.2)');
  gradient.addColorStop(1, 'rgba(0,212,255,0)');

  state.timelineChart = new Chart(tlCtx, {
    type: 'line',
    data: {
      labels: Array.from({ length: 60 }, (_, i) => i % 10 === 0 ? `-${59-i}m` : ''),
      datasets: [{
        label: 'Events/min',
        data: state.timelineBuckets,
        borderColor: '#00d4ff',
        backgroundColor: gradient,
        fill: true, tension: 0.4, pointRadius: 0,
        borderWidth: 1.5,
      }],
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: true,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0d1123',
          borderColor: '#1e2540',
          borderWidth: 1,
          titleColor: '#00d4ff',
          bodyColor: '#e2e8f0',
          titleFont: monoFont,
          bodyFont: monoFont,
        },
      },
      scales: {
        x: { ticks: { color: tickColor, font: monoFont }, grid: { color: gridColor } },
        y: { ticks: { color: tickColor, font: monoFont }, grid: { color: gridColor }, beginAtZero: true },
      },
    },
  });

  // Doughnut
  const bdCtx = document.getElementById('breakdown-chart').getContext('2d');
  state.breakdownChart = new Chart(bdCtx, {
    type: 'doughnut',
    data: {
      labels: ['port_scan','brute_force','malware_upload','command_injection','lateral_movement','other'],
      datasets: [{
        data: [38, 29, 14, 10, 6, 3],
        backgroundColor: ['#00d4ff','#8b5cf6','#ef4444','#f59e0b','#10b981','#334155'],
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      cutout: '68%',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#64748b', font: { ...monoFont, size: 9 }, padding: 12, boxWidth: 8 },
        },
        tooltip: {
          backgroundColor: '#0d1123', borderColor: '#1e2540', borderWidth: 1,
          titleColor: '#00d4ff', bodyColor: '#e2e8f0',
          titleFont: monoFont, bodyFont: monoFont,
        },
      },
    },
  });
  document.getElementById('breakdown-total').textContent = '100';
}

function pushTimelineEvent() {
  state.totalEvents++;
  const buckets = state.timelineBuckets;
  buckets[buckets.length - 1]++;
  if (state.timelineChart) state.timelineChart.update('none');
}

function updateBreakdown(stats) {
  if (!state.breakdownChart || !stats || !stats.length) return;
  state.breakdownChart.data.labels   = stats.map(s => s._id || 'unknown');
  state.breakdownChart.data.datasets[0].data = stats.map(s => s.count);
  state.breakdownChart.update();
  const total = stats.reduce((a, b) => a + b.count, 0);
  document.getElementById('breakdown-total').textContent = total.toLocaleString();
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function initWebSocket() {
  state.socket = io(window.location.origin, { transports: ['websocket', 'polling'] });
  state.socket.on('connect',    () => { setWsStatus(true);  state.socket.emit('subscribe_events'); });
  state.socket.on('disconnect', () => setWsStatus(false));
  state.socket.on('new_event',  event => { addFeedItem(event); pushTimelineEvent(); if (event.latitude && event.longitude) addMapMarker(event.latitude, event.longitude, event.src_ip, event.severity); });
  state.socket.on('profile_update', () => fetchAttackers());
}

function setWsStatus(connected) {
  document.getElementById('ws-status-dot').className = 'status-dot' + (connected ? ' connected' : '');
  document.getElementById('ws-status-text').textContent = connected ? 'Live' : 'Reconnecting';
}

// ── Feed ──────────────────────────────────────────────────────────────────────
function initControls() {
  document.getElementById('filter-type').addEventListener('change', applyFeedFilter);
  document.getElementById('filter-severity').addEventListener('change', applyFeedFilter);
  document.getElementById('btn-clear-feed').addEventListener('click', () => {
    state.feedItems = [];
    const list = document.getElementById('feed-list');
    list.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-radar" style="font-size:28px;color:var(--border);display:block;margin-bottom:8px"></i>Feed cleared</div>';
  });
}

function addFeedItem(event) {
  const filterType = document.getElementById('filter-type').value;
  const filterSev  = document.getElementById('filter-severity').value;

  state.feedItems.unshift(event);
  if (state.feedItems.length > 500) state.feedItems.pop();

  if (filterType && event.attack_type !== filterType) return;
  if (filterSev  && event.severity !== filterSev)     return;

  const list = document.getElementById('feed-list');
  // Remove empty placeholder
  const empty = list.querySelector('.feed-empty');
  if (empty) empty.remove();

  const item = document.createElement('div');
  item.className = `feed-item ${event.severity}`;
  item.dataset.type     = event.attack_type;
  item.dataset.severity = event.severity;

  const ts   = event.timestamp ? new Date(event.timestamp * 1000).toISOString().slice(11, 19) : '—';
  const icon = ATTACK_ICONS[event.attack_type] || ATTACK_ICONS.unknown;
  const sev  = event.severity || 'low';

  item.innerHTML = `
    <span class="feed-time">${ts}</span>
    <span class="feed-sev ${sev}">${sev.toUpperCase()}</span>
    <i class="fa-solid ${icon}" style="color:var(--text-dim);font-size:10px"></i>
    <span class="feed-ip">${event.src_ip}</span>
    <span style="color:var(--text-muted)">&#x2192;</span>
    <span class="feed-type">${(event.attack_type || '').replace(/_/g,' ')}</span>
    <span style="color:var(--text-muted)">:${event.dst_port}</span>
    <span class="feed-src">[${event.honeypot_source || '?'}]</span>
  `;
  item.addEventListener('click', () => openModal(event.src_ip));

  list.insertBefore(item, list.firstChild);
  while (list.children.length > 200) list.removeChild(list.lastChild);
}

function applyFeedFilter() {
  const filterType = document.getElementById('filter-type').value;
  const filterSev  = document.getElementById('filter-severity').value;
  document.getElementById('feed-list').innerHTML = '';
  state.feedItems
    .filter(e => (!filterType || e.attack_type === filterType) && (!filterSev || e.severity === filterSev))
    .slice(0, 200)
    .forEach(addFeedItem);
}

// ── API ───────────────────────────────────────────────────────────────────────
async function fetchAll() {
  await Promise.allSettled([fetchStats(), fetchAttackers(), fetchEnvironments()]);
}

async function fetchStats() {
  try {
    const data = await (await fetch('/api/events/stats')).json();
    if (data.total_events != null) {
      document.getElementById('kpi-events').textContent   = fmtNum(data.total_events);
      document.getElementById('kpi-sessions').textContent = fmtNum(data.active_sessions);
      document.getElementById('kpi-blocked').textContent  = fmtNum(data.blocked_ips);
      updateBreakdown(data.by_attack_type);
      // Threat level
      const lvl = data.blocked_ips > 5 || data.active_sessions > 10 ? 'CRITICAL' :
                  data.active_sessions > 3 ? 'HIGH' : data.total_events > 0 ? 'MEDIUM' : 'LOW';
      const lvlColors = { CRITICAL:'#ef4444', HIGH:'#f59e0b', MEDIUM:'#8b5cf6', LOW:'#10b981' };
      const tlEl = document.getElementById('kpi-threat-level');
      tlEl.textContent = lvl;
      tlEl.style.color = lvlColors[lvl];
    }
  } catch (_) {}
}

async function fetchAttackers() {
  try {
    const data = await (await fetch('/api/attackers?limit=10')).json();
    if ((data.attackers || []).length) renderAttackersTable(data.attackers);
  } catch (_) {}
}

async function fetchEnvironments() {
  try {
    const data = await (await fetch('/api/environments')).json();
    const envs = data.environments || [];
    document.getElementById('kpi-envs').textContent = fmtNum(envs.length);
    renderEnvCards(envs);
  } catch (_) {}
}

// ── Attackers Table ───────────────────────────────────────────────────────────
function renderAttackersTable(attackers) {
  const tbody = document.getElementById('attackers-tbody');
  tbody.innerHTML = '';
  document.getElementById('attacker-count').textContent = `${attackers.length} tracked`;

  attackers.forEach(a => {
    const score      = a.threat_score || 0;
    const scoreClass = score >= 90 ? 'critical' : score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
    const tier       = (a.attacker_tier || 'beginner').replace(' ', '_');
    const barWidth   = Math.min(score, 100).toFixed(0);
    const barColor   = score >= 90 ? '#ef4444' : score >= 70 ? '#f59e0b' : score >= 40 ? '#8b5cf6' : '#475569';
    const lastSeen   = a.last_seen ? timeSince(a.last_seen) : '—';

    const tr = document.createElement('tr');
    tr.onclick = () => openModal(a.src_ip);
    tr.innerHTML = `
      <td>
        <span style="color:var(--accent);font-weight:700">${a.src_ip}</span>
      </td>
      <td>
        <div class="score-bar-wrap">
          <span class="score-pill ${scoreClass}">${score.toFixed(0)}</span>
          <div class="score-bar">
            <div class="score-bar-fill" style="width:${barWidth}%;background:${barColor}"></div>
          </div>
        </div>
      </td>
      <td style="color:var(--text)">${(a.classified_intent||'—').replace(/_/g,' ')}</td>
      <td><span class="tier-cell-badge ${tier}">${(a.attacker_tier||'—').replace(/_/g,' ')}</span></td>
      <td><span style="color:var(--accent2);font-weight:600">${(a.ttps||[]).length}</span></td>
      <td style="color:var(--text-dim)">${lastSeen}</td>
      <td><button class="btn-link" onclick="event.stopPropagation();openModal('${a.src_ip}')">
        <i class="fa-solid fa-arrow-up-right-from-square" style="font-size:9px;margin-right:3px"></i>Profile
      </button></td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Env Cards ─────────────────────────────────────────────────────────────────
function renderEnvCards(envs) {
  const container = document.getElementById('env-cards');
  container.innerHTML = '';
  if (!envs.length) {
    container.innerHTML = `<div class="feed-empty" style="padding:20px 0">
      <i class="fa-solid fa-server" style="font-size:22px;color:var(--border);display:block;margin-bottom:6px"></i>
      No active environments
    </div>`;
    return;
  }
  envs.forEach(e => {
    const age = Math.floor((Date.now()/1000 - e.created_at) / 60);
    const card = document.createElement('div');
    card.className = 'env-card';
    card.innerHTML = `
      <div class="env-card-header">
        <span class="env-card-ip">${e.src_ip}</span>
        <span class="env-tier-badge">${(e.attacker_tier||'').replace(/_/g,' ')}</span>
      </div>
      <div class="env-card-host"><i class="fa-solid fa-server" style="margin-right:5px;color:var(--text-muted)"></i>${e.hostname||'—'}</div>
      <div class="env-services">
        ${(e.services||[]).map(s => `<span class="env-svc-tag">${s}</span>`).join('')}
      </div>
      <div class="env-footer">
        <i class="fa-regular fa-clock" style="margin-right:3px"></i>${age}m active
        &nbsp;·&nbsp;
        <i class="fa-solid fa-bolt" style="margin-right:3px"></i>${(e.engagement_log||[]).length} interactions
      </div>
    `;
    container.appendChild(card);
  });
}

// ── Modal ─────────────────────────────────────────────────────────────────────
async function openModal(ip) {
  state.selectedIP = ip;
  document.getElementById('modal-ip').textContent = ip;
  document.getElementById('modal-intent').textContent   = '…';
  document.getElementById('modal-tier').textContent     = '…';
  document.getElementById('modal-sessions').textContent = '…';
  document.getElementById('modal-first').textContent    = '…';
  document.getElementById('modal-last').textContent     = '…';
  document.getElementById('gauge-value').textContent    = '…';
  document.getElementById('modal-ttps').innerHTML       = '<span class="ttp-empty">Loading…</span>';
  document.getElementById('profile-modal').classList.remove('hidden');

  try {
    const res = await fetch(`/api/attackers/${ip}`);
    if (!res.ok) throw new Error(res.status);
    const p = await res.json();

    document.getElementById('modal-intent').textContent   = (p.classified_intent || '—').replace(/_/g,' ');
    document.getElementById('modal-tier').textContent     = (p.attacker_tier || '—').replace(/_/g,' ');
    document.getElementById('modal-sessions').textContent = `${p.session_count||0} sessions · ${p.total_commands||0} commands`;
    document.getElementById('modal-first').textContent    = fmtTime(p.first_seen);
    document.getElementById('modal-last').textContent     = fmtTime(p.last_seen);
    document.getElementById('gauge-value').textContent    = (p.threat_score||0).toFixed(0);

    const ttpGrid = document.getElementById('modal-ttps');
    ttpGrid.innerHTML = '';
    const ttps = p.ttps || [];
    if (!ttps.length) {
      ttpGrid.innerHTML = '<span class="ttp-empty">No TTPs detected</span>';
    } else {
      ttps.slice(0, 16).forEach(t => {
        const chip = document.createElement('div');
        chip.className = 'ttp-chip';
        chip.title = `${t.technique_name} · ${t.tactic} (confidence: ${((t.confidence||0)*100).toFixed(0)}%)`;
        chip.textContent = t.technique_id;
        ttpGrid.appendChild(chip);
      });
    }

    drawGauge(p.threat_score || 0);
  } catch (e) {
    // Show demo data if no DB
    document.getElementById('modal-intent').textContent   = 'malware_deployment'.replace(/_/g,' ');
    document.getElementById('modal-tier').textContent     = 'advanced human';
    document.getElementById('modal-sessions').textContent = '3 sessions · 24 commands';
    document.getElementById('modal-first').textContent    = '2026-06-04 23:00:00';
    document.getElementById('modal-last').textContent     = '2026-06-04 23:15:00';
    document.getElementById('gauge-value').textContent    = '94';
    drawGauge(94);
    document.getElementById('modal-ttps').innerHTML = ['T1105','T1003.008','T1053.003','T1021.004','T1496','T1033']
      .map(id => `<div class="ttp-chip">${id}</div>`).join('');
  }
}

function handleModalBackdrop(event) {
  if (event.target === document.getElementById('profile-modal')) closeModal();
}

function closeModal() {
  document.getElementById('profile-modal').classList.add('hidden');
  state.selectedIP = null;
}

function drawGauge(score) {
  const canvas = document.getElementById('threat-gauge');
  const ctx    = canvas.getContext('2d');
  const dpr    = window.devicePixelRatio || 1;
  canvas.width  = 200 * dpr;
  canvas.height = 110 * dpr;
  canvas.style.width  = '200px';
  canvas.style.height = '110px';
  ctx.scale(dpr, dpr);

  const cx = 100, cy = 100, r = 75;
  const startA = Math.PI, endA = 2 * Math.PI;
  const scoreA = startA + (score / 100) * Math.PI;

  // Track
  ctx.beginPath();
  ctx.arc(cx, cy, r, startA, endA);
  ctx.lineWidth = 14;
  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineCap = 'round';
  ctx.stroke();

  if (score > 0) {
    const color = score >= 90 ? '#ef4444' : score >= 70 ? '#f59e0b' : score >= 40 ? '#8b5cf6' : '#10b981';
    const glow  = score >= 90 ? 'rgba(239,68,68,0.4)' : score >= 70 ? 'rgba(245,158,11,0.4)' : score >= 40 ? 'rgba(139,92,246,0.4)' : 'rgba(16,185,129,0.4)';

    ctx.shadowBlur = 12;
    ctx.shadowColor = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, r, startA, scoreA);
    ctx.lineWidth = 14;
    ctx.strokeStyle = color;
    ctx.lineCap = 'round';
    ctx.stroke();
    ctx.shadowBlur = 0;

    // Tick marks
    for (let i = 0; i <= 10; i++) {
      const a = startA + (i / 10) * Math.PI;
      const x1 = cx + (r - 18) * Math.cos(a), y1 = cy + (r - 18) * Math.sin(a);
      const x2 = cx + (r - 22) * Math.cos(a), y2 = cy + (r - 22) * Math.sin(a);
      ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(x2,y2);
      ctx.strokeStyle = 'rgba(255,255,255,0.15)'; ctx.lineWidth = 1; ctx.stroke();
    }
  }
}

async function blockIP() {
  if (!state.selectedIP) return;
  if (!confirm(`Block ${state.selectedIP}?\nThis will add an iptables DROP rule.`)) return;
  try {
    const res = await fetch('/api/response/block', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ src_ip: state.selectedIP }),
    });
    const data = await res.json();
    closeModal();
    fetchStats();
  } catch (_) {}
}

// ── Tab System ────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const tab = btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Show/hide main grid vs tab content
    const mainGrid = document.querySelector('.main-grid');
    document.querySelectorAll('.tab-content').forEach(tc => tc.classList.add('hidden'));

    if (tab === 'operations') {
      mainGrid.classList.remove('hidden');
    } else {
      mainGrid.classList.add('hidden');
      const tc = document.getElementById(`tab-${tab}`);
      if (tc) {
        tc.classList.remove('hidden');
        loadTab(tab);
      }
    }
  });
});

function loadTab(tab) {
  if (tab === 'cbee')   loadCBEE();
  if (tab === 'gadcf')  loadGADCF();
  if (tab === 'fhim')   loadFHIM();
}

// ── CBEE ──────────────────────────────────────────────────────────────────────
async function loadCBEE() {
  await refreshCBEE();
}

async function refreshCBEE() {
  try {
    const [profRes, injRes] = await Promise.all([
      fetch('/api/cbee/profiles'),
      fetch('/api/cbee/injections'),
    ]);
    const profData = await profRes.json();
    const injData  = await injRes.json();
    renderCBEEProfiles(profData.profiles || []);
    renderCBEEInjections(injData.injections || []);
  } catch (e) { console.error(e); }
}

function renderCBEEProfiles(profiles) {
  const el = document.getElementById('cbee-profiles-list');
  if (!el) return;
  el.innerHTML = '';

  const biasColors = {
    curiosity_gap:    '#f59e0b',
    confirmation_bias:'#8b5cf6',
    sunk_cost:        '#10b981',
    authority_signal: '#00d4ff',
    scarcity_framing: '#ef4444',
  };
  const biasLabels = {
    curiosity_gap:    'Curiosity Gap',
    confirmation_bias:'Confirmation Bias',
    sunk_cost:        'Sunk Cost Trap',
    authority_signal: 'Authority Signals',
    scarcity_framing: 'Scarcity Framing',
  };

  if (!profiles.length) {
    el.innerHTML = '<div class="feed-empty">No active bias profiles</div>'; return;
  }

  profiles.forEach(p => {
    const card = document.createElement('div');
    card.className = 'cbee-profile-card';
    const bars = Object.keys(biasLabels).map(key => {
      const val = Math.round(p[key] || 0);
      const color = biasColors[key];
      return `<div class="cbee-bar-row">
        <div class="cbee-bar-label">${biasLabels[key]}</div>
        <div class="cbee-bar-track"><div class="cbee-bar-fill" style="width:${val}%;background:${color}"></div></div>
        <div class="cbee-bar-val">${val}</div>
      </div>`;
    }).join('');
    const dominantLabel = biasLabels[p.dominant] || p.dominant;
    card.innerHTML = `
      <div class="cbee-profile-header">
        <span class="cbee-ip">${p.src_ip}</span>
        <span class="cbee-dominant">${dominantLabel}</span>
      </div>
      <div class="cbee-bars">${bars}</div>
      <div style="margin-top:8px;font-size:10px;color:var(--text-dim);font-family:var(--font-mono)">
        Overall score: <b style="color:#f59e0b">${(p.overall||0).toFixed(1)}</b>
      </div>
    `;
    el.appendChild(card);
  });
}

function renderCBEEInjections(injections) {
  const el = document.getElementById('cbee-injections-list');
  if (!el) return;
  el.innerHTML = '';

  if (!injections.length) {
    el.innerHTML = '<div class="feed-empty">No bait injections yet</div>'; return;
  }

  injections.forEach(inj => {
    const card = document.createElement('div');
    card.className = 'cbee-injection-card';
    const ts = inj.created_at ? timeSince(inj.created_at) : '—';
    const assetCount = (inj.assets || []).length;
    const biasColor = { authority_signal:'#00d4ff', curiosity_gap:'#f59e0b', sunk_cost:'#10b981', confirmation_bias:'#8b5cf6', scarcity_framing:'#ef4444' }[inj.bias_trigger] || '#64748b';
    card.innerHTML = `
      <div class="cbee-injection-header">
        <i class="fa-solid fa-syringe" style="color:${biasColor}"></i>
        <span style="color:var(--accent)">${inj.src_ip}</span>
        <span style="color:${biasColor};font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:1px">${(inj.bias_trigger||'').replace(/_/g,' ')}</span>
        <span style="margin-left:auto;color:var(--text-muted)">${ts}</span>
      </div>
      <div style="color:var(--text-dim)">
        Score: <b style="color:#f59e0b">${(inj.bias_score||0).toFixed(1)}</b>
        · Assets injected: <b style="color:var(--text)">${assetCount}</b>
        · <span style="color:${inj.executed?'#10b981':'#64748b'}">${inj.executed?'Executed':'Pending'}</span>
      </div>
    `;
    el.appendChild(card);
  });
}

// ── GADCF ─────────────────────────────────────────────────────────────────────
let _gadcfAssets = [];

async function loadGADCF() {
  try {
    const res  = await fetch('/api/gadcf/assets');
    const data = await res.json();
    _gadcfAssets = data.assets || [];
    renderGADCFAssets(_gadcfAssets);
  } catch (e) {}
}

async function gadcfGenerate() {
  const btn = document.querySelector('.gadcf-generate-btn');
  const status = document.getElementById('gadcf-status');
  btn.disabled = true;
  status.textContent = '⚡ Generating assets…';

  try {
    const res = await fetch('/api/gadcf/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        industry:      document.getElementById('gadcf-industry').value,
        intent:        document.getElementById('gadcf-intent').value,
        sophistication:document.getElementById('gadcf-sophistication').value,
      }),
    });
    const data = await res.json();
    _gadcfAssets = [...(data.assets || []), ..._gadcfAssets];
    renderGADCFAssets(_gadcfAssets);
    status.textContent = `✓ Generated ${data.count} assets (source: ${data.assets?.[0]?.source || 'template'})`;
    status.style.color = '#10b981';
  } catch (e) {
    status.textContent = '✗ Generation failed';
    status.style.color = '#ef4444';
  }
  btn.disabled = false;
}

const ASSET_ICONS = {
  env_file:    { icon: 'fa-file-shield',   color: '#ef4444', bg: 'rgba(239,68,68,0.1)' },
  email_thread:{ icon: 'fa-envelope',      color: '#f59e0b', bg: 'rgba(245,158,11,0.1)' },
  code_repo:   { icon: 'fa-code',          color: '#00d4ff', bg: 'rgba(0,212,255,0.1)' },
  wiki_page:   { icon: 'fa-book',          color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)' },
  db_schema:   { icon: 'fa-database',      color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
};

function renderGADCFAssets(assets) {
  const el = document.getElementById('gadcf-assets-list');
  if (!el) return;
  el.innerHTML = '';
  if (!assets.length) { el.innerHTML = '<div class="feed-empty">No assets generated yet</div>'; return; }

  assets.slice(0, 20).forEach((a, i) => {
    const meta = ASSET_ICONS[a.asset_type] || { icon:'fa-file', color:'#64748b', bg:'rgba(100,116,139,0.1)' };
    const isLLM = a.source === 'llm';
    const item = document.createElement('div');
    item.className = 'gadcf-asset-item';
    item.onclick = () => previewAsset(a, item);
    item.innerHTML = `
      <div class="gadcf-asset-icon" style="background:${meta.bg};color:${meta.color}"><i class="fa-solid ${meta.icon}"></i></div>
      <div style="flex:1;min-width:0">
        <div class="gadcf-asset-name">${a.filename || a.asset_type}</div>
        <div class="gadcf-asset-meta">${a.industry?.replace(/_/g,' ')} · ${a.attacker_intent?.replace(/_/g,' ')}</div>
      </div>
      <span class="gadcf-source-tag" style="background:${isLLM?'rgba(0,212,255,0.15)':'rgba(100,116,139,0.15)'};color:${isLLM?'#00d4ff':'#64748b'}">${isLLM?'LLM':'TMPL'}</span>
    `;
    el.appendChild(item);
  });
}

function previewAsset(asset, el) {
  document.querySelectorAll('.gadcf-asset-item').forEach(i => i.classList.remove('selected'));
  el.classList.add('selected');
  document.getElementById('gadcf-preview-name').textContent = asset.filename || '';
  const preview = document.getElementById('gadcf-preview');
  preview.textContent = asset.content || '(no content)';
  preview.style.color = '#e2e8f0';
}

// ── FHIM ──────────────────────────────────────────────────────────────────────
async function loadFHIM() {
  try {
    const res  = await fetch('/api/fhim/nodes');
    const data = await res.json();
    const nodes = data.nodes || [];
    document.getElementById('fhim-global-f1').textContent   = ((data.global_f1||0)*100).toFixed(1) + '%';
    document.getElementById('fhim-node-count').textContent  = nodes.length;
    document.getElementById('fhim-total-samples').textContent = fmtNum(nodes.reduce((a,n)=>a+(n.samples_contributed||0),0));
    renderFHIMNodes(nodes);
  } catch (e) {}
}

function renderFHIMNodes(nodes) {
  const el = document.getElementById('fhim-nodes-list');
  if (!el) return;
  el.innerHTML = '';
  if (!nodes.length) { el.innerHTML = '<div class="feed-empty">No nodes registered</div>'; return; }

  const flagMap = { EG:'🇪🇬', US:'🇺🇸', DE:'🇩🇪', SA:'🇸🇦', GB:'🇬🇧', FR:'🇫🇷', CN:'🇨🇳' };

  nodes.forEach(n => {
    const card = document.createElement('div');
    card.className = 'fhim-node-card';
    const flag = flagMap[n.location] || '🌐';
    const lastRound = n.last_round ? timeSince(n.last_round) : 'never';
    const f1Pct = ((n.f1_score||0)*100).toFixed(1);
    card.innerHTML = `
      <div class="fhim-node-header">
        <span style="font-size:18px">${flag}</span>
        <div>
          <div class="fhim-node-org">${n.org_name}</div>
          <div class="fhim-node-id">${n.node_id}</div>
        </div>
        <span class="fhim-node-status ${n.status}">${n.status}</span>
      </div>
      <div class="fhim-node-stats">
        <span>F1: <span class="fhim-node-f1">${f1Pct}%</span></span>
        <span>Rounds: <b>${n.rounds_total||0}</b></span>
        <span>Samples: <b>${fmtNum(n.samples_contributed)}</b></span>
        <span>Last: ${lastRound}</span>
      </div>
    `;
    el.appendChild(card);
  });
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function fmtNum(n) { return n == null ? '—' : Number(n).toLocaleString(); }
function fmtTime(ts) { return ts ? new Date(ts * 1000).toLocaleString() : '—'; }
function timeSince(ts) {
  const s = Math.floor(Date.now()/1000 - ts);
  if (s < 60)   return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  return `${Math.floor(s/3600)}h ago`;
}
