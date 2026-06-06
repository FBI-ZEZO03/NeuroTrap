"""
app.py — Flask REST API + WebSocket server for the NeuroTrap management portal.
"""

from __future__ import annotations
import os
import time
import logging
from functools import wraps

from flask import Flask, jsonify, request, render_template, abort, redirect
from flask_socketio import SocketIO, emit

try:
    from flask_jwt_extended import (
        JWTManager, create_access_token, jwt_required, get_jwt_identity,
    )
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "../../dashboard/templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "../../dashboard/static"),
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET", "dev-jwt-change-me")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 3600

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


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if username != ADMIN_USER or password != ADMIN_PASS:
        return jsonify({"error": "Invalid credentials"}), 401

    if JWT_AVAILABLE:
        token = create_access_token(identity=username)
        return jsonify({"access_token": token})

    return jsonify({"access_token": "dev-token-no-jwt"})


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if JWT_AVAILABLE:
            return jwt_required()(f)(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("index.html")

# Legacy standalone routes now redirect into the single-page app (in-page nav).
@app.route("/cbee")
@app.route("/gadcf")
@app.route("/fhim")
@app.route("/ashrta")
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
@require_auth
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
def get_response_log():
    db = get_db()
    if db is None:
        return jsonify({"log": []})
    cursor = db["response_log"].find({}, {"_id": 0}).sort("timestamp", -1).limit(100)
    return jsonify({"log": list(cursor)})


# ── Deception environments API ────────────────────────────────────────────────

@app.route("/api/environments", methods=["GET"])
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


@app.route("/api/honeypots", methods=["GET"])
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
                hits = db["alert_events"].count_documents({"honeypot_source": sensor["name"]})
                latest = db["alert_events"].find_one(
                    {"honeypot_source": sensor["name"]}, {"_id": 0, "timestamp": 1}
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
                db["honeypot_sessions"].find({}, {"_id": 0}).sort("started_at", -1).limit(50)
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
            _get_fhim._instance = FedAvgServer(db if db else type("MockDB", (), {
                "__getitem__": lambda s,k: type("C",(),{"find":lambda *a,**kw:[],"insert_one":lambda *a:None,"update_one":lambda *a,**kw:None})()
            })())
        return _get_fhim._instance
    except Exception as e:
        return None

def _get_ashrta():
    try:
        from src.ashrta.red_agent import RedAgent
        from src.ashrta.hardening_optimizer import HardeningOptimizer, ASHRTAScheduler
        db = get_db()
        if not hasattr(_get_ashrta, "_instance"):
            mock_db = type("MockDB", (), {
                "__getitem__": lambda s,k: type("C",(),{
                    "find":lambda *a,**kw: type("Cur",(),{"sort":lambda *a,**kw:[],"limit":lambda *a:[]})(),
                    "insert_one":lambda *a:None,
                    "update_one":lambda *a,**kw:None,
                })()
            })()
            actual_db = db if db else mock_db
            agent = RedAgent()
            optimizer = HardeningOptimizer(actual_db)
            _get_ashrta._instance = ASHRTAScheduler(actual_db, agent, optimizer)
        return _get_ashrta._instance
    except Exception:
        return None


# ── CBEE API ──────────────────────────────────────────────────────────────────

@app.route("/api/cbee/profiles", methods=["GET"])
def get_cbee_profiles():
    cbee = _get_cbee()
    if cbee:
        return jsonify({"profiles": cbee.get_all_profiles()})
    # Demo data
    import math
    now = time.time()
    return jsonify({"profiles": [
        {"src_ip":"185.220.101.42","curiosity_gap":82,"confirmation_bias":45,"sunk_cost":67,"authority_signal":91,"scarcity_framing":38,"overall":64.6,"dominant":"authority_signal","updated_at":now-120},
        {"src_ip":"91.234.56.78","curiosity_gap":34,"confirmation_bias":78,"sunk_cost":22,"authority_signal":55,"scarcity_framing":89,"overall":55.6,"dominant":"scarcity_framing","updated_at":now-300},
        {"src_ip":"198.51.100.42","curiosity_gap":95,"confirmation_bias":12,"sunk_cost":45,"authority_signal":20,"scarcity_framing":18,"overall":38.0,"dominant":"curiosity_gap","updated_at":now-600},
    ]})

@app.route("/api/cbee/injections", methods=["GET"])
def get_cbee_injections():
    db = get_db()
    if db:
        docs = list(db["cbee_injections"].find({}, {"_id":0}).sort("created_at",-1).limit(20))
        return jsonify({"injections": docs})
    return jsonify({"injections": [
        {"injection_id":"f3a1b2c4","src_ip":"185.220.101.42","bias_trigger":"authority_signal","bias_score":64.6,"assets":[{"asset_type":"file"},{"asset_type":"file"}],"created_at":time.time()-90,"executed":True},
        {"injection_id":"a9d2e5f6","src_ip":"91.234.56.78","bias_trigger":"scarcity_framing","bias_score":55.6,"assets":[{"asset_type":"file"}],"created_at":time.time()-280,"executed":True},
    ]})

@app.route("/api/cbee/score", methods=["POST"])
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


# ── ASHRTA API ────────────────────────────────────────────────────────────────

@app.route("/api/ashrta/reports", methods=["GET"])
def get_ashrta_reports():
    ashrta = _get_ashrta()
    if ashrta:
        return jsonify({"reports": ashrta.get_reports()})
    return jsonify({"reports": [
        {"report_id":"r1a2b3","timestamp":time.time()-86400*3,"hardening_score":62.0,"checks_passed":6,"checks_total":10,"critical_weaknesses":2,"patches_generated":4,"patches_applied":4},
        {"report_id":"c4d5e6","timestamp":time.time()-86400*2,"hardening_score":75.0,"checks_passed":7,"checks_total":10,"critical_weaknesses":1,"patches_generated":3,"patches_applied":3},
        {"report_id":"f7g8h9","timestamp":time.time()-86400*1,"hardening_score":82.0,"checks_passed":8,"checks_total":10,"critical_weaknesses":0,"patches_generated":2,"patches_applied":2},
        {"report_id":"i0j1k2","timestamp":time.time()-3600,   "hardening_score":90.0,"checks_passed":9,"checks_total":10,"critical_weaknesses":0,"patches_generated":1,"patches_applied":1},
    ]})

@app.route("/api/ashrta/patches", methods=["GET"])
def get_ashrta_patches():
    ashrta = _get_ashrta()
    if ashrta:
        return jsonify({"patches": ashrta.optimizer.get_patch_history()})
    return jsonify({"patches": [
        {"patch_id":"p1","weakness":"ssh_banner_fingerprint","severity":"critical","config_target":"cowrie.cfg","before":"SSH-2.0-OpenSSH_6.0p1","after":"SSH-2.0-OpenSSH_9.3p1 Ubuntu-3ubuntu0.6","applied":True,"timestamp":time.time()-86400},
        {"patch_id":"p2","weakness":"timing_analysis","severity":"high","config_target":"cowrie.cfg","before":"response_delay = 0","after":"response_delay = 142","applied":True,"timestamp":time.time()-86400+60},
        {"patch_id":"p3","weakness":"filesystem_completeness","severity":"critical","config_target":"honeyfs","before":"entries = 120","after":"entries = 2800","applied":True,"timestamp":time.time()-86400+120},
        {"patch_id":"p4","weakness":"process_tree_plausibility","severity":"high","config_target":"cowrie.cfg","before":"processes = 15","after":"processes = 127","applied":True,"timestamp":time.time()-86400+180},
    ]})

@app.route("/api/ashrta/run", methods=["POST"])
def ashrta_run_cycle():
    ashrta = _get_ashrta()
    if ashrta:
        summary = ashrta.run_cycle()
        return jsonify(summary)
    # Demo run
    from src.ashrta.red_agent import RedAgent
    from src.ashrta.hardening_optimizer import HardeningOptimizer
    db_mock = type("MockDB", (), {"__getitem__": lambda s,k: type("C",(),{"insert_one":lambda *a:None,"update_one":lambda *a,**kw:None,"find":lambda *a,**kw:type("Cur",(),{"sort":lambda *a,**kw:[],"limit":lambda *a:[]})()})()})()
    agent     = RedAgent()
    optimizer = HardeningOptimizer(db_mock)
    report    = agent.run()
    patches   = optimizer.generate_patches(report)
    applied   = optimizer.apply_patches(patches)
    return jsonify({
        "report_id": report.report_id,
        "hardening_score": report.hardening_score,
        "checks_passed": report.checks_passed,
        "checks_total": report.checks_total,
        "critical_weaknesses": report.critical_weaknesses,
        "patches_generated": len(patches),
        "patches_applied": applied,
        "full_results": report.results,
    })


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
def soc_chat():
    data = request.get_json(silent=True) or {}
    soc = _get_soc()
    if soc is None:
        return jsonify({"answer": "Analyst offline.", "source": "heuristic"})
    return jsonify(soc.answer_question(data.get("question", "")))


# ── WebSocket live feed ───────────────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    logger.info("Dashboard client connected: %s", request.sid)
    emit("connected", {"message": "Connected to NeuroTrap live feed"})


@socketio.on("subscribe_events")
def handle_subscribe(data=None):
    emit("subscribed", {"channel": "events"})


def broadcast_event(event: dict):
    """Called by detection pipeline to push events to dashboard in real-time."""
    socketio.emit("new_event", event, namespace="/")


def broadcast_profile_update(profile_dict: dict):
    """Called by behavior engine to push attacker profile updates."""
    socketio.emit("profile_update", profile_dict, namespace="/")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
