# Installation & Deployment Guide

This guide covers full production deployment on Ubuntu 22.04/24.04 using Docker Compose, and local development without Docker.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 also tested |
| CPU | 4 cores | 6+ recommended for production |
| RAM | 8 GB | 11 GB recommended |
| Disk | 50 GB | 200+ GB recommended for log retention |
| Docker Engine | 24.x | With Compose v2 plugin |
| Open ports | 22, 23, 80, 443, 8080 | Plus optional: 21, 445, 1433, 3306, 3389, 5900, 161/udp |

---

## Step 1 — Host Hardening

### 1.1 Move your real SSH off port 22

Port 22 must be free for Cowrie. Do this *before* running the stack.

```bash
# Edit SSH config
sudo sed -i 's/^#Port 22/Port 50402/' /etc/ssh/sshd_config
sudo sed -i 's/^Port 22/Port 50402/' /etc/ssh/sshd_config

# Verify the change before restarting
grep ^Port /etc/ssh/sshd_config   # should print: Port 50402

sudo systemctl restart sshd
```

> **Keep your current SSH session open** while testing a new session on port 50402 before closing the original.

### 1.2 Configure UFW firewall

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Admin SSH (real)
sudo ufw allow 50402/tcp comment "SSH management"

# Honeypot ports
sudo ufw allow 22/tcp   comment "Cowrie SSH honeypot"
sudo ufw allow 23/tcp   comment "Cowrie Telnet"
sudo ufw allow 80/tcp   comment "OpenCanary HTTP"
sudo ufw allow 443/tcp  comment "Dashboard HTTPS"
sudo ufw allow 8080/tcp comment "Dashboard HTTP redirect"
sudo ufw allow 8088/tcp comment "Galah LLM web honeypot"
sudo ufw allow 21/tcp   comment "OpenCanary FTP"
sudo ufw allow 445/tcp  comment "OpenCanary SMB"
sudo ufw allow 1433/tcp comment "OpenCanary MSSQL"
sudo ufw allow 3306/tcp comment "OpenCanary MySQL"
sudo ufw allow 3389/tcp comment "OpenCanary RDP"
sudo ufw allow 5900/tcp comment "OpenCanary VNC"
sudo ufw allow 161/udp  comment "OpenCanary SNMP"

sudo ufw enable
sudo ufw status verbose
```

### 1.3 Install Docker

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER   # log out and back in after this
```

---

## Step 2 — Clone & Configure

```bash
git clone https://github.com/FBI-ZEZO03/NeuroTrap.git
cd NeuroTrap/neurotrap
cp .env.example .env
nano .env
```

### Required `.env` values

```bash
MONGO_USER=admin
MONGO_PASS=<strong-random-password-32-chars>
MONGO_URI=mongodb://admin:<MONGO_PASS>@mongodb:27017/neurotrap?authSource=admin
SECRET_KEY=<64-char-random-hex>
JWT_SECRET=<64-char-random-hex>
ADMIN_USER=admin
ADMIN_PASS=<strong-password>
ANALYST_USER=analyst
ANALYST_PASS=<strong-password>
MONITOR_INTERFACE=eth0   # replace with your primary NIC name
```

Generate random secrets:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Optional `.env` values

```bash
# Enable Galah LLM web honeypot
ANTHROPIC_API_KEY=sk-ant-...
GALAH_PROVIDER=anthropic
GALAH_MODEL=claude-opus-4-8

# Or use OpenAI instead
# OPENAI_API_KEY=sk-...
# GALAH_PROVIDER=openai

# Enable MFA for admin login
MFA_ENABLED=1
MFA_SECRET=<base32-totp-secret>   # generate: python3 -c "import pyotp; print(pyotp.random_base32())"

# Force SQLite (development only)
# NEUROTRAP_FORCE_FALLBACK=1
```

---

## Step 3 — Generate SSL Certificate

```bash
bash scripts/generate_ssl_cert.sh
```

This creates a self-signed certificate for Nginx. For production, replace with a CA-signed cert by mounting it into the nginx container.

---

## Step 4 — Launch the Stack

```bash
docker compose up -d
```

Wait ~30 seconds for all containers to start. Check health:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

All containers should show `Up` or `healthy`.

---

## Step 5 — Initialize the Database

```bash
docker compose exec api python scripts/setup_db_indexes.py
```

---

## Step 6 — Train the ML Classifier

Pre-trained models are already in `data/models/`. To retrain on your own captured sessions:

```bash
docker compose exec behavior-engine python -m src.behavior.train_classifier
```

---

## Step 7 — Open the Dashboard

```
https://<your-server-ip>
```

Accept the self-signed certificate warning. Default credentials:

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | value of `ADMIN_PASS` in `.env` |
| Analyst | `analyst` | value of `ANALYST_PASS` in `.env` |

> **Change the defaults immediately.** The factory defaults are in the env file; update `ADMIN_PASS` and `ANALYST_PASS` before exposing the server.

---

## Common Post-Install Operations

### Reload nginx after any API restart

nginx resolves the `api` upstream at startup. Always reload after restarting the API:

```bash
docker compose build api && docker compose up -d api
docker compose exec nginx nginx -s reload
```

### View live logs

```bash
docker logs -f neurotrap-cowrie      # live attacker SSH activity
docker logs -f neurotrap-monitor     # packet capture + ingestion events
docker logs -f neurotrap-api         # Flask request log
docker logs -f neurotrap-behavior    # ML classification events
```

### Force-recalculate all threat scores

```bash
curl -s -X POST http://localhost:5000/api/profiles/recalculate
```

### Enable Galah after deploy

```bash
echo "ANTHROPIC_API_KEY=sk-ant-..." >> .env
docker compose up -d galah
```

---

## Local Development (No Docker)

For quick iteration without the full stack:

```bash
cd neurotrap
pip install -r requirements/api.txt
NEUROTRAP_FORCE_FALLBACK=1 python -m src.api.app
# API on http://localhost:5000, SQLite at data/neurotrap.db
```

Source files (`src/`) and dashboard templates are bind-mounted into the API container during Docker deployment, so edits are picked up on the next request without rebuilding.

---

## Simulating an Attack

Run the built-in 5-stage attack simulation to verify the pipeline:

```bash
python scripts/simulate_attack.py
```

Stages: recon → brute-force → login + commands → malware upload → lateral movement.

After running, check the dashboard — you should see events, attacker profiles, and threat scores populated.

---

## Upgrading

```bash
git pull origin master
docker compose build
docker compose up -d
docker compose exec nginx nginx -s reload
```

---

## Uninstall

```bash
docker compose down -v          # stop containers and remove volumes
docker image prune -f           # remove unused images
```

> MongoDB data is stored in the `mongo-data` named volume. `down -v` will delete all captured attacker data permanently.
