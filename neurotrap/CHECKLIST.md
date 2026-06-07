# NeuroTrap CADN — Full System Audit
**Date:** 2026-06-07  **Server:** 13.140.144.118  **Audited by:** Claude Code

---

## 🟢 Infrastructure

| Component | Status | Detail |
|-----------|--------|--------|
| nginx reverse proxy | ✅ Running | Port 443 (HTTPS) + 8080 (HTTP) |
| MongoDB | ✅ Running | Internal only — not exposed to internet |
| SSL Certificate | ✅ Valid | Expires 2028-09-08 (self-signed) |
| Port 443 (HTTPS) | ✅ Open | Dashboard accessible |
| Port 22 (Cowrie SSH) | ✅ Open | Honeypot receiving attacks |
| Port 50402 (Real SSH) | ✅ Open | Admin access intact |

---

## 🟢 Honeypots

| Honeypot | Status | Detail |
|----------|--------|--------|
| Cowrie (SSH/Telnet) | ✅ Running | Ports 22→2222, 23→2223 — active sessions right now |
| OpenCanary | ✅ Running | FTP/HTTP/SMB/MSSQL/MySQL/RDP/VNC/SNMP all open |
| Galah (LLM web) | ❌ Exited | Needs `ANTHROPIC_API_KEY` set in `.env` to run |
| Dionaea | ➖ Not deployed | Source present in `/home/neurotrap/dionaea-src` but not in compose |

---

## 🟢 Detection Pipeline

| Component | Status | Detail |
|-----------|--------|--------|
| Packet Monitor (Scapy) | ✅ Running | Host network — captures live traffic |
| Log Ingestion Pipeline | ✅ Running | Tailing Cowrie JSON logs in real time |
| alert_events collection | ✅ Active | 16,303 total · 5,122 last hour · 32 last 5 min |
| cowrie_sessions collection | ✅ Active | 1,870 sessions recorded |

---

## 🟢 Behavior Analysis

| Component | Status | Detail |
|-----------|--------|--------|
| Behavior Engine | ✅ Running | Classifying sessions every cycle |
| ML Classifier | ✅ Active | Intent + tier + score per session |
| attacker_profiles | ✅ Active | 75 profiles · 55 with country resolved |
| Blocked IPs | ⚠️ 0 | All threats currently LOW (max score 38.7) — threshold not reached |

---

## 🟢 Deception Engine

| Component | Status | Detail |
|-----------|--------|--------|
| Deception Engine | ✅ Running | Spawning environments for attackers |
| Active Environments | ⚠️ 0 now | Last env timed out at 20:29 (1h GC) — new ones spawn as threats qualify |
| Total Environments Created | ✅ 16 | Lifecycle working correctly |
| Docker socket access | ✅ OK | Container spawning works |

---

## 🟡 CBEE (Cognitive Bias Exploitation Engine)

| Component | Status | Detail |
|-----------|--------|--------|
| CBEE Engine | ✅ Running | Integrated in behavior container |
| CBEE Profiles | ⚠️ 3 | Low count — only attackers with enough session depth get scored |
| Bait Injections | ⚠️ 0 | None fired yet — CBEE score threshold not reached |

---

## 🔴 GADCF (Generative Deception Content)

| Component | Status | Detail |
|-----------|--------|--------|
| GADCF Engine | ⚠️ Degraded | Running on template fallback (no LLM) |
| Ollama (Mistral) | ❌ Not running | Not installed — GADCF uses static templates instead |
| GADCF Assets | ⚠️ 0 | No content generated yet (requires manual trigger or attacker activity) |
| `/api/gadcf/generate` | ✅ 200 | Endpoint works, returns template content |

---

## 🟢 Attacker Digital Twin

| Component | Status | Detail |
|-----------|--------|--------|
| Twin Engine | ✅ Running | Embedded in API |
| Twins Built | ✅ 5 | Live source — real attacker twins |
| Tactic Predictor (Markov) | ✅ Active | Next-tactic prediction working |
| Kill Chain Mapping | ✅ Active | MITRE → Lockheed Martin 7-stage |

---

## 🟢 FHIM (Federated Honeypot Intelligence Mesh)

| Component | Status | Detail |
|-----------|--------|--------|
| FHIM Nodes | ✅ 4 nodes | Cairo Uni, Acme Financial, Fraunhofer FKIE, SaudiTelecom |
| Aggregation Rounds | ⚠️ 0 | No rounds run yet — requires manual trigger |
| `/api/fhim/nodes` | ✅ 200 | Returns 4 demo nodes |

---

## 🟢 ASHRTA (Autonomous Self-Hardening)

| Component | Status | Detail |
|-----------|--------|--------|
| ASHRTA Scheduler | ✅ Available | Runs on demand via `/api/ashrta/run` |
| ASHRTA Reports | ⚠️ 0 | No cycles run yet — trigger manually |
| ASHRTA Patches | ⚠️ 0 | Follows from reports |

---

## 🟢 SOC Analyst

| Component | Status | Detail |
|-----------|--------|--------|
| SOC Analyst Engine | ✅ Running | Heuristic mode (no `ANTHROPIC_API_KEY`) |
| LLM Mode | ❌ Off | `ANTHROPIC_API_KEY` empty in `.env` |
| Triage Queue | ✅ 15 items | Ranked threat queue working |
| SOC Reports | ✅ 9 | Generated reports in DB |
| `/api/soc/summary` | ✅ 200 | 75 actors tracked, 16,290 events in window |

---

## 🟢 Response Engine

| Component | Status | Detail |
|-----------|--------|--------|
| Response Engine | ✅ Active | Decision matrix running per attacker |
| Response Log | ✅ 16 entries | All `log_only` (threats below 40 threshold) |
| Auto-block (≥ 90) | ✅ Armed | No attacker has reached threshold yet |

---

## 🟢 API & Dashboard

| Endpoint | Status | Response Time |
|----------|--------|---------------|
| `GET /` (Dashboard) | ✅ 200 | — |
| `GET /api/events/stats` | ✅ 200 | ~21ms (cached) |
| `GET /api/attackers` | ✅ 200 | ~31ms (cached) |
| `GET /api/honeypots` | ✅ 200 | ~18ms (cached) |
| `GET /api/environments` | ✅ 200 | ~16ms (cached) |
| `GET /api/intel` | ✅ 200 | ~18ms (cached) |
| `GET /api/response/log` | ✅ 200 | ~21ms (cached) |
| `GET /api/cbee/profiles` | ✅ 200 | ~23ms |
| `GET /api/gadcf/assets` | ✅ 200 | ~37ms |
| `GET /api/fhim/nodes` | ✅ 200 | ~15ms |
| `GET /api/twin/list` | ✅ 200 | ~22ms |
| `GET /api/soc/summary` | ✅ 200 | ~73ms |
| `GET /api/soc/triage` | ✅ 200 | ~19ms |
| WebSocket (Socket.IO) | ✅ 200 | Live feed pushing every 2s |

---

## 🟢 Live Data Pipeline (End-to-End)

```
Attacker hits port 22
  → Cowrie logs JSON event
    → Monitor tails log → saves AlertEvent to alert_events ✅
      → Behavior engine reads cowrie_sessions → classifies attacker ✅
        → Deception engine spawns honeypot environment ✅
          → API live-feed poller pushes to dashboard WebSocket ✅
            → Dashboard renders in real time ✅
```

---

## ⚠️ Items That Need Attention

| # | Issue | Fix |
|---|-------|-----|
| 1 | **Galah LLM honeypot offline** | Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`, then `docker compose up -d galah` |
| 2 | **SOC Analyst in heuristic mode** | Same — set `ANTHROPIC_API_KEY` to enable LLM reports |
| 3 | **GADCF no LLM content** | Install Ollama + pull Mistral, OR set `ANTHROPIC_API_KEY` for Claude fallback |
| 4 | **FHIM rounds = 0** | Trigger via `/api/fhim/trigger` or wait for automated schedule |
| 5 | **ASHRTA never run** | POST to `/api/ashrta/run` to start first red-team cycle |
| 6 | **CBEE injections = 0** | Normal — attackers haven't held sessions long enough to trigger bait |

---

## 📊 Key Numbers (as of audit)

| Metric | Value |
|--------|-------|
| Total Events | 16,303 |
| Events/hour (last 1h) | 5,122 |
| Active Attackers (profiles) | 75 |
| Cowrie Sessions | 1,870 |
| Digital Twins | 5 |
| Deception Environments (total) | 16 |
| Countries Seen | 15 |
| Top Attacker | 192.109.200.220 (Netherlands, score 38.7) |
| API Cache TTL | 30 seconds |
| Live Feed Poll | every 2 seconds |
