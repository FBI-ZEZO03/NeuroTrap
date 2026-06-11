# AI SOC Analyst

The AI SOC Analyst module provides an AI-powered interface for security operations teams. It generates structured triage queues, per-attacker incident reports, a natural-language Q&A interface, and shift summaries — all usable without any LLM API key (heuristic mode), with much richer output when `ANTHROPIC_API_KEY` is set (LLM mode).

---

## Components

| Component | File | Role |
|-----------|------|------|
| `SOCAnalyst` | `src/soc_analyst/soc_analyst.py` | All analyst logic: triage, reports, Q&A, summary |
| `LLMClient` | `src/soc_analyst/llm_client.py` | Thin Anthropic API wrapper with heuristic fallback |

---

## Operating Modes

| Mode | Requirement | Output quality |
|------|-------------|----------------|
| Heuristic | No API key needed | Structured text based on attacker data fields |
| LLM | `ANTHROPIC_API_KEY` set in `.env` | Rich narrative analysis, context-aware insights |

The mode is transparent to the API — both modes return identically shaped JSON. Enabling LLM mode is purely additive.

---

## Triage Queue

`GET /api/soc/triage` returns all active attackers ranked by threat score, with a risk band and recommended action:

```json
{
  "queue": [
    {
      "src_ip": "192.109.200.220",
      "priority": 1,
      "threat_score": 100.0,
      "risk_band": "CRITICAL",
      "recommended_action": "block",
      "reason": "798 sessions, bot_enrollment intent, automated_bot tier"
    },
    {
      "src_ip": "45.148.10.183",
      "priority": 2,
      "threat_score": 78.0,
      "risk_band": "HIGH",
      "recommended_action": "isolate",
      "reason": "12 sessions, credential_harvesting intent, /etc/shadow accessed"
    }
  ]
}
```

### Risk Bands

| Score Range | Band | Recommended Action |
|-------------|------|--------------------|
| ≥ 90 | CRITICAL | Block immediately (iptables DROP) |
| 70–89 | HIGH | Isolate and alert |
| 40–69 | ELEVATED | Slow redirect + monitor |
| < 40 | LOW | Monitor only |

---

## Incident Reports

`POST /api/soc/report` generates a detailed Markdown incident report for a specific IP:

**Request:**
```json
{ "src_ip": "192.109.200.220" }
```

**Heuristic report structure:**
```
# Incident Report — 192.109.200.220
**Generated:** 2025-06-09 10:15:32 UTC

## Executive Summary
This attacker has been active since [date], with [N] sessions recorded.
Classification: bot_enrollment (automated_bot tier). Threat score: 100/100.

## Timeline
- [timestamp] First contact: brute_force on port 22
- [timestamp] Successful login, executed: uname -a, id, cat /etc/passwd
- [timestamp] Downloaded: wget http://...
- [timestamp] Established persistence: crontab -e

## MITRE ATT&CK Techniques Observed
| Technique ID | Name | Tactic | Confidence |
|---|---|---|---|
| T1110 | Brute Force | Credential Access | 0.95 |
| T1105 | Ingress Tool Transfer | Command and Control | 0.90 |
| T1053.003 | Scheduled Task: Cron | Persistence | 0.85 |

## Recommended Response
BLOCK immediately. Evidence of bot infrastructure enrollment.
```

LLM mode produces richer narrative analysis with threat-intel context.

---

## Analyst Q&A

`POST /api/soc/chat` allows natural-language questions about the current threat landscape:

**Request:**
```json
{ "message": "What is 192.109.200.220 trying to do?" }
```

**Heuristic response:**
```json
{
  "reply": "Based on 798 sessions and bot_enrollment classification, this IP
            is attempting to enroll this system into a botnet. Key evidence:
            wget downloads followed by crontab persistence across multiple sessions."
}
```

**LLM response** (when API key set): Uses the full attacker profile and MITRE mappings as context to generate a detailed analyst-quality assessment.

---

## Shift Summary

`GET /api/soc/summary?hours=8` generates a summary of activity over the specified window:

```json
{
  "summary": "During the last 8 hours: 3 CRITICAL attackers detected, 2 blocked automatically.
              Top attack type: tool_fingerprint (18,671 events). 
              Most active source: Netherlands (14 unique IPs).
              New technique observed: T1053.003 (Cron persistence) — first seen this shift.",
  "generated_at": 1780969777.0,
  "window_hours": 8
}
```

---

## LLM Client

`LLMClient` (`src/soc_analyst/llm_client.py`) wraps the Anthropic API:

```python
class LLMClient:
    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return self._heuristic_fallback(prompt)
        response = self.client.messages.create(
            model="claude-opus-4-8",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _heuristic_fallback(self, prompt: str) -> str:
        # Extract data fields from context and generate structured text
        ...
```

The fallback ensures the SOC Analyst UI is never empty, even without an API key.

---

## Dashboard Integration

The **AI Analyst** section of the dashboard shows:

- **Triage queue** — ranked action list with risk band color coding
- **Shift summary panel** — auto-refreshed narrative summary
- **Incident reports** — admin can generate a report for any IP from the dashboard
- **Q&A chat** — admin-only chat interface for natural-language queries

---

## Enabling LLM Mode

```bash
# Add to .env
ANTHROPIC_API_KEY=sk-ant-...

# Restart the API
docker compose restart api
docker compose exec nginx nginx -s reload
```

---

## API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/soc/summary` | GET | — | Shift summary (`?hours=N`) |
| `/api/soc/triage` | GET | — | Ranked action queue |
| `/api/soc/reports` | GET | — | Recent report metadata |
| `/api/soc/report` | POST | admin | Generate incident report for one IP |
| `/api/soc/chat` | POST | admin | Natural-language Q&A |
