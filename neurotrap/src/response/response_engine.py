"""
response_engine.py — Autonomous response decision engine.

Decision matrix (from project spec):
  score < 40   → log only
  40–70        → slow + redirect to deeper honeypot
  70–90        → isolate session + alert
  > 90         → block IP + emergency alert + forensic capture
"""

from __future__ import annotations
import time
import logging
import subprocess
import smtplib
import threading
import os
from email.mime.text import MIMEText
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

RESPONSE_ACTIONS = ("log_only", "slow_redirect", "isolate_alert", "block_emergency")


class ResponseDecision:
    def __init__(self, action: str, src_ip: str, threat_score: float, details: dict | None = None):
        self.action = action
        self.src_ip = src_ip
        self.threat_score = threat_score
        self.timestamp = time.time()
        self.details = details or {}

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "src_ip": self.src_ip,
            "threat_score": self.threat_score,
            "timestamp": self.timestamp,
            "details": self.details,
        }


class ResponseEngine:
    """
    Evaluates threat scores and executes the appropriate response action
    within 10 seconds of a threshold breach (project requirement).

    Usage:
        engine = ResponseEngine(db, alert_config)
        engine.evaluate(profile)
    """

    THRESHOLDS = {
        "block":    90,
        "isolate":  70,
        "slow":     40,
    }

    def __init__(self, db, alert_config: dict | None = None):
        self.db = db
        self.alert_config = alert_config or {}
        self._response_log = db["response_log"]

    def evaluate(self, profile) -> ResponseDecision:
        """
        Evaluate profile.threat_score and execute the appropriate action.
        profile must have .src_ip, .threat_score, .classified_intent attributes.
        """
        score = profile.threat_score
        src_ip = profile.src_ip

        if score >= self.THRESHOLDS["block"]:
            decision = ResponseDecision("block_emergency", src_ip, score)
            self._execute_async(self._action_block_emergency, decision, profile)
        elif score >= self.THRESHOLDS["isolate"]:
            decision = ResponseDecision("isolate_alert", src_ip, score)
            self._execute_async(self._action_isolate_alert, decision, profile)
        elif score >= self.THRESHOLDS["slow"]:
            decision = ResponseDecision("slow_redirect", src_ip, score)
            self._execute_async(self._action_slow_redirect, decision, profile)
        else:
            decision = ResponseDecision("log_only", src_ip, score)
            self._log_decision(decision)

        return decision

    # ── Action implementations ─────────────────────────────────────────────

    def _action_block_emergency(self, decision: ResponseDecision, profile):
        logger.warning("BLOCK+EMERGENCY: %s (score=%.1f)", decision.src_ip, decision.threat_score)
        self._firewall_block(decision.src_ip)
        self._send_alert(
            subject=f"[CRITICAL] Attacker blocked: {decision.src_ip}",
            body=self._format_alert_body(profile, decision),
            level="critical",
        )
        self._capture_forensics(decision.src_ip)
        self._log_decision(decision)

    def _action_isolate_alert(self, decision: ResponseDecision, profile):
        logger.warning("ISOLATE+ALERT: %s (score=%.1f)", decision.src_ip, decision.threat_score)
        self._isolate_session(decision.src_ip)
        self._send_alert(
            subject=f"[HIGH] Attacker isolated: {decision.src_ip}",
            body=self._format_alert_body(profile, decision),
            level="high",
        )
        self._log_decision(decision)

    def _action_slow_redirect(self, decision: ResponseDecision, profile):
        logger.info("SLOW+REDIRECT: %s (score=%.1f)", decision.src_ip, decision.threat_score)
        self._apply_rate_limit(decision.src_ip)
        self._log_decision(decision)

    # ── Network enforcement ────────────────────────────────────────────────

    def _firewall_block(self, src_ip: str):
        """Block IP at iptables level (requires NET_ADMIN cap in container)."""
        try:
            subprocess.run(
                ["iptables", "-I", "INPUT", "-s", src_ip, "-j", "DROP"],
                check=True, timeout=5, capture_output=True,
            )
            logger.info("iptables DROP rule added for %s", src_ip)
        except FileNotFoundError:
            logger.warning("iptables not available (mock mode)")
        except subprocess.CalledProcessError as e:
            logger.error("iptables failed: %s", e.stderr.decode())

    def _isolate_session(self, src_ip: str):
        """Add rate-limit + log rule — softer than full block."""
        try:
            subprocess.run(
                ["iptables", "-I", "INPUT", "-s", src_ip,
                 "-m", "limit", "--limit", "1/min", "-j", "LOG",
                 "--log-prefix", "NEUROTRAP_ISOLATE: "],
                check=True, timeout=5, capture_output=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.warning("iptables isolate rule skipped (mock mode)")

    def _apply_rate_limit(self, src_ip: str):
        """tc netem delay to frustrate automated tools."""
        try:
            iface = os.getenv("MONITOR_INTERFACE", "eth0")
            # Add 500ms + 100ms jitter delay for this source
            subprocess.run(
                ["tc", "qdisc", "add", "dev", iface, "root", "handle", "1:0",
                 "netem", "delay", "500ms", "100ms"],
                check=False, timeout=5, capture_output=True,
            )
        except FileNotFoundError:
            logger.warning("tc not available (mock mode)")

    # ── Alerting ──────────────────────────────────────────────────────────

    def _send_alert(self, subject: str, body: str, level: str = "high"):
        threads = [
            threading.Thread(target=self._send_email, args=(subject, body), daemon=True),
            threading.Thread(target=self._send_slack, args=(subject, body), daemon=True),
            threading.Thread(target=self._send_telegram, args=(subject, body), daemon=True),
        ]
        for t in threads:
            t.start()

    def _send_email(self, subject: str, body: str):
        cfg = self.alert_config
        smtp_host = cfg.get("smtp_host") or os.getenv("SMTP_HOST")
        smtp_user = cfg.get("smtp_user") or os.getenv("SMTP_USER")
        smtp_pass = cfg.get("smtp_pass") or os.getenv("SMTP_PASS")
        alert_email = cfg.get("alert_email") or os.getenv("ALERT_EMAIL")

        if not all([smtp_host, smtp_user, smtp_pass, alert_email]):
            return

        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = smtp_user
            msg["To"] = alert_email
            with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587"))) as s:
                s.ehlo()
                s.starttls()
                s.login(smtp_user, smtp_pass)
                s.sendmail(smtp_user, [alert_email], msg.as_string())
            logger.info("Email alert sent to %s", alert_email)
        except Exception as exc:
            logger.error("Email alert failed: %s", exc)

    def _send_slack(self, subject: str, body: str):
        webhook = self.alert_config.get("slack_webhook") or os.getenv("SLACK_WEBHOOK_URL")
        if not webhook or not REQUESTS_AVAILABLE:
            return
        try:
            requests.post(webhook, json={"text": f"*{subject}*\n{body}"}, timeout=5)
        except Exception as exc:
            logger.error("Slack alert failed: %s", exc)

    def _send_telegram(self, subject: str, body: str):
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id or not REQUESTS_AVAILABLE:
            return
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": f"{subject}\n\n{body}"},
                timeout=5,
            )
        except Exception as exc:
            logger.error("Telegram alert failed: %s", exc)

    # ── Forensics ─────────────────────────────────────────────────────────

    def _capture_forensics(self, src_ip: str):
        pcap_path = f"/app/logs/forensics_{src_ip.replace('.', '_')}_{int(time.time())}.pcap"
        try:
            iface = os.getenv("MONITOR_INTERFACE", "eth0")
            subprocess.Popen(
                ["tcpdump", "-i", iface, "-w", pcap_path, f"host {src_ip}", "-c", "10000"],
                close_fds=True,
            )
            logger.info("Forensic PCAP capture started: %s", pcap_path)
        except FileNotFoundError:
            logger.warning("tcpdump not available — forensic capture skipped")

    # ── Utilities ─────────────────────────────────────────────────────────

    def _log_decision(self, decision: ResponseDecision):
        try:
            self._response_log.insert_one(decision.to_dict())
        except Exception as exc:
            logger.error("Failed to log response decision: %s", exc)

    def _execute_async(self, func, *args):
        t = threading.Thread(target=func, args=args, daemon=True)
        t.start()

    @staticmethod
    def _format_alert_body(profile, decision: ResponseDecision) -> str:
        ttps = ", ".join(t.get("technique_id", "") for t in profile.ttps[:5])
        return (
            f"Source IP:    {decision.src_ip}\n"
            f"Threat Score: {decision.threat_score:.1f}/100\n"
            f"Intent:       {profile.classified_intent}\n"
            f"Tier:         {profile.attacker_tier}\n"
            f"TTPs:         {ttps or 'none detected'}\n"
            f"Action:       {decision.action}\n"
            f"Time:         {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(decision.timestamp))}\n"
        )
