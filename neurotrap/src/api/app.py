"""
app.py — Flask REST API + WebSocket server for the NeuroTrap management portal.
"""

from __future__ import annotations
import os
import time
import logging
import urllib.request
import json as _json
from functools import wraps

from flask import Flask, jsonify, request, render_template, abort, redirect
from flask_socketio import SocketIO, emit

try:
    from flask_jwt_extended import (
        JWTManager, create_access_token, jwt_required, get_jwt_identity,
        get_jwt,
    )
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

try:
    import pyotp
    PYOTP_AVAILABLE = True
except ImportError:
    PYOTP_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── In-memory response cache ───────────────────────────────────────────────────
_CACHE: dict = {}
_CACHE_TTL = 30  # seconds

def _cache_get(key: str):
    entry = _CACHE.get(key)
    if entry and (time.time() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None

def _cache_set(key: str, data):
    _CACHE[key] = (data, time.time())
    return data

def cached(key: str):
    """Decorator: serve cached JSON. Cache key includes query string so different
    limit/filter params get their own entry."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            qs  = request.query_string.decode()
            ck  = f"{key}?{qs}" if qs else key
            hit = _cache_get(ck)
            if hit is not None:
                return jsonify(hit)
            result = fn(*args, **kwargs)
            try:
                _cache_set(ck, result.get_json())
            except Exception:
                pass
            return result
        return wrapper
    return decorator

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "../../dashboard/templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "../../dashboard/static"),
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "dev-jwt-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

if JWT_AVAILABLE:
    jwt = JWTManager(app)

# ── DB connection ──────────────────────────────────────────────────────────────
# Delegates to the central data layer: MongoDB when reachable, otherwise the
# embedded SQLite fallback. Returns None only if even the fallback fails to
# initialise, in which case routes serve their built-in demo data.

def get_db():
    try:
        from src.db import get_db as _get_db
        return _get_db()
    except Exception:
        return None


# ── Auth ───────────────────────────────────────────────────────────────────────

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "neurotrap2024")

ANALYST_USER = os.getenv("ANALYST_USER", "analyst")
ANALYST_PASS = os.getenv("ANALYST_PASS", "analyst2024")

# username → {password, role}
USERS = {
    ADMIN_USER:   {"password": ADMIN_PASS,   "role": "admin"},
    ANALYST_USER: {"password": ANALYST_PASS, "role": "analyst"},
}

# When MFA_ENABLED=1, every login requires a valid TOTP code.
# The secret is read from MFA_SECRET (base32). Generate one with:
#   python -c "import pyotp; print(pyotp.random_base32())"
# then set MFA_SECRET=<value> in .env and scan the QR from /api/auth/otp/setup.
MFA_ENABLED = os.getenv("MFA_ENABLED", "0") == "1"
MFA_SECRET  = os.getenv("MFA_SECRET", "")


def _verify_totp(code: str) -> bool:
    """Return True if code is a valid current TOTP for MFA_SECRET."""
    if not PYOTP_AVAILABLE or not MFA_SECRET:
        return False
    totp = pyotp.TOTP(MFA_SECRET)
    return totp.verify(code, valid_window=1)


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    user = USERS.get(username)
    if not user or user["password"] != password:
        return jsonify({"error": "Invalid credentials"}), 401

    if MFA_ENABLED and user["role"] == "admin":
        otp_code = data.get("otp", "")
        if not otp_code:
            return jsonify({"error": "OTP required", "mfa_required": True}), 401
        if not _verify_totp(otp_code):
            return jsonify({"error": "Invalid OTP code"}), 401

    role = user["role"]
    if JWT_AVAILABLE:
        token = create_access_token(identity=username, additional_claims={"role": role})
        return jsonify({"access_token": token, "role": role, "mfa_enabled": MFA_ENABLED})

    return jsonify({"access_token": "dev-token-no-jwt", "role": role, "mfa_enabled": MFA_ENABLED})


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if JWT_AVAILABLE:
            return jwt_required()(f)(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if JWT_AVAILABLE:
            @jwt_required()
            def inner(*a, **kw):
                claims = get_jwt()
                if claims.get("role") != "admin":
                    return jsonify({"error": "Admin access required"}), 403
                return f(*a, **kw)
            return inner(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated


@app.route("/api/auth/otp/setup", methods=["GET"])
@require_admin
def otp_setup():
    """Return a new TOTP secret + provisioning URI for first-time setup.

    If MFA_SECRET is already set in .env, returns the existing secret's URI
    (idempotent). The caller should display the URI as a QR code and then
    set MFA_SECRET + MFA_ENABLED=1 in .env and restart the API container.
    """
    if not PYOTP_AVAILABLE:
        return jsonify({"error": "pyotp not installed in this environment"}), 500

    secret = MFA_SECRET if MFA_SECRET else pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri  = totp.provisioning_uri(name=ADMIN_USER, issuer_name="NeuroTrap")

    try:
        import qrcode, io, base64
        img = qrcode.make(uri)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        qr_b64 = None

    return jsonify({
        "secret": secret,
        "provisioning_uri": uri,
        "qr_png_base64": qr_b64,
        "instructions": (
            "1. Scan the QR code (or enter the secret) in your authenticator app. "
            "2. Add MFA_SECRET=<secret> and MFA_ENABLED=1 to .env. "
            "3. Restart the API container: docker compose restart api. "
            "4. Future logins will require the 6-digit TOTP code in the 'otp' field."
        ),
    })


@app.route("/api/auth/otp/verify", methods=["POST"])
def otp_verify():
    """Verify a TOTP code without a full login (useful for UI pre-check)."""
    if not PYOTP_AVAILABLE:
        return jsonify({"error": "pyotp not installed"}), 500
    data = request.get_json(silent=True) or {}
    code = data.get("otp", "")
    if not code:
        return jsonify({"valid": False, "error": "otp field required"}), 400
    valid = _verify_totp(code)
    return jsonify({"valid": valid})


@app.route("/api/auth/mfa/status", methods=["GET"])
def mfa_status():
    """Public endpoint — lets the login UI know whether MFA is required."""
    return jsonify({"mfa_enabled": MFA_ENABLED, "mfa_configured": bool(MFA_SECRET)})


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("index.html")

# Legacy standalone routes now redirect into the single-page app (in-page nav).
@app.route("/cbee")
@app.route("/gadcf")
@app.route("/fhim")
@app.route("/soc")
def legacy_pages():
    return redirect("/")


# ── Events API ────────────────────────────────────────────────────────────────

@app.route("/api/events", methods=["GET"])
def get_events():
    db = get_db()
    limit = min(int(request.args.get("limit", 100)), 500)
    offset = int(request.args.get("offset", 0))
    attack_type = request.args.get("attack_type")
    severity = request.args.get("severity")

    query = {}
    if attack_type:
        query["attack_type"] = attack_type
    if severity:
        query["severity"] = severity

    if db is None:
        return jsonify({"events": [], "total": 0})

    total = db["alert_events"].count_documents(query)
    cursor = db["alert_events"].find(query, {"_id": 0}).sort("timestamp", -1).skip(offset).limit(limit)
    return jsonify({"events": list(cursor), "total": total})


@app.route("/api/events/stats", methods=["GET"])
@cached("events_stats")
def get_stats():
    db = get_db()
    if db is None:
        return jsonify({})

    pipeline = [
        {"$group": {
            "_id": "$attack_type",
            "count": {"$sum": 1},
            "avg_severity_score": {"$avg": {
                "$switch": {
                    "branches": [
                        {"case": {"$eq": ["$severity", "critical"]}, "then": 4},
                        {"case": {"$eq": ["$severity", "high"]}, "then": 3},
                        {"case": {"$eq": ["$severity", "medium"]}, "then": 2},
                    ],
                    "default": 1,
                }
            }},
        }},
        {"$sort": {"count": -1}},
    ]
    stats = list(db["alert_events"].aggregate(pipeline))
    total_events = db["alert_events"].count_documents({})
    # Count unique attacker IPs seen in the last 5 minutes from alert_events.
    # This is more reliable than querying attacker_profiles.last_seen, which can
    # be None/empty when profiles are loaded from an older DB document.
    try:
        recent_ips = db["alert_events"].aggregate([
            {"$match": {"timestamp": {"$gte": time.time() - 3600}}},
            {"$group": {"_id": "$src_ip"}},
        ])
        active_sessions = len(list(recent_ips))
    except Exception:
        active_sessions = 0
    blocked_ips = db["response_log"].count_documents({"action": "block_emergency"})

    return jsonify({
        "total_events": total_events,
        "active_sessions": active_sessions,
        "blocked_ips": blocked_ips,
        "by_attack_type": stats,
    })


# ── Attacker profiles API ──────────────────────────────────────────────────────

@app.route("/api/attackers", methods=["GET"])
@cached("attackers")
def get_attackers():
    db = get_db()
    if db is None:
        return jsonify({"attackers": []})

    limit = min(int(request.args.get("limit", 50)), 200)
    cursor = db["attacker_profiles"].find({}, {"_id": 0}).sort("threat_score", -1).limit(limit)
    return jsonify({"attackers": list(cursor)})


@app.route("/api/attackers/<src_ip>", methods=["GET"])
def get_attacker(src_ip: str):
    db = get_db()
    if db is None:
        return jsonify({})

    profile = db["attacker_profiles"].find_one({"src_ip": src_ip}, {"_id": 0})
    if not profile:
        abort(404, description=f"No profile found for {src_ip}")
    return jsonify(profile)


# ── Response API ───────────────────────────────────────────────────────────────

@app.route("/api/response/block", methods=["POST"])
@require_admin
def manual_block():
    data = request.get_json(silent=True) or {}
    src_ip = data.get("src_ip", "")
    if not src_ip:
        return jsonify({"error": "src_ip required"}), 400

    import subprocess
    try:
        subprocess.run(
            ["iptables", "-I", "INPUT", "-s", src_ip, "-j", "DROP"],
            check=True, timeout=5, capture_output=True,
        )
        status = "blocked"
    except Exception:
        status = "mock_blocked"

    db = get_db()
    if db:
        db["response_log"].insert_one({
            "action": "manual_block",
            "src_ip": src_ip,
            "timestamp": time.time(),
            "actor": "admin",
        })

    return jsonify({"status": status, "src_ip": src_ip})


@app.route("/api/response/log", methods=["GET"])
@cached("response_log")
def get_response_log():
    db = get_db()
    if db is None:
        return jsonify({"log": []})
    cursor = db["response_log"].find({}, {"_id": 0}).sort("timestamp", -1).limit(100)
    return jsonify({"log": list(cursor)})


# ── Deception environments API ────────────────────────────────────────────────

@app.route("/api/environments", methods=["GET"])
@cached("environments")
def get_environments():
    db = get_db()
    if db is None:
        return jsonify({"environments": []})
    cursor = db["deception_environments"].find(
        {"is_active": True}, {"_id": 0}
    ).sort("created_at", -1).limit(50)
    return jsonify({"environments": list(cursor)})


# ── Honeypots API ──────────────────────────────────────────────────────────────

# Default native honeypot sensors and the host ports they listen on.
HONEYPOT_SENSORS = [
    {"name": "ssh",    "protocol": "SSH",    "port": 22},
    {"name": "http",   "protocol": "HTTP",   "port": 80},
    {"name": "ftp",    "protocol": "FTP",    "port": 21},
    {"name": "telnet", "protocol": "Telnet", "port": 23},
]


@app.route("/api/honeypots/sessions/<src_ip>", methods=["GET"])
def get_honeypot_ip_detail(src_ip):
    """All sessions + alert events for a specific attacker IP."""
    db = get_db()
    sessions, events = [], []
    if db is not None:
        try:
            sessions = list(
                db["cowrie_sessions"].find({"src_ip": src_ip}, {"_id": 0})
                .sort("start_time", -1).limit(100)
            )
        except Exception:
            sessions = []
        try:
            events = list(
                db["alert_events"].find({"src_ip": src_ip}, {"_id": 0})
                .sort("timestamp", -1).limit(200)
            )
        except Exception:
            events = []

    all_commands = []
    for s in sessions:
        for cmd in s.get("commands", []):
            all_commands.append({"cmd": cmd, "session_id": s.get("session_id"), "time": s.get("start_time")})

    usernames  = list({s.get("username") for s in sessions if s.get("username")})
    passwords  = list({s.get("password") for s in sessions if s.get("password")})
    attack_types = list({e.get("attack_type") for e in events if e.get("attack_type")})
    ports_hit  = list({e.get("dst_port") for e in events if e.get("dst_port")})

    return jsonify({
        "src_ip": src_ip,
        "session_count": len(sessions),
        "event_count": len(events),
        "usernames_tried": usernames,
        "passwords_tried": passwords,
        "attack_types": attack_types,
        "ports_hit": ports_hit,
        "sessions": sessions,
        "events": events[:50],
        "all_commands": all_commands,
    })


@app.route("/api/honeypots", methods=["GET"])
@cached("honeypots")
def get_honeypots():
    """Per-sensor capture counts plus a roll-up of unique attacker IPs."""
    db = get_db()
    sensors = []
    unique_ips: set = set()
    total_hits = 0

    for sensor in HONEYPOT_SENSORS:
        hits = 0
        last_seen = None
        if db is not None:
            try:
                hits = db["alert_events"].count_documents({"dst_port": sensor["port"]})
                latest = db["alert_events"].find_one(
                    {"dst_port": sensor["port"]}, {"_id": 0, "timestamp": 1},
                    sort=[("timestamp", -1)],
                )
                last_seen = latest.get("timestamp") if latest else None
            except Exception:
                hits = 0
        total_hits += hits
        sensors.append({**sensor, "hits": hits, "last_seen": last_seen,
                        "status": "online"})

    sessions = []
    if db is not None:
        try:
            sessions = list(
                db["cowrie_sessions"].find({}, {"_id": 0}).sort("start_time", -1).limit(50)
            )
            unique_ips = {s.get("src_ip") for s in sessions if s.get("src_ip")}
        except Exception:
            sessions = []

    return jsonify({
        "sensors": sensors,
        "total_hits": total_hits,
        "unique_attackers": len(unique_ips),
        "recent_sessions": sessions,
    })


# ── Innovation modules (lazy-loaded, graceful if not importable) ──────────────

def _get_cbee():
    try:
        from src.cbee.cbee_engine import CBEEEngine
        db = get_db()
        if db is None:
            return None
        if not hasattr(_get_cbee, "_instance"):
            _get_cbee._instance = CBEEEngine(db)
        return _get_cbee._instance
    except Exception:
        return None

def _get_soc():
    """AI SOC Analyst engine. Returns an instance even when db is None so it can
    serve heuristic/demo output (LLM used automatically when ANTHROPIC_API_KEY set)."""
    try:
        from src.soc_analyst import SOCAnalyst
        return SOCAnalyst(get_db(), use_llm=True)
    except Exception:
        return None

def _get_gadcf():
    try:
        from src.gadcf.gadcf_engine import GADCFEngine
        db = get_db()
        if db is None:
            return None
        if not hasattr(_get_gadcf, "_instance"):
            _get_gadcf._instance = GADCFEngine(db, use_llm=False)
        return _get_gadcf._instance
    except Exception:
        return None

def _get_fhim():
    try:
        from src.fhim.aggregation_server import FedAvgServer
        db = get_db()
        if not hasattr(_get_fhim, "_instance"):
            _get_fhim._instance = FedAvgServer(db if db is not None else type("MockDB", (), {
                "__getitem__": lambda s,k: type("C",(),{"find":lambda *a,**kw:[],"insert_one":lambda *a:None,"update_one":lambda *a,**kw:None})()
            })())
        return _get_fhim._instance
    except Exception as e:
        return None

# ── CBEE API ──────────────────────────────────────────────────────────────────

@app.route("/api/cbee/profiles", methods=["GET"])
def get_cbee_profiles():
    cbee = _get_cbee()
    if cbee is not None:
        profiles = cbee.get_all_profiles()
        # Auto-score any attacker profiles that don't have a bias profile yet
        if not profiles:
            try:
                from src.cbee.bias_scorer import BiasScorer
                scorer = BiasScorer()
                db = get_db()
                if db is not None:
                    for ap in db["attacker_profiles"].find({}, {"_id": 0}).limit(20):
                        session_data = {
                            "commands": [s.get("commands", []) for s in ap.get("sessions", [])],
                            "duration_secs": ap.get("total_commands", 1) * 8,
                            "login_attempts": ap.get("session_count", 1),
                        }
                        session_data["commands"] = [c for sub in session_data["commands"] for c in sub]
                        scored = scorer.score(session_data)
                        cbee.db["cbee_profiles"].update_one(
                            {"src_ip": ap["src_ip"]},
                            {"$set": {**scored.to_dict(), "src_ip": ap["src_ip"], "updated_at": time.time()}},
                            upsert=True,
                        )
                    profiles = cbee.get_all_profiles()
            except Exception as exc:
                logger.warning("CBEE auto-score failed: %s", exc)
        return jsonify({"profiles": profiles})
    # Demo data fallback
    now = time.time()
    return jsonify({"profiles": [
        {"src_ip":"185.220.101.42","curiosity_gap":82,"confirmation_bias":45,"sunk_cost":67,"authority_signal":91,"scarcity_framing":38,"overall":64.6,"dominant":"authority_signal","updated_at":now-120},
        {"src_ip":"91.234.56.78","curiosity_gap":34,"confirmation_bias":78,"sunk_cost":22,"authority_signal":55,"scarcity_framing":89,"overall":55.6,"dominant":"scarcity_framing","updated_at":now-300},
        {"src_ip":"198.51.100.42","curiosity_gap":95,"confirmation_bias":12,"sunk_cost":45,"authority_signal":20,"scarcity_framing":18,"overall":38.0,"dominant":"curiosity_gap","updated_at":now-600},
    ]})

@app.route("/api/cbee/injections", methods=["GET"])
def get_cbee_injections():
    db = get_db()
    if db is not None:
        docs = list(db["cbee_injections"].find({}, {"_id":0}).sort("created_at",-1).limit(20))
        return jsonify({"injections": docs})
    return jsonify({"injections": [
        {"injection_id":"f3a1b2c4","src_ip":"185.220.101.42","bias_trigger":"authority_signal","bias_score":64.6,"assets":[{"asset_type":"file"},{"asset_type":"file"}],"created_at":time.time()-90,"executed":True},
        {"injection_id":"a9d2e5f6","src_ip":"91.234.56.78","bias_trigger":"scarcity_framing","bias_score":55.6,"assets":[{"asset_type":"file"}],"created_at":time.time()-280,"executed":True},
    ]})

@app.route("/api/cbee/score", methods=["POST"])
@require_admin
def score_session_bias():
    data = request.get_json(silent=True) or {}
    try:
        from src.cbee.bias_scorer import BiasScorer
        scorer = BiasScorer()
        profile = scorer.score(data)
        return jsonify(profile.to_dict())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── GADCF API ─────────────────────────────────────────────────────────────────

@app.route("/api/gadcf/assets", methods=["GET"])
def get_gadcf_assets():
    gadcf = _get_gadcf()
    if gadcf:
        return jsonify({"assets": gadcf.get_recent_generations()})
    return jsonify({"assets": [
        {"asset_type":"env_file","filename":".env.financial-services.production","industry":"financial_services","attacker_intent":"credential_harvesting","source":"template","generated_at":time.time()-300},
        {"asset_type":"email_thread","filename":"IT_thread_a3f2.eml","industry":"financial_services","attacker_intent":"credential_harvesting","source":"template","generated_at":time.time()-290},
        {"asset_type":"code_repo","filename":"app_b4c1.py","industry":"saas_startup","attacker_intent":"malware_deployment","source":"template","generated_at":time.time()-180},
        {"asset_type":"wiki_page","filename":"RUNBOOK_SAAS_STARTUP_d2e3.md","industry":"saas_startup","attacker_intent":"malware_deployment","source":"template","generated_at":time.time()-170},
        {"asset_type":"db_schema","filename":"schema_dump_e5f4.sql","industry":"financial_services","attacker_intent":"credential_harvesting","source":"template","generated_at":time.time()-150},
    ]})

@app.route("/api/gadcf/generate", methods=["POST"])
@require_admin
def gadcf_generate():
    data = request.get_json(silent=True) or {}
    try:
        from src.gadcf.content_generator import ContentGenerator
        gen    = ContentGenerator(use_llm=False)
        assets = gen.generate_package(
            industry=data.get("industry","saas_startup"),
            attacker_intent=data.get("intent","reconnaissance"),
            sophistication=data.get("sophistication","beginner"),
        )
        return jsonify({"assets": [a.to_dict() for a in assets], "count": len(assets)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── FHIM API ──────────────────────────────────────────────────────────────────

@app.route("/api/fhim/nodes", methods=["GET"])
def get_fhim_nodes():
    fhim = _get_fhim()
    if fhim:
        return jsonify({"nodes": fhim.get_node_status(), "global_f1": fhim.get_global_f1()})
    return jsonify({"nodes": [], "global_f1": 0.88})

@app.route("/api/fhim/rounds", methods=["GET"])
def get_fhim_rounds():
    fhim = _get_fhim()
    rounds = fhim.get_round_history() if fhim else []
    return jsonify({"rounds": rounds})


# ── ADT — Attacker Digital Twin API (Innovation 05) ───────────────────────────

def _get_adt():
    try:
        from src.twin.digital_twin import AttackerDigitalTwin
        db = get_db()
        if db is None:
            return None
        if not hasattr(_get_adt, "_instance"):
            _get_adt._instance = AttackerDigitalTwin(db)
        return _get_adt._instance
    except Exception:
        return None


def _demo_twins():
    from src.twin.kill_chain import build_kill_chain
    now = time.time()
    return [{
        "src_ip": "185.220.101.42", "attacker_tier": "advanced_human",
        "classified_intent": "credential_harvesting", "threat_score": 92.0,
        "observation_count": 38, "confidence": 0.86, "automation_score": 30.0,
        "sophistication": 84.0, "first_seen": now - 7200, "last_seen": now - 120,
        "honeypots_touched": ["ssh", "http", "ftp"],
        "countries": ["RU"], "tools": ["Hydra", "sqlmap", "wget"],
        "tactics_observed": ["Discovery", "Credential Access", "Lateral Movement", "Exfiltration"],
        "tactic_sequence": ["Discovery", "Credential Access", "Lateral Movement", "Exfiltration"],
        "technique_ids": ["T1110", "T1003.008", "T1021.004"],
        "kill_chain": build_kill_chain(
            ["Discovery", "Credential Access", "Lateral Movement", "Exfiltration"]),
        "psychology": {"dominant": "authority_signal", "overall": 64.6},
        "predicted_next": [
            {"tactic": "Impact", "probability": 0.5, "technique_id": "T1486",
             "technique_name": "Data Encrypted for Impact", "kill_chain_stage": "Actions on Objectives"},
            {"tactic": "Command and Control", "probability": 0.25, "technique_id": "T1105",
             "technique_name": "Ingress Tool Transfer", "kill_chain_stage": "Command & Control"},
        ],
        "recommendation": {"suggested_env_tier": "advanced_human", "anticipated_tactic": "Impact",
                           "action": "Throttle + snapshot the environment; deploy a believable but inert target.",
                           "bias_lever": "authority_signal", "urgency": "high"},
        "fidelity": 0.71, "predictions_made": 12, "predictions_hit": 8,
    }, {
        "src_ip": "91.234.56.78", "attacker_tier": "automated_bot",
        "classified_intent": "malware_deployment", "threat_score": 64.0,
        "observation_count": 21, "confidence": 0.74, "automation_score": 90.0,
        "sophistication": 52.0, "first_seen": now - 3600, "last_seen": now - 40,
        "honeypots_touched": ["telnet", "ssh"], "countries": ["CN"],
        "tools": ["Mirai", "BusyBox", "wget"],
        "tactics_observed": ["Discovery", "Execution", "Command and Control"],
        "tactic_sequence": ["Discovery", "Execution", "Command and Control"],
        "technique_ids": ["T1105", "T1059"],
        "kill_chain": build_kill_chain(
            ["Discovery", "Execution", "Command and Control"]),
        "psychology": {}, "predicted_next": [
            {"tactic": "Exfiltration", "probability": 0.3, "technique_id": "T1041",
             "technique_name": "Exfiltration Over C2 Channel", "kill_chain_stage": "Actions on Objectives"},
            {"tactic": "Impact", "probability": 0.25, "technique_id": "T1496",
             "technique_name": "Resource Hijacking", "kill_chain_stage": "Actions on Objectives"},
        ],
        "recommendation": {"suggested_env_tier": "automated_bot", "anticipated_tactic": "Exfiltration",
                           "action": "Plant beaconing canary documents to attribute and track stolen data.",
                           "bias_lever": None, "urgency": "high"},
        "fidelity": 0.83, "predictions_made": 6, "predictions_hit": 5,
    }]


@app.route("/api/twin/list", methods=["GET"])
def twin_list():
    adt = _get_adt()
    if adt:
        twins = adt.list_twins(limit=int(request.args.get("limit", 50)))
        if twins:
            return jsonify({"twins": twins, "count": len(twins), "source": "live"})
    return jsonify({"twins": _demo_twins(), "count": 2, "source": "demo"})


@app.route("/api/twin/<src_ip>", methods=["GET"])
def twin_detail(src_ip: str):
    adt = _get_adt()
    if adt:
        twin = adt.get_twin(src_ip)
        if twin:
            return jsonify(twin)
    for t in _demo_twins():
        if t["src_ip"] == src_ip:
            return jsonify(t)
    abort(404, description=f"No twin for {src_ip}")


@app.route("/api/twin/build", methods=["POST"])
@require_admin
def twin_build():
    adt = _get_adt()
    if not adt:
        return jsonify({"error": "twin engine unavailable"}), 503
    data = request.get_json(silent=True) or {}
    src_ip = data.get("src_ip")
    if src_ip:
        twin = adt.build_twin(src_ip)
        return jsonify(twin.to_dict())
    twins = adt.build_all()
    return jsonify({"built": len(twins), "twins": [t.to_dict() for t in twins]})


@app.route("/api/twin/simulate", methods=["POST"])
@require_admin
def twin_simulate():
    data = request.get_json(silent=True) or {}
    steps = min(int(data.get("steps", 5)), 12)
    src_ip = data.get("src_ip")
    tactics = data.get("tactics")

    # Path 1: simulate a live/persisted twin.
    adt = _get_adt()
    if adt and src_ip:
        twin_doc = adt.get_twin(src_ip)
        if twin_doc:
            from src.twin.digital_twin import DigitalTwin
            twin = DigitalTwin(**{k: v for k, v in twin_doc.items()
                                  if k in DigitalTwin.__dataclass_fields__})
            return jsonify({"src_ip": src_ip,
                            "current": twin.tactic_sequence[-1] if twin.tactic_sequence else None,
                            "forecast": adt.simulate(twin, steps=steps)})

    # Path 2: ad-hoc simulation from a supplied tactic sequence (works offline).
    try:
        from src.twin.predictor import TacticPredictor
        seq = tactics if isinstance(tactics, list) else ["Discovery"]
        predictor = TacticPredictor(seq)
        forecast = predictor.simulate_forward(seq[-1] if seq else None, steps=steps,
                                               seed=int(data.get("seed", 42)))
        return jsonify({"current": seq[-1] if seq else None, "forecast": forecast})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI SOC Analyst API (Innovation 06) ─────────────────────────────────────────

@app.route("/api/soc/summary", methods=["GET"])
def soc_summary():
    soc = _get_soc()
    if soc is None:
        return jsonify({"actors_tracked": 0, "by_risk": {}, "needs_action": 0,
                        "headline": "Analyst offline.", "llm_enabled": False})
    return jsonify(soc.summary(hours=int(request.args.get("hours", 24))))


@app.route("/api/soc/triage", methods=["GET"])
def soc_triage():
    soc = _get_soc()
    limit = min(int(request.args.get("limit", 15)), 100)
    return jsonify({"queue": soc.triage_queue(limit) if soc else []})


@app.route("/api/soc/reports", methods=["GET"])
def soc_reports():
    soc = _get_soc()
    return jsonify({"reports": soc.get_recent_reports() if soc else []})


@app.route("/api/soc/report", methods=["POST"])
@require_admin
def soc_report():
    data = request.get_json(silent=True) or {}
    src_ip = (data.get("src_ip") or "").strip()
    if not src_ip:
        return jsonify({"error": "src_ip required"}), 400
    soc = _get_soc()
    if soc is None:
        return jsonify({"error": "analyst unavailable"}), 503
    return jsonify(soc.generate_report(src_ip))


@app.route("/api/soc/chat", methods=["POST"])
@require_admin
def soc_chat():
    data = request.get_json(silent=True) or {}
    soc = _get_soc()
    if soc is None:
        return jsonify({"answer": "Analyst offline.", "source": "heuristic"})
    return jsonify(soc.answer_question(data.get("question", "")))


# ── Threat Intelligence API ───────────────────────────────────────────────────

def _resolve_countries(db, ips: list[str]) -> dict[str, str]:
    """Batch-resolve countries for IPs that have no country set yet.
    Uses ip-api.com free batch endpoint (no key, max 100 IPs).
    Results are cached back into attacker_profiles immediately.
    """
    if not ips:
        return {}
    resolved: dict[str, str] = {}
    try:
        payload = _json.dumps([{"query": ip, "fields": "query,country"} for ip in ips[:100]]).encode()
        req = urllib.request.Request(
            "http://ip-api.com/batch?fields=query,country",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            results = _json.loads(resp.read())
        for r in results:
            country = (r.get("country") or "Unknown").replace("The Netherlands", "Netherlands")
            ip = r.get("query", "")
            if ip:
                resolved[ip] = country
                try:
                    db["attacker_profiles"].update_one(
                        {"src_ip": ip}, {"$set": {"country": country}}
                    )
                except Exception:
                    pass
    except Exception as exc:
        logger.warning("GeoIP batch lookup failed: %s", exc)
    return resolved


@app.route("/api/intel", methods=["GET"])
@cached("intel")
def get_threat_intel():
    db = get_db()
    now = time.time()

    if db is None:
        return jsonify({
            "iocs": [],
            "top_countries": [],
            "top_ports": [],
            "attack_type_dist": [],
            "campaigns": [],
            "summary": {"total_iocs": 0, "countries_seen": 0, "active_campaigns": 0, "top_threat": "N/A"},
        })

    # IOC list — top attacker IPs by threat score
    iocs = []
    try:
        profiles = list(db["attacker_profiles"].find({}, {"_id": 0}).sort("threat_score", -1).limit(50))

        # Resolve countries for any IP that still has none
        unresolved = [p["src_ip"] for p in profiles if not p.get("country")]
        if unresolved:
            geo = _resolve_countries(db, unresolved)
            for p in profiles:
                if not p.get("country") and p["src_ip"] in geo:
                    p["country"] = geo[p["src_ip"]]

        for p in profiles:
            iocs.append({
                "ip": p.get("src_ip", ""),
                "threat_score": p.get("threat_score", 0),
                "intent": p.get("classified_intent", "unknown"),
                "tier": p.get("attacker_tier", "unknown"),
                "country": p.get("country") or "Unknown",
                "first_seen": p.get("first_seen", now),
                "last_seen": p.get("last_seen", now),
                "session_count": p.get("session_count", 0),
                "ttp_count": len(p.get("ttps", [])),
                "is_blocked": p.get("is_blocked", False),
                "campaign_id": p.get("campaign_id", ""),
            })
    except Exception:
        pass

    # Top countries
    country_counts: dict = {}
    for ioc in iocs:
        c = ioc["country"] or "Unknown"
        country_counts[c] = country_counts.get(c, 0) + 1
    top_countries = sorted(
        [{"country": k, "count": v} for k, v in country_counts.items()],
        key=lambda x: x["count"], reverse=True
    )[:15]

    # Top targeted ports
    top_ports = []
    try:
        port_pipeline = [
            {"$group": {"_id": "$dst_port", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]
        for doc in db["alert_events"].aggregate(port_pipeline):
            if doc["_id"]:
                top_ports.append({"port": doc["_id"], "count": doc["count"]})
    except Exception:
        pass

    # Attack type distribution
    attack_dist = []
    try:
        for doc in db["alert_events"].aggregate([
            {"$group": {"_id": "$attack_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 8},
        ]):
            if doc["_id"]:
                attack_dist.append({"type": doc["_id"], "count": doc["count"]})
    except Exception:
        pass

    # Active campaigns
    campaigns = []
    try:
        camp_map: dict = {}
        for p in db["attacker_profiles"].find({"campaign_id": {"$ne": ""}}, {"_id": 0}):
            cid = p.get("campaign_id", "")
            if not cid:
                continue
            if cid not in camp_map:
                camp_map[cid] = {"campaign_id": cid, "actor_count": 0, "max_score": 0, "intents": set()}
            camp_map[cid]["actor_count"] += 1
            camp_map[cid]["max_score"] = max(camp_map[cid]["max_score"], p.get("threat_score", 0))
            camp_map[cid]["intents"].add(p.get("classified_intent", ""))
        for c in camp_map.values():
            c["intents"] = list(c["intents"])
            campaigns.append(c)
        campaigns.sort(key=lambda x: x["max_score"], reverse=True)
    except Exception:
        pass

    top_threat = iocs[0]["ip"] if iocs else "N/A"
    return jsonify({
        "iocs": iocs,
        "top_countries": top_countries,
        "top_ports": top_ports,
        "attack_type_dist": attack_dist,
        "campaigns": campaigns,
        "summary": {
            "total_iocs": len(iocs),
            "countries_seen": len(country_counts),
            "active_campaigns": len(campaigns),
            "top_threat": top_threat,
        },
    })


# ── WebSocket live feed ───────────────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    logger.info("Dashboard client connected: %s", request.sid)
    emit("connected", {"message": "Connected to NeuroTrap live feed"})


@socketio.on("subscribe_events")
def handle_subscribe(data=None):
    emit("subscribed", {"channel": "events"})


def broadcast_event(event: dict):
    socketio.emit("new_event", event, namespace="/")


def broadcast_profile_update(profile_dict: dict):
    socketio.emit("profile_update", profile_dict, namespace="/")


def _live_feed_poller():
    """Background thread: polls alert_events and attacker_profiles for new
    documents every 2 s and pushes them to connected dashboard clients."""
    import time as _time
    last_event_ts = _time.time()
    last_profile_ts = _time.time()

    while True:
        _time.sleep(2)
        try:
            db = get_db()

            # --- new alert events ---
            new_events = list(
                db["alert_events"].find(
                    {"timestamp": {"$gt": last_event_ts}},
                    {"_id": 0},
                ).sort("timestamp", 1).limit(50)
            )
            for ev in new_events:
                broadcast_event(ev)
                if ev.get("timestamp", 0) > last_event_ts:
                    last_event_ts = ev["timestamp"]

            # --- new / updated attacker profiles ---
            new_profiles = list(
                db["attacker_profiles"].find(
                    {"last_seen": {"$gt": last_profile_ts}},
                    {"_id": 0},
                ).sort("last_seen", 1).limit(20)
            )
            for prof in new_profiles:
                broadcast_profile_update(prof)
                if prof.get("last_seen", 0) > last_profile_ts:
                    last_profile_ts = prof["last_seen"]

        except Exception as exc:
            logger.debug("live_feed_poller error: %s", exc)


# Start the poller once (guarded so it doesn't double-start under reloader)
import os as _os
if not _os.environ.get("WERKZEUG_RUN_MAIN"):
    import threading as _threading
    _poller = _threading.Thread(target=_live_feed_poller, daemon=True, name="live-feed-poller")
    _poller.start()


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
