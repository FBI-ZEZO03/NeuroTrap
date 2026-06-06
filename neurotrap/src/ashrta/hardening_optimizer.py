"""
hardening_optimizer.py — Reads RedAgent weakness reports and auto-generates
configuration patches to fix detected honeypot tells.

Outputs YAML patches for the Deception Engine's config templates
and Cowrie configuration files.
"""

from __future__ import annotations
import time
import logging
import random
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class HardeningPatch:
    patch_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    weakness: str = ""
    severity: str = ""
    config_target: str = ""     # cowrie.cfg | env_template | honeyfs | network
    patch_type: str = ""        # value_change | file_add | command
    before: str = ""
    after: str = ""
    applied: bool = False
    verified: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class HardeningOptimizer:
    """
    Auto-generates configuration patches from RedAgent weakness reports.

    Usage:
        optimizer = HardeningOptimizer(db)
        patches = optimizer.generate_patches(red_agent_report)
        optimizer.apply_patches(patches)
    """

    def __init__(self, db):
        self.db = db

    def generate_patches(self, report) -> list[HardeningPatch]:
        patches: list[HardeningPatch] = []
        for result in (report.results if hasattr(report, 'results') else report.get('results', [])):
            if isinstance(result, dict):
                passed = result.get("passed", True)
                check  = result.get("check_name", "")
                sev    = result.get("severity", "low")
            else:
                passed = result.passed
                check  = result.check_name
                sev    = result.severity

            if not passed:
                patch = self._patch_for_weakness(check, sev)
                if patch:
                    patches.append(patch)
                    self._persist_patch(patch)

        logger.info("Generated %d hardening patches from report", len(patches))
        return patches

    def apply_patches(self, patches: list[HardeningPatch]) -> int:
        applied = 0
        for patch in patches:
            try:
                self._apply_patch(patch)
                patch.applied = True
                self._persist_patch(patch)
                applied += 1
            except Exception as exc:
                logger.error("Patch %s failed: %s", patch.patch_id, exc)
        logger.info("Applied %d/%d patches", applied, len(patches))
        return applied

    def get_patch_history(self, limit: int = 20) -> list[dict]:
        try:
            return list(self.db["ashrta_patches"].find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))
        except Exception:
            return []

    def get_hardening_trend(self) -> list[dict]:
        """Returns score history for dashboard chart."""
        try:
            return list(
                self.db["ashrta_reports"].find({}, {"_id": 0, "timestamp": 1, "hardening_score": 1})
                .sort("timestamp", -1).limit(20)
            )
        except Exception:
            return []

    # ── Patch generators ───────────────────────────────────────────────────────

    def _patch_for_weakness(self, check_name: str, severity: str) -> Optional[HardeningPatch]:
        patches = {
            "timing_analysis": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="cowrie.cfg",
                patch_type="value_change",
                before="response_delay = 0",
                after=f"response_delay = {random.randint(80, 180)}  # ms, randomized per check",
            ),
            "ssh_banner_fingerprint": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="cowrie.cfg",
                patch_type="value_change",
                before="version_string = SSH-2.0-OpenSSH_6.0p1",
                after=f"version_string = SSH-2.0-OpenSSH_9.{random.randint(1,6)}p1 Ubuntu-{random.randint(1,5)}ubuntu0.{random.randint(1,4)}",
            ),
            "os_fingerprint_consistency": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="env_template",
                patch_type="value_change",
                before='os_banner = "Ubuntu 20.04.6 LTS", kernel = "5.15.0-97-generic"',
                after='os_banner = "Ubuntu 22.04.4 LTS", kernel = "5.15.0-107-generic"',
            ),
            "filesystem_completeness": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="honeyfs",
                patch_type="file_add",
                before="filesystem_entries = 120",
                after="filesystem_entries = 2800  # expanded with /proc, /sys, /dev entries",
            ),
            "process_tree_plausibility": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="cowrie.cfg",
                patch_type="value_change",
                before="fake_process_count = 15",
                after="fake_process_count = 127  # systemd, kworker×40, rsyslog, cron, sshd×3, nginx, postgres...",
            ),
            "network_stack_fingerprint": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="network",
                patch_type="command",
                before="tcp_window_size = 65535",
                after="sysctl -w net.ipv4.tcp_window_scaling=1 && sysctl -w net.core.rmem_default=212992",
            ),
            "service_response_behavior": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="cowrie.cfg",
                patch_type="value_change",
                before='login_fail_msg = "Permission denied, please try again."',
                after='login_fail_msg = "Permission denied (publickey,password)."',
            ),
            "cpu_memory_artifacts": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="honeyfs",
                patch_type="file_add",
                before="/proc/loadavg = '0.00 0.00 0.00 1/312 1337'",
                after=f"/proc/loadavg = '{random.uniform(0.1,0.8):.2f} {random.uniform(0.1,0.6):.2f} {random.uniform(0.1,0.5):.2f} {random.randint(2,8)}/{random.randint(200,400)} {random.randint(1000,2000)}'",
            ),
            "uptime_consistency": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="honeyfs",
                patch_type="value_change",
                before="fake_uptime_days = 0",
                after=f"fake_uptime_days = {random.randint(45, 120)}",
            ),
            "error_message_authenticity": HardeningPatch(
                weakness=check_name, severity=severity,
                config_target="cowrie.cfg",
                patch_type="value_change",
                before="custom_error_messages = false",
                after="custom_error_messages = true  # override all msgs to match OpenSSH 9.x",
            ),
        }
        return patches.get(check_name)

    def _apply_patch(self, patch: HardeningPatch):
        # In production: parse target config file and apply the change
        # Here we simulate the application and log it
        logger.info("Applying patch %s: %s → %s [target: %s]",
                    patch.patch_id, patch.config_target, patch.patch_type, patch.after[:60])
        time.sleep(0.05)  # simulate write

    def _persist_patch(self, patch: HardeningPatch):
        try:
            self.db["ashrta_patches"].update_one(
                {"patch_id": patch.patch_id},
                {"$set": patch.to_dict()},
                upsert=True,
            )
        except Exception:
            pass


class ASHRTAScheduler:
    """
    Schedules automated RedAgent runs and hardening cycles.
    Runs every 6 hours (configurable) using APScheduler or manual trigger.
    """

    def __init__(self, db, red_agent, optimizer, interval_hours: float = 6.0):
        self.db = db
        self.red_agent = red_agent
        self.optimizer = optimizer
        self.interval  = interval_hours * 3600
        self._reports: list[dict] = []
        self._running = False

    def run_cycle(self, env_config: Optional[dict] = None) -> dict:
        """Execute one full red-team + hardening cycle."""
        config = env_config or self._default_env_config()
        logger.info("ASHRTA cycle starting...")

        report = self.red_agent.run(env_config=config)
        patches = self.optimizer.generate_patches(report)
        applied = self.optimizer.apply_patches(patches)

        summary = {
            "report_id": report.report_id,
            "timestamp": report.timestamp,
            "hardening_score": report.hardening_score,
            "checks_passed": report.checks_passed,
            "checks_total": report.checks_total,
            "critical_weaknesses": report.critical_weaknesses,
            "patches_generated": len(patches),
            "patches_applied": applied,
        }
        self._reports.append(summary)

        try:
            self.db["ashrta_reports"].insert_one({**summary, **report.to_dict()})
        except Exception:
            pass

        logger.info("ASHRTA cycle complete: score=%.1f%% patches=%d/%d",
                    report.hardening_score, applied, len(patches))
        return summary

    def get_reports(self, limit: int = 10) -> list[dict]:
        try:
            return list(self.db["ashrta_reports"].find(
                {}, {"_id": 0, "report_id": 1, "timestamp": 1, "hardening_score": 1,
                     "checks_passed": 1, "checks_total": 1, "critical_weaknesses": 1,
                     "patches_generated": 1, "patches_applied": 1}
            ).sort("timestamp", -1).limit(limit))
        except Exception:
            return self._reports[-limit:]

    @staticmethod
    def _default_env_config() -> dict:
        return {
            "ssh_banner":             "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6",
            "os_banner":              "Ubuntu 20.04.6 LTS",
            "kernel_version":         "5.15.0-97-generic",
            "filesystem_entries":     145,
            "has_proc_entries":       False,
            "fake_process_count":     18,
            "tcp_window_size":        65535,
            "ttl":                    64,
            "login_fail_msg":         "Permission denied, please try again.",
            "fake_load_avg":          "0.00 0.00 0.00",
            "fake_uptime_days":       2,
            "custom_error_messages":  False,
            "has_systemd":            True,
        }
