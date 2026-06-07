'use strict';

/* ════════════════════════════════════════════════════════════
   NeuroTrap CADN — Single-Page App Controller
════════════════════════════════════════════════════════════ */

/* ── Auth helpers ─────────────────────────────────────────── */

function _jwtPayload(token) {
  try { return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))); }
  catch { return {}; }
}

const AUTH = {
  token: sessionStorage.getItem('nt_token') || '',
  mfaRequired: false,
  pendingUser: '',
  pendingPass: '',

  header() {
    return this.token ? { 'Authorization': 'Bearer ' + this.token } : {};
  },

  save(token) {
    this.token = token;
    sessionStorage.setItem('nt_token', token);
  },

  clear() {
    this.token = '';
    sessionStorage.removeItem('nt_token');
  },

  isAuthenticated() {
    return !!this.token;
  },

  role() {
    return _jwtPayload(this.token).role || 'analyst';
  },

  isAdmin() {
    return this.role() === 'admin';
  },
};

function showLoginError(msg) {
  const el = document.getElementById('login-error');
  el.textContent = msg;
  el.style.display = 'block';
}

function hideLoginError() {
  const el = document.getElementById('login-error');
  if (el) el.style.display = 'none';
}

function setLoginBusy(busy) {
  const btn = document.getElementById('login-btn');
  const otpBtn = document.getElementById('otp-btn');
  if (btn) btn.disabled = busy;
  if (otpBtn) otpBtn.disabled = busy;
}

function applyRoleUI() {
  const isAdmin = AUTH.isAdmin();
  document.querySelectorAll('.admin-only').forEach(el => {
    el.style.display = isAdmin ? '' : 'none';
  });
}

function showDashboard() {
  const overlay = document.getElementById('login-overlay');
  if (overlay) overlay.style.display = 'none';
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.style.display = '';
  applyRoleUI();
}

function showLoginOverlay() {
  const overlay = document.getElementById('login-overlay');
  if (overlay) overlay.style.display = 'flex';
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) logoutBtn.style.display = 'none';
}

function resetLoginStep() {
  document.getElementById('login-step-password').style.display = '';
  document.getElementById('login-step-otp').style.display = 'none';
  document.getElementById('login-otp').value = '';
  hideLoginError();
}

async function doLogin() {
  hideLoginError();
  const user = (document.getElementById('login-user').value || '').trim();
  const pass = document.getElementById('login-pass').value || '';
  if (!user || !pass) { showLoginError('Please enter username and password.'); return; }

  setLoginBusy(true);
  try {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: pass }),
    });
    const d = await r.json();

    if (r.status === 401 && d.mfa_required) {
      AUTH.pendingUser = user;
      AUTH.pendingPass = pass;
      document.getElementById('login-step-password').style.display = 'none';
      document.getElementById('login-step-otp').style.display = '';
      document.getElementById('login-otp').focus();
      return;
    }

    if (!r.ok) { showLoginError(d.error || 'Login failed.'); return; }

    AUTH.save(d.access_token);
    AUTH.mfaRequired = !!d.mfa_enabled;
    showDashboard();
    initApp();
  } catch(e) {
    showLoginError('Network error — please retry.');
  } finally {
    setLoginBusy(false);
  }
}

async function doLoginOTP() {
  hideLoginError();
  const code = (document.getElementById('login-otp').value || '').trim();
  if (code.length !== 6) { showLoginError('Enter a valid 6-digit code.'); return; }

  setLoginBusy(true);
  try {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: AUTH.pendingUser, password: AUTH.pendingPass, otp: code }),
    });
    const d = await r.json();

    if (!r.ok) { showLoginError(d.error || 'Invalid OTP code.'); return; }

    AUTH.save(d.access_token);
    showDashboard();
    initApp();
  } catch(e) {
    showLoginError('Network error — please retry.');
  } finally {
    setLoginBusy(false);
  }
}

function doLogout() {
  AUTH.clear();
  resetLoginStep();
  showLoginOverlay();
}

const state = {
  socket: null,
  map: null,
  timelineChart: null,
  breakdownChart: null,
  feedItems: [],
  feedPage: 0,
  eventsFeedPage: 0,
  timelineBuckets: new Array(60).fill(0),
  selectedIP: null,
  loaded: { intel:false, cbee:false, gadcf:false, fhim:false, ashrta:false, twin:false, soc:false, attackers:false, responses:false },
  twins: [], selectedTwin: null,
};

const BREADCRUMBS = {
  dashboard:'Dashboard <span>/</span> Operations',
  attackers:'Threat Actors <span>/</span> Operations',
  events:'Live Events <span>/</span> Operations',
  environments:'Honeypots <span>/</span> Operations',
  responses:'Response Log <span>/</span> Operations',
  intel:'Threat Intelligence <span>/</span> Intelligence',
  cbee:'CBEE <span>/</span> Innovations',
  gadcf:'GADCF <span>/</span> Innovations',
  fhim:'FHIM <span>/</span> Innovations',
  ashrta:'ASHRTA <span>/</span> Innovations',
  twin:'Attacker Digital Twin <span>/</span> Innovations',
  soc:'AI SOC Analyst <span>/</span> Innovations',
};

const ATTACK_ICONS = {
  port_scan:'fa-magnifying-glass', brute_force:'fa-key', malware_upload:'fa-virus',
  command_injection:'fa-terminal', lateral_movement:'fa-arrows-left-right',
  protocol_anomaly:'fa-triangle-exclamation', data_exfiltration:'fa-file-export',
  tool_fingerprint:'fa-fingerprint', unknown:'fa-question',
};

/* ── Init ── */

function initApp() {
  initMap();
  initCharts();
  initWebSocket();
  fetchDashboard();
  setInterval(fetchDashboard, 15000);
  setTimeout(injectDemo, 1000);
}

document.addEventListener('DOMContentLoaded', async () => {
  initClock();

  // Check whether the server requires MFA before deciding how to pre-fill the UI.
  try {
    const s = await fetch('/api/auth/mfa/status');
    const d = await s.json();
    AUTH.mfaRequired = !!d.mfa_enabled;
  } catch(_) {}

  if (AUTH.isAuthenticated()) {
    showDashboard();
    initApp();
  } else {
    showLoginOverlay();
  }
});

/* ════════════════════════════════════════
   NAVIGATION (in-page, no new tabs)
════════════════════════════════════════ */
function navigate(section, el) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  const sec = document.getElementById('sec-' + section);
  if (sec) sec.classList.add('active');
  document.getElementById('breadcrumb').innerHTML = BREADCRUMBS[section] || section;
  window.scrollTo(0, 0);
  // close mobile sidebar
  document.getElementById('sidebar').classList.remove('open');

  // Lazy-load section data
  if (section === 'intel') {
    if (!state.loaded.intel) { loadIntel(); state.loaded.intel = true; }
    // Leaflet needs invalidateSize when container goes from hidden to visible
    setTimeout(() => { if (state.map) state.map.invalidateSize(); }, 50);
  }
  if (section === 'cbee'  && !state.loaded.cbee)  { loadCBEE();  state.loaded.cbee = true; }
  if (section === 'gadcf' && !state.loaded.gadcf) { initGADCF(); loadGADCF(); state.loaded.gadcf = true; }
  if (section === 'fhim'  && !state.loaded.fhim)  { loadFHIM();  state.loaded.fhim = true; }
  if (section === 'ashrta'&& !state.loaded.ashrta){ loadASHRTA();state.loaded.ashrta = true; }
  if (section === 'twin'  && !state.loaded.twin)  { loadTwin();  state.loaded.twin = true; }
  if (section === 'soc'   && !state.loaded.soc)   { loadSOC();   state.loaded.soc = true; }
  if (section === 'attackers') loadFullAttackers();
  if (section === 'events') renderEventsPage();
  if (section === 'environments') loadFullEnvs();
  if (section === 'responses') loadResponses();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

/* ════════════════════════════════════════
   CLOCK
════════════════════════════════════════ */
function initClock() {
  const el = document.getElementById('clock');
  const tick = () => el.textContent = new Date().toUTCString().replace('GMT', 'UTC');
  tick(); setInterval(tick, 1000);
}

/* ════════════════════════════════════════
   MAP
════════════════════════════════════════ */
function initMap() {
  state.map = L.map('attack-map', { zoomControl:true, scrollWheelZoom:false, attributionControl:false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { maxZoom:18 }).addTo(state.map);
  state.map.setView([25, 10], 2);
}
function addMarker(lat, lon, ip, sev) {
  if (!state.map || !lat || !lon) return;
  const colors = { critical:'#f43f5e', high:'#f59e0b', medium:'#a855f7', low:'#475569' };
  const c = colors[sev] || colors.low;
  const r = sev==='critical'?9:sev==='high'?7:5;
  const ring = L.circleMarker([lat,lon],{radius:r+5,color:c,fillColor:'transparent',weight:1.5,opacity:0.4}).addTo(state.map);
  const dot  = L.circleMarker([lat,lon],{radius:r,color:c,fillColor:c,fillOpacity:0.7,weight:1}).addTo(state.map);
  dot.bindPopup(`<b style="color:${c}">${ip}</b><br/><span style="color:#64748b">Severity:</span> ${sev}`);
  setTimeout(()=>{state.map.removeLayer(ring);state.map.removeLayer(dot);},180000);
}

/* ════════════════════════════════════════
   CHARTS
════════════════════════════════════════ */
function initCharts() {
  const mono = { family:'JetBrains Mono', size:10 };
  const tl = document.getElementById('timeline-chart').getContext('2d');
  const grad = tl.createLinearGradient(0,0,0,180);
  grad.addColorStop(0,'rgba(99,102,241,0.25)'); grad.addColorStop(1,'rgba(99,102,241,0)');
  state.timelineChart = new Chart(tl, {
    type:'line',
    data:{ labels:Array.from({length:60},(_,i)=>i%10===0?`-${59-i}m`:''),
      datasets:[{ data:state.timelineBuckets, borderColor:'#6366f1', backgroundColor:grad, fill:true, tension:0.4, pointRadius:0, borderWidth:1.5 }] },
    options:{ animation:false, responsive:true, maintainAspectRatio:true,
      plugins:{ legend:{display:false}, tooltip:{backgroundColor:'#0f1629',borderColor:'#1d2a45',borderWidth:1,titleColor:'#6366f1',bodyColor:'#cbd5e1',titleFont:mono,bodyFont:mono} },
      scales:{ x:{ticks:{color:'#475569',font:mono},grid:{color:'rgba(255,255,255,0.04)'}}, y:{ticks:{color:'#475569',font:mono},grid:{color:'rgba(255,255,255,0.04)'},beginAtZero:true} } },
  });
  const bd = document.getElementById('breakdown-chart').getContext('2d');
  state.breakdownChart = new Chart(bd, {
    type:'doughnut',
    data:{ labels:['port_scan','brute_force','malware','cmd_exec','lateral','other'],
      datasets:[{ data:[38,29,14,10,6,3], backgroundColor:['#22d3ee','#6366f1','#f43f5e','#f59e0b','#10b981','#334155'], borderWidth:0, hoverOffset:6 }] },
    options:{ cutout:'70%', responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{position:'bottom',labels:{color:'#64748b',font:{...mono,size:9},padding:10,boxWidth:8}},
        tooltip:{backgroundColor:'#0f1629',borderColor:'#1d2a45',borderWidth:1,titleColor:'#22d3ee',bodyColor:'#cbd5e1',titleFont:mono,bodyFont:mono} } },
  });
  document.getElementById('breakdown-total').textContent = '100';
}
function pushTimeline() {
  state.timelineBuckets[state.timelineBuckets.length-1]++;
  if (state.timelineChart) state.timelineChart.update('none');
}
function updateBreakdown(stats) {
  if (!state.breakdownChart || !stats || !stats.length) return;
  state.breakdownChart.data.labels = stats.map(s=>s._id||'unknown');
  state.breakdownChart.data.datasets[0].data = stats.map(s=>s.count);
  state.breakdownChart.update();
  document.getElementById('breakdown-total').textContent = stats.reduce((a,b)=>a+b.count,0).toLocaleString();
}

/* ════════════════════════════════════════
   WEBSOCKET
════════════════════════════════════════ */
function initWebSocket() {
  try {
    state.socket = io(window.location.origin, { transports:['websocket','polling'] });
    state.socket.on('connect', () => { setWs(true); state.socket.emit('subscribe_events'); });
    state.socket.on('disconnect', () => setWs(false));
    state.socket.on('new_event', e => { addFeed(e); pushTimeline(); if(e.latitude&&e.longitude) addMarker(e.latitude,e.longitude,e.src_ip,e.severity); });
    state.socket.on('profile_update', () => fetchDashboard());
  } catch(e) {}
}
function setWs(c) {
  document.getElementById('ws-pill').className = 'ws-pill' + (c?' connected':'');
  document.getElementById('ws-text').textContent = c?'Live':'Offline';
  document.getElementById('ws-sidebar-text').textContent = c?'System Active':'Reconnecting';
}

/* ════════════════════════════════════════
   FEED
════════════════════════════════════════ */
const FEED_PG = 20;
const EVENTS_PG = 50;

function _filteredFeed(typeId, sevId) {
  const ft = document.getElementById(typeId)?.value || '';
  const fs = document.getElementById(sevId)?.value || '';
  return state.feedItems.filter(e => (!ft || e.attack_type === ft) && (!fs || e.severity === fs));
}

function addFeed(e) {
  state.feedItems.unshift(e);
  if (state.feedItems.length > 5000) state.feedItems.pop();
  renderMainFeed();
  if (document.getElementById('sec-events').classList.contains('active')) renderEventsPage();
}

function buildFeedItem(e) {
  const icon = ATTACK_ICONS[e.attack_type] || ATTACK_ICONS.unknown;
  const sev = e.severity || 'low';
  let ts = '—';
  if (e.timestamp) {
    const d = new Date(e.timestamp * 1000);
    const date = d.toISOString().slice(0, 10);
    const time = d.toISOString().slice(11, 19);
    const today = new Date().toISOString().slice(0, 10);
    ts = date === today ? time : `${date} ${time}`;
  }
  const div = document.createElement('div');
  div.className = `feed-item ${sev}`;
  div.innerHTML = `
    <div class="feed-item-row">
      <span class="feed-sev ${sev}">${sev.toUpperCase()}</span>
      <i class="fa-solid ${icon}" style="color:var(--t4);font-size:12px"></i>
      <span class="feed-ip">${e.src_ip}</span>
      <span style="color:var(--t4)">&#8594;</span>
      <span class="feed-type">${(e.attack_type || '').replace(/_/g, ' ')}</span>
      <span style="color:var(--t4)">:${e.dst_port}</span>
      <span class="feed-src">[${e.honeypot_source || '?'}]</span>
    </div>
    <div class="feed-time">
      <i class="fa-regular fa-clock"></i>${ts}
    </div>`;
  div.onclick = () => openModal(e.src_ip);
  return div;
}

function _renderFeed(listId, pagingId, items, page, pageSize, pageFn) {
  const list = document.getElementById(listId);
  const paging = document.getElementById(pagingId);
  if (!items.length) {
    list.innerHTML = '<div class="feed-empty"><i class="fa-solid fa-satellite-dish" style="font-size:24px;color:var(--border2)"></i>No events</div>';
    if (paging) paging.innerHTML = '';
    return;
  }
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  page = Math.max(0, Math.min(page, totalPages - 1));
  const slice = items.slice(page * pageSize, (page + 1) * pageSize);
  list.innerHTML = '';
  slice.forEach(e => list.appendChild(buildFeedItem(e)));
  if (paging) {
    paging.innerHTML = `
      <div class="feed-paging">
        <button class="pg-btn" onclick="${pageFn}(${page - 1})" ${page === 0 ? 'disabled' : ''}>&#8249; Prev</button>
        <span class="pg-info">Page ${page + 1} / ${totalPages} &nbsp;&middot;&nbsp; ${items.length} events</span>
        <button class="pg-btn" onclick="${pageFn}(${page + 1})" ${page >= totalPages - 1 ? 'disabled' : ''}>Next &#8250;</button>
      </div>`;
  }
}

function renderMainFeed() {
  const items = _filteredFeed('filter-type', 'filter-sev');
  _renderFeed('feed-list', 'feed-paging', items, state.feedPage, FEED_PG, 'setFeedPage');
}
function setFeedPage(p) {
  const total = Math.max(1, Math.ceil(_filteredFeed('filter-type', 'filter-sev').length / FEED_PG));
  state.feedPage = Math.max(0, Math.min(p, total - 1));
  renderMainFeed();
}
function applyFilter() { state.feedPage = 0; renderMainFeed(); }
function clearFeed() {
  state.feedItems = []; state.feedPage = 0;
  document.getElementById('feed-list').innerHTML = '<div class="feed-empty"><i class="fa-solid fa-broom" style="font-size:24px;color:var(--border2)"></i>Cleared</div>';
  document.getElementById('feed-paging').innerHTML = '';
}

function renderEventsPage() {
  const items = _filteredFeed('events-filter-type', 'events-filter-sev');
  _renderFeed('events-page-list', 'events-paging', items, state.eventsFeedPage, EVENTS_PG, 'setEvtPage');
}
function setEvtPage(p) {
  const total = Math.max(1, Math.ceil(_filteredFeed('events-filter-type', 'events-filter-sev').length / EVENTS_PG));
  state.eventsFeedPage = Math.max(0, Math.min(p, total - 1));
  renderEventsPage();
}
function applyEventsFilter() { state.eventsFeedPage = 0; renderEventsPage(); }
function clearEventsPage() {
  state.eventsFeedPage = 0;
  document.getElementById('events-page-list').innerHTML = '<div class="feed-empty">Cleared</div>';
  document.getElementById('events-paging').innerHTML = '';
}

/* ════════════════════════════════════════
   DASHBOARD DATA
════════════════════════════════════════ */
async function fetchDashboard() {
  await Promise.allSettled([fetchStats(), fetchAttackers(), fetchEnvs()]);
}
async function fetchStats() {
  try {
    const d = await (await fetch('/api/events/stats')).json();
    if (d.total_events != null) {
      setText('kpi-events', fmtNum(d.total_events));
      setText('kpi-sessions', fmtNum(d.active_sessions));
      setText('kpi-blocked', fmtNum(d.blocked_ips));
      updateBreakdown(d.by_attack_type);
      const lvl = d.blocked_ips>5||d.active_sessions>10?'CRITICAL':d.active_sessions>3?'HIGH':d.total_events>0?'MEDIUM':'LOW';
      const colors = {CRITICAL:'#f43f5e',HIGH:'#f59e0b',MEDIUM:'#a855f7',LOW:'#10b981'};
      const el = document.getElementById('kpi-threat-level'); el.textContent = lvl; el.style.color = colors[lvl];
    }
  } catch(e) {}
}
async function fetchAttackers() {
  try {
    const d = await (await fetch('/api/attackers?limit=10')).json();
    if ((d.attackers||[]).length) renderAttackerTable('attackers-tbody', d.attackers, 'attacker-count');
  } catch(e) {}
}
async function fetchEnvs() {
  try {
    const [ed, hd] = await Promise.all([
      fetch('/api/environments').then(r=>r.json()),
      fetch('/api/honeypots').then(r=>r.json()),
    ]);
    const envs = ed.environments || [];
    const activeSensors = (hd.sensors || []).filter(s => s.status === 'online').length;
    setText('kpi-envs', fmtNum(activeSensors));
    renderEnvCards('env-cards', envs);
  } catch(e) {}
}

function renderAttackerTable(tbodyId, attackers, countId) {
  const tb = document.getElementById(tbodyId);
  if (countId) document.getElementById(countId).textContent = `${attackers.length} tracked`;
  tb.innerHTML = '';
  attackers.forEach(a => {
    const s = a.threat_score||0;
    const cls = s>=90?'critical':s>=70?'high':s>=40?'medium':'low';
    const tier = (a.attacker_tier||'beginner').replace(' ','_');
    const barC = s>=90?'#f43f5e':s>=70?'#f59e0b':s>=40?'#a855f7':'#475569';
    const tr = document.createElement('tr');
    tr.onclick = () => openModal(a.src_ip);
    tr.innerHTML = `<td><span style="color:var(--cyan);font-weight:700">${a.src_ip}</span></td>
      <td><div style="display:flex;align-items:center;gap:8px"><span class="score-pill ${cls}">${s.toFixed(0)}</span><div style="flex:1;max-width:50px;height:3px;background:var(--border2);border-radius:2px;overflow:hidden"><div style="width:${Math.min(s,100)}%;height:100%;background:${barC}"></div></div></div></td>
      <td style="color:var(--t2)">${(a.classified_intent||'—').replace(/_/g,' ')}</td>
      <td><span class="tier-badge ${tier}">${(a.attacker_tier||'—').replace(/_/g,' ')}</span></td>
      <td><span style="color:var(--purple);font-weight:600">${(a.ttps||[]).length}</span></td>
      <td style="color:var(--t3)">${a.last_seen?timeSince(a.last_seen):'—'}</td>
      <td><button class="btn btn-sm btn-secondary" onclick="event.stopPropagation();openModal('${a.src_ip}')"><i class="fa-solid fa-eye"></i></button></td>`;
    tb.appendChild(tr);
  });
}

function renderEnvCards(containerId, envs) {
  const c = document.getElementById(containerId);
  if (!envs.length) { c.innerHTML = '<div style="color:var(--t4);font-size:12px;grid-column:1/-1"><i class="fa-solid fa-server" style="margin-right:6px"></i>No active environments</div>'; return; }
  c.innerHTML = '';
  envs.forEach(e => {
    const age = Math.floor((Date.now()/1000-e.created_at)/60);
    const card = document.createElement('div');
    card.className = 'env-card';
    card.innerHTML = `<div class="env-card-top"><span class="env-ip">${e.src_ip}</span><span class="env-tier">${(e.attacker_tier||'').replace(/_/g,' ')}</span></div>
      <div class="env-host"><i class="fa-solid fa-server" style="margin-right:5px;color:var(--t4)"></i>${e.hostname||'—'}</div>
      <div class="env-services">${(e.services||[]).map(s=>`<span class="env-svc">${s}</span>`).join('')}</div>
      <div class="env-footer"><i class="fa-regular fa-clock"></i> ${age}m active · <i class="fa-solid fa-bolt"></i> ${(e.engagement_log||[]).length} interactions</div>`;
    c.appendChild(card);
  });
}

/* ── Full pages ── */
async function loadFullAttackers() {
  try {
    const d = await (await fetch('/api/attackers?limit=100')).json();
    const arr = d.attackers || [];
    const tb = document.getElementById('full-attackers-tbody');
    document.getElementById('full-attacker-count').textContent = `${arr.length} profiles`;
    if (!arr.length) return;
    tb.innerHTML = '';
    arr.forEach(a => {
      const s = a.threat_score||0;
      const cls = s>=90?'critical':s>=70?'high':s>=40?'medium':'low';
      const tier = (a.attacker_tier||'beginner').replace(' ','_');
      const tr = document.createElement('tr');
      tr.onclick = () => openModal(a.src_ip);
      tr.innerHTML = `<td style="color:var(--cyan);font-weight:700">${a.src_ip}</td>
        <td><span class="score-pill ${cls}">${s.toFixed(0)}</span></td>
        <td style="color:var(--t2)">${(a.classified_intent||'—').replace(/_/g,' ')}</td>
        <td><span class="tier-badge ${tier}">${(a.attacker_tier||'—').replace(/_/g,' ')}</span></td>
        <td style="color:var(--purple)">${(a.ttps||[]).length}</td>
        <td>${a.total_commands||0}</td>
        <td style="color:var(--t3)">${a.first_seen?timeSince(a.first_seen):'—'}</td>
        <td style="color:var(--t3)">${a.last_seen?timeSince(a.last_seen):'—'}</td>
        <td><button class="btn btn-sm btn-secondary" onclick="event.stopPropagation();openModal('${a.src_ip}')"><i class="fa-solid fa-eye"></i></button></td>`;
      tb.appendChild(tr);
    });
  } catch(e) {}
}
async function loadFullEnvs() {
  try {
    const [ed, hd] = await Promise.all([
      fetch('/api/environments').then(r=>r.json()),
      fetch('/api/honeypots').then(r=>r.json()),
    ]);

    // Sensors grid
    const sensors = hd.sensors || [];
    const sg = document.getElementById('sensors-grid');
    if (sg) {
      const totalHits = hd.total_hits || 0;
      const uniq = hd.unique_attackers || 0;
      document.getElementById('sensors-summary').textContent = `${totalHits} total hits · ${uniq} unique attackers`;
      sg.innerHTML = sensors.map(s => {
        const hitColor = s.hits > 0 ? '#22d3ee' : 'var(--t4)';
        const dot = s.status==='online' ? '#10b981' : '#f43f5e';
        const last = s.last_seen ? timeSince(s.last_seen) : 'never';
        return `<div style="background:var(--bg3);border:1px solid var(--border2);border-radius:8px;padding:14px">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <div style="width:8px;height:8px;border-radius:50%;background:${dot};flex-shrink:0"></div>
            <span style="font-weight:700;color:var(--t1);font-size:13px">${s.protocol}</span>
            <span style="margin-left:auto;color:var(--t4);font-size:11px">:${s.port}</span>
          </div>
          <div style="font-size:22px;font-weight:800;color:${hitColor};margin-bottom:4px">${s.hits}</div>
          <div style="font-size:11px;color:var(--t4)">hits · last: ${last}</div>
        </div>`;
      }).join('');
    }

    // Recent sessions table
    const sessions = hd.recent_sessions || [];
    document.getElementById('sessions-count').textContent = `${sessions.length} shown`;
    const stb = document.getElementById('sessions-tbody');
    if (stb) {
      if (!sessions.length) {
        stb.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--t4);padding:24px;font-family:var(--sans)">No sessions yet</td></tr>';
      } else {
        stb.innerHTML = sessions.map(s => {
          const cmds = (s.commands||[]).length;
          const dur = s.duration_secs ? s.duration_secs.toFixed(1)+'s' : '—';
          const ago = s.start_time ? timeSince(s.start_time) : '—';
          const ip = s.src_ip||'—';
          return `<tr style="cursor:pointer" onclick="openHpModal('${ip}')">
            <td style="color:var(--cyan);font-weight:700">${ip}</td>
            <td style="color:var(--t2)">${s.protocol||'ssh'}</td>
            <td style="color:var(--t3)">${s.username||'—'}</td>
            <td style="color:var(--purple);font-weight:600">${cmds}</td>
            <td style="color:var(--t3)">${dur}</td>
            <td style="color:var(--t4)">${ago}</td>
            <td><button class="btn btn-sm btn-secondary" onclick="event.stopPropagation();openHpModal('${ip}')"><i class="fa-solid fa-magnifying-glass"></i></button></td>
          </tr>`;
        }).join('');
      }
    }

    // Deception environments
    const envs = ed.environments||[];
    document.getElementById('envs-count').textContent = `${envs.length} active`;
    renderEnvCards('envs-full', envs);
  } catch(e) { console.error('loadFullEnvs', e); }
}
async function loadResponses() {
  try {
    const d = await (await fetch('/api/response/log')).json();
    const log = d.log||[];
    const tb = document.getElementById('response-tbody');
    if (!log.length) return;
    const actionColors = {block_emergency:'#f43f5e',isolate_alert:'#f59e0b',slow_redirect:'#a855f7',log_only:'#64748b',manual_block:'#f43f5e'};
    tb.innerHTML = '';
    log.forEach(r => {
      const c = actionColors[r.action]||'#64748b';
      const tr = document.createElement('tr');
      tr.innerHTML = `<td><span style="color:${c};font-weight:600">${(r.action||'').replace(/_/g,' ')}</span></td>
        <td style="color:var(--cyan)">${r.src_ip||'—'}</td>
        <td>${r.threat_score!=null?r.threat_score.toFixed(0):'—'}</td>
        <td style="color:var(--t3)">${r.timestamp?new Date(r.timestamp*1000).toLocaleString():'—'}</td>`;
      tb.appendChild(tr);
    });
  } catch(e) {}
}

/* ════════════════════════════════════════
   MODAL
════════════════════════════════════════ */
async function openModal(ip) {
  state.selectedIP = ip;
  setText('modal-ip', ip);
  ['modal-intent','modal-tier','modal-sessions','modal-first','modal-last'].forEach(id=>setText(id,'…'));
  setText('modal-score-val','…');
  document.getElementById('modal-ttps').innerHTML = '<span style="color:var(--t4);font-size:11px">Loading…</span>';
  document.getElementById('profile-modal').classList.remove('hidden');
  let p;
  try { const r = await fetch('/api/attackers/'+ip); if(!r.ok) throw 0; p = await r.json(); }
  catch { p = { classified_intent:'malware_deployment', attacker_tier:'advanced_human', session_count:3, total_commands:24, threat_score:94, first_seen:Date.now()/1000-3600, last_seen:Date.now()/1000-120, ttps:[{technique_id:'T1105'},{technique_id:'T1003.008'},{technique_id:'T1053.003'},{technique_id:'T1021.004'},{technique_id:'T1496'},{technique_id:'T1033'}] }; }
  setText('modal-intent',(p.classified_intent||'—').replace(/_/g,' '));
  setText('modal-tier',(p.attacker_tier||'—').replace(/_/g,' '));
  setText('modal-sessions',`${p.session_count||0} sessions · ${p.total_commands||0} cmds`);
  setText('modal-first',p.first_seen?new Date(p.first_seen*1000).toLocaleString():'—');
  setText('modal-last',p.last_seen?new Date(p.last_seen*1000).toLocaleString():'—');
  setText('modal-score-val',(p.threat_score||0).toFixed(0));
  const g = document.getElementById('modal-ttps');
  const ttps = p.ttps||[];
  g.innerHTML = ttps.length ? ttps.slice(0,16).map(t=>`<span class="ttp-chip" title="${t.technique_name||''}">${t.technique_id}</span>`).join('') : '<span style="color:var(--t4);font-size:11px">No TTPs detected</span>';
  drawGauge('modal-gauge', p.threat_score||0, 180, 100);
}
function handleModalBg(e) { if (e.target === document.getElementById('profile-modal')) closeModal(); }
function closeModal() { document.getElementById('profile-modal').classList.add('hidden'); state.selectedIP = null; }
async function blockIP() {
  if (!state.selectedIP) return;
  if (!confirm(`Block ${state.selectedIP}?\nThis adds an iptables DROP rule.`)) return;
  try {
    await fetch('/api/response/block', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...AUTH.header() },
      body: JSON.stringify({ src_ip: state.selectedIP }),
    });
  } catch(e) {}
  closeModal(); fetchStats();
}

/* ════════════════════════════════════════
   HONEYPOT IP DETAIL MODAL
════════════════════════════════════════ */

function closeHpModal() {
  document.getElementById('hp-modal').classList.add('hidden');
}

async function openHpModal(ip) {
  const modal = document.getElementById('hp-modal');
  const body  = document.getElementById('hp-modal-body');
  document.getElementById('hp-modal-ip').textContent = ip;
  body.innerHTML = '<div style="text-align:center;color:var(--t4);padding:32px"><i class="fa-solid fa-spinner fa-spin"></i> Loading…</div>';
  modal.classList.remove('hidden');

  try {
    const d = await fetch(`/api/honeypots/sessions/${ip}`).then(r => r.json());

    const sev = c => c === 'critical' ? '#f43f5e' : c === 'high' ? '#f59e0b' : c === 'medium' ? '#a855f7' : '#64748b';

    // ── Summary chips ─────────────────────────────────────────────────────
    const chips = [
      { label: 'Sessions',    val: d.session_count,                      color: '#22d3ee' },
      { label: 'Events',      val: d.event_count,                        color: '#f59e0b' },
      { label: 'Commands',    val: d.all_commands.length,                 color: '#a855f7' },
      { label: 'Ports hit',   val: (d.ports_hit||[]).join(', ')||'—',    color: '#10b981' },
    ].map(c => `<div style="background:var(--bg3);border:1px solid var(--border2);border-radius:8px;padding:10px 14px;flex:1;min-width:100px">
      <div style="font-size:20px;font-weight:800;color:${c.color}">${c.val}</div>
      <div style="font-size:11px;color:var(--t4);margin-top:2px">${c.label}</div>
    </div>`).join('');

    // ── Credentials tried ────────────────────────────────────────────────
    const credRows = (d.sessions||[]).filter(s=>s.username||s.password).map(s =>
      `<tr><td style="color:#f59e0b;font-family:monospace">${s.username||'—'}</td>
           <td style="color:#f43f5e;font-family:monospace">${s.password||'—'}</td>
           <td style="color:var(--t4);font-size:11px">${s.start_time ? timeSince(s.start_time) : '—'}</td></tr>`
    ).join('');

    // ── Commands ──────────────────────────────────────────────────────────
    const cmdRows = d.all_commands.length
      ? d.all_commands.map(c =>
          `<tr><td style="font-family:monospace;color:#22d3ee;word-break:break-all">${escHtml(c.cmd)}</td>
               <td style="color:var(--t4);font-size:11px;white-space:nowrap">${c.time ? timeSince(c.time) : '—'}</td></tr>`
        ).join('')
      : '<tr><td colspan="2" style="color:var(--t4);text-align:center;padding:16px">No commands recorded</td></tr>';

    // ── Attack events ─────────────────────────────────────────────────────
    const evtRows = (d.events||[]).slice(0,30).map(e =>
      `<tr>
        <td><span style="color:${sev(e.severity)};font-weight:600;font-size:11px">${(e.severity||'').toUpperCase()}</span></td>
        <td style="color:var(--t2)">${(e.attack_type||'').replace(/_/g,' ')}</td>
        <td style="color:var(--t3)">:${e.dst_port||'?'}</td>
        <td style="color:var(--t4);font-size:11px">${e.timestamp ? timeSince(e.timestamp) : '—'}</td>
      </tr>`
    ).join('') || '<tr><td colspan="4" style="color:var(--t4);text-align:center;padding:16px">No events</td></tr>';

    // ── Attack types ──────────────────────────────────────────────────────
    const typeChips = (d.attack_types||[]).map(t =>
      `<span style="background:rgba(99,102,241,0.15);color:#818cf8;border:1px solid rgba(99,102,241,0.3);
        border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600">${t.replace(/_/g,' ')}</span>`
    ).join(' ') || '<span style="color:var(--t4);font-size:12px">None</span>';

    body.innerHTML = `
      <!-- Summary -->
      <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px">${chips}</div>

      <!-- Attack types -->
      <div style="margin-bottom:20px">
        <div style="font-size:11px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Attack Types</div>
        <div style="display:flex;flex-wrap:wrap;gap:6px">${typeChips}</div>
      </div>

      ${credRows ? `
      <!-- Credentials -->
      <div style="margin-bottom:20px">
        <div style="font-size:11px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Credentials Tried</div>
        <div style="overflow-x:auto;max-height:160px;overflow-y:auto">
          <table class="data-table">
            <thead><tr><th>Username</th><th>Password</th><th>When</th></tr></thead>
            <tbody>${credRows}</tbody>
          </table>
        </div>
      </div>` : ''}

      <!-- Commands -->
      <div style="margin-bottom:20px">
        <div style="font-size:11px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Commands Executed <span style="color:var(--t4);font-weight:400">(${d.all_commands.length})</span></div>
        <div style="overflow-x:auto;max-height:220px;overflow-y:auto">
          <table class="data-table">
            <thead><tr><th>Command</th><th>When</th></tr></thead>
            <tbody>${cmdRows}</tbody>
          </table>
        </div>
      </div>

      <!-- Events -->
      <div>
        <div style="font-size:11px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Alert Events <span style="color:var(--t4);font-weight:400">(${d.event_count} total, showing ${Math.min(d.event_count,30)})</span></div>
        <div style="overflow-x:auto;max-height:220px;overflow-y:auto">
          <table class="data-table">
            <thead><tr><th>Severity</th><th>Type</th><th>Port</th><th>When</th></tr></thead>
            <tbody>${evtRows}</tbody>
          </table>
        </div>
      </div>
    `;
  } catch(e) {
    body.innerHTML = `<div style="color:#f43f5e;padding:24px">Failed to load data for ${ip}</div>`;
  }
}

function escHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/* ════════════════════════════════════════
   GAUGE (shared)
════════════════════════════════════════ */
function drawGauge(canvasId, score, w, h) {
  const c = document.getElementById(canvasId); if (!c) return;
  const ctx = c.getContext('2d'); const dpr = window.devicePixelRatio||1;
  c.width=w*dpr; c.height=h*dpr; c.style.width=w+'px'; c.style.height=h+'px';
  ctx.setTransform(1,0,0,1,0,0); ctx.scale(dpr,dpr);
  const cx=w/2, cy=h-8, r=Math.min(w/2-12,h-18);
  ctx.beginPath(); ctx.arc(cx,cy,r,Math.PI,2*Math.PI); ctx.lineWidth=13; ctx.strokeStyle='rgba(255,255,255,0.05)'; ctx.lineCap='round'; ctx.stroke();
  if (score>0) {
    const col = score>=90?'#f43f5e':score>=70?'#f59e0b':score>=40?'#a855f7':'#10b981';
    ctx.shadowBlur=12; ctx.shadowColor=col;
    ctx.beginPath(); ctx.arc(cx,cy,r,Math.PI,Math.PI+(score/100)*Math.PI); ctx.lineWidth=13; ctx.strokeStyle=col; ctx.lineCap='round'; ctx.stroke();
    ctx.shadowBlur=0;
  }
}

/* ════════════════════════════════════════
   CBEE
════════════════════════════════════════ */
const BIAS_COLORS = {curiosity_gap:'#f59e0b',confirmation_bias:'#a855f7',sunk_cost:'#10b981',authority_signal:'#22d3ee',scarcity_framing:'#f43f5e'};
const BIAS_LABELS = {curiosity_gap:'Curiosity Gap',confirmation_bias:'Confirmation Bias',sunk_cost:'Sunk Cost Trap',authority_signal:'Authority Signals',scarcity_framing:'Scarcity Framing'};

async function loadCBEE() {
  try {
    const [pd, id] = await Promise.all([fetch('/api/cbee/profiles').then(r=>r.json()), fetch('/api/cbee/injections').then(r=>r.json())]);
    const profiles = pd.profiles||[], inj = id.injections||[];
    setText('cbee-kpi-profiles', profiles.length||'—');
    setText('cbee-kpi-inj', inj.length||'—');
    if (profiles.length) {
      const cnt={}; profiles.forEach(p=>cnt[p.dominant]=(cnt[p.dominant]||0)+1);
      const top=Object.entries(cnt).sort((a,b)=>b[1]-a[1])[0]?.[0];
      setText('cbee-kpi-dom',(BIAS_LABELS[top]||top||'—').split(' ')[0]);
    }
    renderCBEEProfiles(profiles); renderCBEEInj(inj);
  } catch(e) {}
}
function renderCBEEProfiles(profiles) {
  const el = document.getElementById('cbee-profiles');
  if (!profiles.length) { el.innerHTML='<div class="feed-empty"><i class="fa-solid fa-brain" style="font-size:24px;color:rgba(245,158,11,0.2)"></i>No active sessions</div>'; return; }
  el.innerHTML = '';
  profiles.forEach(p => {
    const bars = Object.keys(BIAS_LABELS).map(k=>{
      const v=Math.round(p[k]||0),c=BIAS_COLORS[k],dom=k===p.dominant;
      return `<div class="pbar-row"><div class="pbar-label${dom?' dom':''}">${BIAS_LABELS[k]}${dom?' ★':''}</div><div class="pbar-track"><div class="pbar-fill" style="width:${v}%;background:${c};${dom?'box-shadow:0 0 8px '+c:''}"></div></div><div class="pbar-val" style="${dom?'color:'+c:''}">${v}</div></div>`;
    }).join('');
    const card = document.createElement('div'); card.className='profile-card';
    card.innerHTML = `<div class="profile-top"><span class="env-ip">${p.src_ip}</span><span style="font-family:var(--mono);font-size:11px;color:var(--t3)">overall ${(p.overall||0).toFixed(1)}</span><span class="dom-tag">${BIAS_LABELS[p.dominant]||p.dominant}</span></div>${bars}`;
    el.appendChild(card);
  });
}
function renderCBEEInj(inj) {
  const el = document.getElementById('cbee-injections');
  if (!inj.length) { el.innerHTML='<div class="feed-empty" style="min-height:80px;font-size:11px;color:var(--t4)">None fired yet</div>'; return; }
  el.innerHTML='';
  inj.forEach(x=>{
    const c=BIAS_COLORS[x.bias_trigger]||'#64748b';
    const card=document.createElement('div'); card.className='inj-card'; card.style.borderLeftColor=c;
    card.innerHTML=`<div style="display:flex;align-items:center;gap:7px;margin-bottom:5px;flex-wrap:wrap"><i class="fa-solid fa-syringe" style="color:${c}"></i><span style="color:var(--cyan);font-weight:700">${x.src_ip}</span><span style="font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.5px;padding:1px 7px;border-radius:10px;background:${c}22;color:${c};border:1px solid ${c}55">${(x.bias_trigger||'').replace(/_/g,' ')}</span><span style="margin-left:auto;color:var(--t4);font-size:10px">${timeSince(x.created_at)}</span></div><div style="color:var(--t3)">Score <b style="color:#f59e0b">${(x.bias_score||0).toFixed(1)}</b> · Assets <b style="color:var(--t2)">${(x.assets||[]).length}</b> · <span style="color:${x.executed?'#10b981':'#64748b'}">${x.executed?'✓ Injected':'Pending'}</span></div>`;
    el.appendChild(card);
  });
}
async function scoreSessionCBEE() {
  const out = document.getElementById('cbee-score-out');
  const cmds = document.getElementById('cbee-cmds').value.split('\n').map(c=>c.trim()).filter(Boolean);
  const dur = parseFloat(document.getElementById('cbee-dur').value)||0;
  const logins = parseInt(document.getElementById('cbee-logins').value)||1;
  let d;
  try { d = await (await fetch('/api/cbee/score',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({commands:cmds,duration_secs:dur,login_attempts:logins})})).json(); }
  catch { d = {curiosity_gap:72,confirmation_bias:38,sunk_cost:55,authority_signal:91,scarcity_framing:44,overall:60,dominant:'authority_signal'}; }
  out.style.display='flex';
  out.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><b style="font-size:12px">Analysis Result</b><span style="font-family:var(--mono);color:var(--t3);font-size:11px">Overall <b style="color:#f59e0b;font-size:14px">${(d.overall||0).toFixed(1)}</b></span></div>` +
    Object.keys(BIAS_LABELS).map(k=>{const v=Math.round(d[k]||0),c=BIAS_COLORS[k],dom=k===d.dominant;return `<div class="s-row"><div class="s-lbl${dom?' dom':''}">${BIAS_LABELS[k]}${dom?' ★':''}</div><div class="s-track"><div class="s-fill" style="width:${v}%;background:${c}"></div></div><div class="s-val">${v}</div></div>`;}).join('');
}

/* ════════════════════════════════════════
   GADCF
════════════════════════════════════════ */
const AMETA = {env_file:{i:'fa-file-shield',c:'#f43f5e'},email_thread:{i:'fa-envelope',c:'#f59e0b'},code_repo:{i:'fa-code',c:'#22d3ee'},wiki_page:{i:'fa-book',c:'#a855f7'},db_schema:{i:'fa-database',c:'#10b981'}};
const SOPHS = ['beginner','automated_bot','advanced_human'];
let gadcfAssets = [], gIndustry='financial_services', gIntent='credential_harvesting', gSoph=2;

function initGADCF() {
  document.querySelectorAll('#gadcf-ind-opts .opt-btn').forEach(b=>b.onclick=()=>{document.querySelectorAll('#gadcf-ind-opts .opt-btn').forEach(x=>x.classList.remove('active'));b.classList.add('active');gIndustry=b.dataset.v;});
  document.querySelectorAll('#gadcf-int-opts .opt-btn').forEach(b=>b.onclick=()=>{document.querySelectorAll('#gadcf-int-opts .opt-btn').forEach(x=>x.classList.remove('active'));b.classList.add('active');gIntent=b.dataset.v;});
  document.getElementById('gadcf-soph').oninput=e=>gSoph=parseInt(e.target.value);
}
async function loadGADCF() {
  try { const d = await (await fetch('/api/gadcf/assets')).json(); gadcfAssets = d.assets||[]; renderGADCF(); } catch { gadcfAssets=[]; renderGADCF(); }
  setText('gadcf-kpi-total', gadcfAssets.length||'0');
  const llm = gadcfAssets.some(a=>a.source==='llm');
  const el = document.getElementById('gadcf-kpi-llm'); el.textContent = llm?'Ollama':'Templates'; el.style.color = llm?'#10b981':'#64748b';
}
async function gadcfGenerate() {
  const btn = document.getElementById('gadcf-gen-btn'), st = document.getElementById('gadcf-status');
  btn.disabled=true; btn.innerHTML='<i class="fa-solid fa-spinner fa-spin"></i> Generating…'; st.textContent='';
  try {
    const d = await (await fetch('/api/gadcf/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({industry:gIndustry,intent:gIntent,sophistication:SOPHS[gSoph]})})).json();
    if (d.assets) { gadcfAssets=[...d.assets,...gadcfAssets]; renderGADCF(); selectAsset(d.assets[0]); setText('gadcf-kpi-total',gadcfAssets.length); st.textContent=`✓ ${d.count} assets (${d.assets[0]?.source||'template'})`; st.style.color='#10b981'; }
  } catch { st.textContent='✗ Failed'; st.style.color='#f43f5e'; }
  btn.disabled=false; btn.innerHTML='<i class="fa-solid fa-wand-magic-sparkles"></i> Generate Package';
}
function renderGADCF() {
  const el = document.getElementById('gadcf-assets');
  document.getElementById('gadcf-count').textContent = `${gadcfAssets.length} total`;
  if (!gadcfAssets.length) { el.innerHTML='<div class="feed-empty"><i class="fa-solid fa-folder-open" style="font-size:24px;color:rgba(99,102,241,0.2)"></i>Generate a package</div>'; return; }
  el.innerHTML='';
  gadcfAssets.slice(0,30).forEach(a=>{
    const m=AMETA[a.asset_type]||{i:'fa-file',c:'#64748b'}, llm=a.source==='llm';
    const it=document.createElement('div'); it.className='asset-list-item';
    it.innerHTML=`<div style="width:34px;height:34px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:13px;background:${m.c}1f;color:${m.c};flex-shrink:0"><i class="fa-solid ${m.i}"></i></div><div style="flex:1;min-width:0"><div style="font-family:var(--mono);font-size:11px;color:var(--cyan);font-weight:600">${a.filename||a.asset_type}</div><div style="font-size:10px;color:var(--t3)">${(a.industry||'').replace(/_/g,' ')} · ${(a.attacker_intent||'').replace(/_/g,' ')}</div></div><span style="font-size:8px;font-weight:800;padding:2px 6px;border-radius:3px;text-transform:uppercase;flex-shrink:0;background:${llm?'rgba(16,185,129,0.15)':'rgba(100,116,139,0.12)'};color:${llm?'#10b981':'#64748b'}">${llm?'LLM':'TMPL'}</span>`;
    it.onclick=()=>selectAsset(a,it);
    el.appendChild(it);
  });
}
function selectAsset(a, el) {
  document.querySelectorAll('.asset-list-item').forEach(x=>x.classList.remove('sel'));
  if (el) el.classList.add('sel');
  setText('gadcf-prev-name', a.filename||'');
  const pv = document.getElementById('gadcf-preview'); pv.textContent = a.content||'(no content)';
}

/* ════════════════════════════════════════
   FHIM
════════════════════════════════════════ */
const FLAGS = {EG:'🇪🇬',US:'🇺🇸',DE:'🇩🇪',SA:'🇸🇦',GB:'🇬🇧',FR:'🇫🇷',CN:'🇨🇳',AU:'🇦🇺',JP:'🇯🇵'};
async function loadFHIM() {
  try {
    const [nd, rd] = await Promise.all([fetch('/api/fhim/nodes').then(r=>r.json()), fetch('/api/fhim/rounds').then(r=>r.json())]);
    const nodes = nd.nodes||[], f1 = nd.global_f1||0;
    setText('fhim-kpi-nodes', nodes.length||'—');
    setText('fhim-kpi-f1', (f1*100).toFixed(1)+'%');
    setText('fhim-kpi-samples', nodes.reduce((a,n)=>a+(n.samples_contributed||0),0).toLocaleString());
    renderFHIMNodes(nodes); renderFHIMRounds(rd.rounds||[]);
  } catch(e) {}
}
function renderFHIMNodes(nodes) {
  const el = document.getElementById('fhim-nodes');
  if (!nodes.length) { el.innerHTML='<div style="color:var(--t4);font-size:12px">No nodes</div>'; return; }
  el.innerHTML='';
  nodes.forEach(n=>{
    const flag=FLAGS[n.location]||'🌐', f1=((n.f1_score||0)*100).toFixed(1);
    const card=document.createElement('div'); card.className='node-card';
    const sp = n.status==='synced'?'background:rgba(16,185,129,0.15);color:#10b981;border:1px solid rgba(16,185,129,0.3)':'background:rgba(100,116,139,0.1);color:#64748b;border:1px solid rgba(100,116,139,0.2)';
    card.innerHTML=`<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px"><span style="font-size:24px">${flag}</span><div style="flex:1;min-width:0"><div style="font-weight:700;font-size:13px">${n.org_name}</div><div style="font-family:var(--mono);font-size:10px;color:var(--t3)">${n.node_id}</div></div><span style="font-size:9px;font-weight:700;padding:2px 8px;border-radius:20px;text-transform:uppercase;letter-spacing:0.5px;${sp}">${n.status}</span></div><div class="node-stats"><div class="node-stat"><div class="node-stat-v">${f1}%</div><div class="node-stat-l">Local F1</div></div><div class="node-stat"><div class="node-stat-v">${n.rounds_total||0}</div><div class="node-stat-l">Rounds</div></div><div class="node-stat"><div class="node-stat-v" style="font-size:14px">${(n.samples_contributed||0).toLocaleString()}</div><div class="node-stat-l">Samples</div></div><div class="node-stat"><div class="node-stat-v" style="font-size:13px;color:${n.status==='synced'?'#10b981':'#64748b'}">${n.location||'?'}</div><div class="node-stat-l">Region</div></div></div><div style="font-size:10px;color:var(--t4);font-family:var(--mono);margin-top:10px;border-top:1px solid var(--border);padding-top:8px"><i class="fa-regular fa-clock"></i> Last: ${timeSince(n.last_round)}</div>`;
    el.appendChild(card);
  });
}
function renderFHIMRounds(rounds) {
  const el = document.getElementById('fhim-rounds');
  if (!rounds.length) { el.innerHTML='<div style="color:var(--t4);font-size:11px">No rounds yet</div>'; return; }
  el.innerHTML='';
  rounds.slice(0,8).forEach(r=>{
    const d=document.createElement('div');
    d.style.cssText='display:flex;align-items:center;gap:10px;background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:8px 12px;font-size:11px;font-family:var(--mono);margin-bottom:6px';
    d.innerHTML=`<span style="color:#10b981;font-weight:700;font-size:14px">${((r.global_f1_after||0)*100).toFixed(1)}%</span><span style="color:var(--t3)">F1</span><span>${r.participants||'—'} nodes</span><span style="margin-left:auto;color:var(--t4)">${timeSince(r.timestamp)}</span>`;
    el.appendChild(d);
  });
}

/* ════════════════════════════════════════
   DEMO DATA (when no live MongoDB)
════════════════════════════════════════ */
function injectDemo() {
  const events = [
    {src_ip:'91.234.56.78',dst_port:22,attack_type:'brute_force',severity:'high',honeypot_source:'cowrie',timestamp:Date.now()/1000-10},
    {src_ip:'185.220.101.42',dst_port:22,attack_type:'brute_force',severity:'critical',honeypot_source:'cowrie',timestamp:Date.now()/1000-8},
    {src_ip:'45.33.32.156',dst_port:80,attack_type:'port_scan',severity:'low',honeypot_source:'scapy',timestamp:Date.now()/1000-6},
    {src_ip:'198.51.100.42',dst_port:22,attack_type:'command_injection',severity:'high',honeypot_source:'cowrie',timestamp:Date.now()/1000-4},
    {src_ip:'103.21.244.0',dst_port:445,attack_type:'malware_upload',severity:'critical',honeypot_source:'dionaea',timestamp:Date.now()/1000-2},
    {src_ip:'2.56.57.90',dst_port:3306,attack_type:'brute_force',severity:'medium',honeypot_source:'cowrie',timestamp:Date.now()/1000-1},
  ];
  // only inject if feed still empty (no live data)
  if (state.feedItems.length === 0) {
    events.forEach(e=>{ addFeed(e); pushTimeline(); });
    if (document.getElementById('kpi-events').textContent === '0') {
      animateVal('kpi-events',0,1247,800); animateVal('kpi-sessions',0,3,600);
      animateVal('kpi-blocked',0,8,700); animateVal('kpi-envs',0,3,500);
      const tl=document.getElementById('kpi-threat-level'); tl.textContent='HIGH'; tl.style.color='#f59e0b';
    }
    if (document.getElementById('attackers-tbody').children.length <= 1) {
      renderAttackerTable('attackers-tbody',[
        {src_ip:'185.220.101.42',threat_score:94,classified_intent:'malware_deployment',attacker_tier:'advanced_human',ttps:[{},{},{},{},{}],last_seen:Date.now()/1000-60},
        {src_ip:'91.234.56.78',threat_score:78.5,classified_intent:'credential_harvesting',attacker_tier:'automated_bot',ttps:[{},{},{}],last_seen:Date.now()/1000-120},
        {src_ip:'198.51.100.42',threat_score:52,classified_intent:'reconnaissance',attacker_tier:'beginner',ttps:[{}],last_seen:Date.now()/1000-240},
      ],'attacker-count');
    }
    setTimeout(()=>{
      addMarker(51.5074,-0.1278,'185.220.101.42','critical');
      addMarker(40.7128,-74.006,'45.33.32.156','low');
      addMarker(35.6762,139.6503,'103.21.244.0','critical');
      addMarker(48.8566,2.3522,'91.234.56.78','high');
      addMarker(55.7558,37.6176,'2.56.57.90','medium');
    },600);
  }
}
function animateVal(id, from, to, dur) {
  const el = document.getElementById(id); if (!el) return;
  const start = performance.now();
  const step = now => { const t=Math.min((now-start)/dur,1); el.textContent=Math.round(from+(to-from)*(1-Math.pow(1-t,3))).toLocaleString(); if(t<1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

/* ── Utils ── */
function setText(id, v){ const el=document.getElementById(id); if(el) el.textContent=v; }
function fmtNum(n){ return n==null?'—':Number(n).toLocaleString(); }
function timeSince(ts){ if(!ts) return '—'; const s=Math.floor(Date.now()/1000-ts); if(s<60) return s+'s ago'; if(s<3600) return Math.floor(s/60)+'m ago'; if(s<86400) return Math.floor(s/3600)+'h ago'; return Math.floor(s/86400)+'d ago'; }
