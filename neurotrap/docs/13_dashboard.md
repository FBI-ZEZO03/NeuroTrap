# Dashboard

The NeuroTrap dashboard is a single-page application (SPA) served by the Flask API. It provides real-time visibility into all active threats, attacker profiles, intelligence data, and the innovation modules (CBEE, GADCF, FHIM, ADT, SOC Analyst).

---

## Access

| URL | Notes |
|-----|-------|
| `https://<server-ip>` | Primary HTTPS access (self-signed cert) |
| `http://<server-ip>:8080` | Redirected to HTTPS by Nginx |
| `http://localhost:5000` | Direct Flask access (development only) |

---

## Architecture

The dashboard is a Jinja2-rendered HTML template (`dashboard/templates/index.html`) with modular JavaScript (`dashboard/static/js/`):

| JS file | Section |
|---------|---------|
| `app.js` | Core: auth, navigation, WebSocket, live feed, global state |
| `dashboard.js` | Main dashboard KPIs and attack map |
| `behavior.js` | Behavior Analysis section |
| `cbee.js` | CBEE section |
| `gadcf.js` | GADCF section |
| `fhim.js` | FHIM section |
| `intel.js` | Threat Intel + Geo Map sections |
| `soc.js` | AI Analyst section |
| `twin.js` | ADT section |

All sections are loaded on page open (no per-section loading spinners). The SPA uses hash-based navigation (`#dashboard`, `#attackers`, `#cbee`, etc.).

---

## Authentication

The dashboard uses JWT authentication. On load, `app.js` checks `localStorage` for a token. If absent, the login modal is shown.

```javascript
// app.js
async function login(username, password, otp) {
    const resp = await fetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password, otp })
    });
    const data = await resp.json();
    if (data.token) {
        localStorage.setItem('jwt', data.token);
        state.role = data.role;
        initApp();
    }
}
```

Admin-only features (manual block, generate report, CBEE ad-hoc score) show a lock icon and require admin role.

---

## Real-Time Feed

The live event feed uses WebSocket for real-time updates and a REST seed on page load:

```javascript
// Seed from API on page load
async function seedFeedFromApi() {
    const resp = await fetch('/api/events?limit=200');
    const data = await resp.json();
    state.feedItems = data.events;
    renderMainFeed();
}

// WebSocket: prepend new events as they arrive
socket.on('new_event', (event) => {
    state.feedItems.unshift(event);
    if (currentPage === 1) renderMainFeed();
    else showNewBadge(state.pendingNewCount++);
});
```

### Feed Features

- **Paginated:** 20 events per page with Prev/Next navigation
- **● LIVE badge:** shown on page 1
- **"N new ↑" badge:** shown on other pages when new events arrive
- **Scrollable within page:** 390px fixed height, `overflow-y: auto`
- **Events/min counter:** color-coded green < 3, amber 3–9, red ≥ 10
- **Click to detail:** any event card opens the attacker modal

---

## Dashboard Sections

### Operations

#### Dashboard (Main)

KPI cards:
- **Total Events** — total `alert_events` count
- **Active Sessions** — sessions in the last hour
- **IPs Blocked** — `block_emergency` + `isolate_alert` entries in `response_log`
- **Environments Deployed** — total deception environments (ever created)
- **Threat Level** — computed from top attacker scores

Charts:
- **Attack type distribution** — doughnut chart
- **Events over time** — 24h timeline
- **Top source countries** — bar chart (up to 22 countries)

Live feed: seeded from API on load, WebSocket-updated in real time.

#### Threat Actors

Table of all attacker profiles sorted by threat score:
- IP, threat score badge (LOW/MEDIUM/HIGH/CRITICAL), tier, intent, session count, last seen, country flag
- Click any row: opens full attacker modal with TTPs, session history, CBEE profile, kill chain stage

#### Live Events

Full paginated event log from all honeypots:
- Filter by attack type and severity
- Pagination (20/page)
- Each card shows: timestamp, source IP, attack type, severity, honeypot source, port

#### Honeypots

Three panels:
- **Live sensors** — hit counts and status per protocol (SSH, Telnet, HTTP, FTP, etc.)
- **Recent attacker sessions** — last 20 Cowrie sessions with command counts
- **Deception environments** — all spawned environments with status (active/expired)

#### Response Log

All autonomous response actions in reverse-chronological order:
- Color-coded by action type
- Shows IP, action, threat score, timestamp, and reason

### Intelligence

#### Threat Intel

- IOC list (indicators of compromise) — IPs with high threat scores
- Top source countries (with flag icons)
- Top targeted ports
- Attack type distribution over time
- Active campaigns

#### Geo Map

Full-page section with:
- **Leaflet.js world map** — animated arcs from attacker source to server
- **Threat-level markers** — color-coded by risk band
- **IP grid** — live table of active attacker IPs with geo info

#### MITRE ATT&CK

Full-viewport heatmap navigator:
- All 14 tactic columns with observed technique counts
- Click any cell: opens technique detail panel with description, observed commands, attacker IPs

#### Behavior Analysis

- ML intent distribution — doughnut chart of 6 intent classes
- Tier breakdown — beginner/automated_bot/advanced_human counts
- Top commands — normalized (path-stripped) command frequency
- Classified profiles table — all profiles with tier + intent tags

### Innovations

#### CBEE

- Bias profiles table — 5 dimension scores per attacker
- Bait injection log — which assets were planted for which IPs
- Ad-hoc scorer — paste commands to get live bias scoring (admin)

#### GADCF

- Asset library — all generated fake content with type and content preview
- Manual generation button (admin) — trigger asset generation for a target IP

#### FHIM

- Node status table — 4 demo organizations with F1 scores
- Aggregation rounds timeline — global F1 evolution per round

#### ADT (Attacker Digital Twins)

- Twin list — all twins with kill chain stage and predicted next moves
- Twin detail — click for full MITRE fingerprint, psychology summary, forward simulation
- Simulator — run N-step forward simulation (admin)

#### AI Analyst

- Shift summary — narrative overview of current threat landscape
- Triage queue — ranked action queue with risk bands
- Report generation — produce incident report for any IP (admin)
- Q&A chat — natural-language analyst interface (admin)

---

## WebSocket Events

| Event (server → client) | Payload | Trigger |
|------------------------|---------|---------|
| `connected` | `{"status": "connected"}` | On WebSocket connect |
| `subscribed` | `{"channel": "events"}` | After `subscribe_events` |
| `new_event` | `AlertEvent` dict | New event in `alert_events` |
| `profile_update` | `AttackerProfile` dict | Profile score/intent updated |

---

## Development

The source and dashboard directories are bind-mounted into the API container:

| Change type | What to do |
|-------------|-----------|
| HTML templates | Browser refresh |
| CSS / JS | Browser refresh (caching disabled in dev) |
| Python source | Rebuild API: `docker compose build api && docker compose up -d api && docker compose exec nginx nginx -s reload` |

When bumping static assets after major changes, increment the cache-busting version string in `index.html`:
```html
<link rel="stylesheet" href="/static/css/main.css?v=4"/>
```
