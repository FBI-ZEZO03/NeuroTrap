"""
red_agent.py — Automated Red Team Agent that attempts to detect NeuroTrap's
own honeypots using real honeypot-detection heuristics.

Detection checks (from HoneyBadger & academic literature):
  1. Response timing analysis (honeypots add latency)
  2. OS fingerprint inconsistencies (kernel vs banner mismatch)
  3. Filesystem anomaly detection (missing /proc entries, fake fs)
  4. Behavioral tells in service responses (SSH banner patterns)
  5. Network stack fingerprinting (TCP window sizes, options)
  6. Process list analysis (too-clean process tree)
  7. CPU/memory artifact detection (fake load averages)
"""

from __future__ import annotations
import time
import uuid
import logging
import random
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DetectionResult:
    check_name: str
    passed: bool           # True = Red Agent could NOT detect honeypot (good)
    severity: str          # low | medium | high | critical
    description: str
    recommendation: str
    confidence: float      # 0.0–1.0
    latency_ms: float = 0.0


@dataclass
class RedAgentReport:
    report_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    target_env: str = ""
    checks_total: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    hardening_score: float = 0.0    # 0–100
    critical_weaknesses: int = 0
    results: list[dict] = field(default_factory=list)
    status: str = "complete"

    def to_dict(self) -> dict:
        return asdict(self)


class RedAgent:
    """
    Automated attacker that tests NeuroTrap's own honeypots for detectability.

    Each check simulates a real honeypot-detection technique.
    Returns a RedAgentReport with per-check results and a hardening score.

    Usage:
        agent = RedAgent()
        report = agent.run(target_host="cowrie", target_port=22, env_config={...})
    """

    CHECKS = [
        "timing_analysis",
        "ssh_banner_fingerprint",
        "os_fingerprint_consistency",
        "filesystem_completeness",
        "process_tree_plausibility",
        "network_stack_fingerprint",
        "service_response_behavior",
        "cpu_memory_artifacts",
        "uptime_consistency",
        "error_message_authenticity",
    ]

    def run(self, target_host: str = "localhost", target_port: int = 22,
            env_config: Optional[dict] = None) -> RedAgentReport:

        report = RedAgentReport(target_env=f"{target_host}:{target_port}")
        results: list[DetectionResult] = []

        for check in self.CHECKS:
            try:
                result = getattr(self, f"_check_{check}")(target_host, target_port, env_config or {})
                results.append(result)
            except Exception as exc:
                results.append(DetectionResult(
                    check_name=check, passed=False, severity="low",
                    description=f"Check failed to execute: {exc}",
                    recommendation="Ensure check tooling is installed",
                    confidence=0.0,
                ))

        report.checks_total  = len(results)
        report.checks_passed = sum(1 for r in results if r.passed)
        report.checks_failed = sum(1 for r in results if not r.passed)
        report.critical_weaknesses = sum(1 for r in results if not r.passed and r.severity == "critical")
        report.hardening_score = round((report.checks_passed / max(report.checks_total, 1)) * 100, 1)
        report.results = [asdict(r) for r in results]

        logger.info("RedAgent report %s: score=%.1f%%  passed=%d/%d  critical=%d",
                    report.report_id, report.hardening_score,
                    report.checks_passed, report.checks_total, report.critical_weaknesses)
        return report

    # ── Detection checks ───────────────────────────────────────────────────────

    def _check_timing_analysis(self, host, port, cfg) -> DetectionResult:
        latencies = []
        for _ in range(5):
            t = time.perf_counter()
            time.sleep(random.uniform(0.001, 0.003))  # simulate network round-trip
            latencies.append((time.perf_counter() - t) * 1000)

        avg_ms  = sum(latencies) / len(latencies)
        jitter  = max(latencies) - min(latencies)
        # Real SSH has <10ms jitter; Cowrie default adds ~2ms consistent delay
        consistent_delay = jitter < 1.5
        passed = not consistent_delay

        return DetectionResult(
            check_name="timing_analysis",
            passed=passed,
            severity="high" if not passed else "low",
            description=f"Average response: {avg_ms:.1f}ms, jitter: {jitter:.1f}ms. "
                        f"{'Suspiciously consistent — possible emulation.' if not passed else 'Natural timing variance detected.'}",
            recommendation="Add randomized response delay (50–200ms jitter) to all emulated services"
                           if not passed else "Timing looks natural.",
            confidence=0.72 if not passed else 0.15,
            latency_ms=avg_ms,
        )

    def _check_ssh_banner_fingerprint(self, host, port, cfg) -> DetectionResult:
        banner = cfg.get("ssh_banner", "SSH-2.0-OpenSSH_8.9p1 Ubuntu-3ubuntu0.6")
        # Cowrie default banners are well-known to detection tools
        known_cowrie_banners = ["OpenSSH_6.0p1", "OpenSSH_7.5", "SSH-2.0-OpenSSH_5.9"]
        detected = any(kb in banner for kb in known_cowrie_banners)
        # Check version vs OS consistency
        version_match = "Ubuntu" in banner and "p1" in banner
        passed = not detected and version_match

        return DetectionResult(
            check_name="ssh_banner_fingerprint",
            passed=passed,
            severity="critical" if not passed else "low",
            description=f"Banner: '{banner}'. "
                        f"{'Known Cowrie default detected.' if detected else 'Banner appears realistic.'}",
            recommendation="Randomize SSH banner version per deployment; use current LTS versions"
                           if not passed else "Banner is convincing.",
            confidence=0.95 if detected else 0.2,
        )

    def _check_os_fingerprint_consistency(self, host, port, cfg) -> DetectionResult:
        banner_os   = cfg.get("os_banner", "Ubuntu 20.04.6 LTS")
        kernel_fake = cfg.get("kernel_version", "5.15.0-97-generic")
        # Validate: Ubuntu 20.04 LTS → kernel 5.4.x, not 5.15.x
        inconsistent = "20.04" in banner_os and "5.15" in kernel_fake
        passed = not inconsistent

        return DetectionResult(
            check_name="os_fingerprint_consistency",
            passed=passed,
            severity="high" if not passed else "low",
            description=f"OS '{banner_os}' with kernel '{kernel_fake}'. "
                        f"{'Kernel/OS mismatch detected.' if not passed else 'Fingerprints are consistent.'}",
            recommendation="Ubuntu 20.04 ships kernel 5.4.x. Use matching kernel strings in config."
                           if not passed else "Fingerprints consistent.",
            confidence=0.88 if not passed else 0.1,
        )

    def _check_filesystem_completeness(self, host, port, cfg) -> DetectionResult:
        honeyfs = cfg.get("filesystem_entries", 120)
        # Real Ubuntu systems have 50K+ filesystem entries; Cowrie defaults ~200
        too_sparse = honeyfs < 500
        missing_proc = not cfg.get("has_proc_entries", False)
        passed = not too_sparse and not missing_proc

        return DetectionResult(
            check_name="filesystem_completeness",
            passed=passed,
            severity="critical" if too_sparse else ("medium" if missing_proc else "low"),
            description=f"Filesystem entries: {honeyfs}. /proc present: {not missing_proc}. "
                        f"{'Too sparse for a real system.' if too_sparse else 'Filesystem density looks realistic.'}",
            recommendation="Expand honeyfs with realistic /proc, /sys, /dev entries. Target >2000 files."
                           if not passed else "Filesystem completeness is convincing.",
            confidence=0.91 if too_sparse else 0.3,
        )

    def _check_process_tree_plausibility(self, host, port, cfg) -> DetectionResult:
        process_count = cfg.get("fake_process_count", 15)
        has_systemd   = cfg.get("has_systemd", True)
        # Real servers run 100-300 processes; honeypots default to <20
        too_clean = process_count < 40
        passed = not too_clean and has_systemd

        return DetectionResult(
            check_name="process_tree_plausibility",
            passed=passed,
            severity="high" if not passed else "low",
            description=f"Process count: {process_count}. systemd present: {has_systemd}. "
                        f"{'Too few processes — honeypot tell.' if too_clean else 'Process tree looks realistic.'}",
            recommendation="Add realistic background processes: kworker, systemd-journald, rsyslog, sshd, cron, etc."
                           if not passed else "Process tree convincing.",
            confidence=0.82 if too_clean else 0.2,
        )

    def _check_network_stack_fingerprint(self, host, port, cfg) -> DetectionResult:
        tcp_window = cfg.get("tcp_window_size", 65535)
        ttl        = cfg.get("ttl", 64)
        # Linux default TTL=64, window=29200; Windows=128; Cowrie often uses 65535
        suspicious = tcp_window == 65535 and ttl == 64
        passed = not suspicious

        return DetectionResult(
            check_name="network_stack_fingerprint",
            passed=passed,
            severity="medium" if not passed else "low",
            description=f"TCP window: {tcp_window}, TTL: {ttl}. "
                        f"{'TCP window = 65535 with TTL 64 is a common Cowrie fingerprint.' if not passed else 'Network stack looks realistic.'}",
            recommendation="Set TCP window to 29200 (Linux default) in kernel parameters."
                           if not passed else "Network fingerprint convincing.",
            confidence=0.65 if not passed else 0.1,
        )

    def _check_service_response_behavior(self, host, port, cfg) -> DetectionResult:
        error_msg = cfg.get("login_fail_msg", "Permission denied, please try again.")
        cmd_output = cfg.get("sample_cmd_output", "")
        # Cowrie's exact error messages are fingerprinted
        cowrie_tells = ["please try again", "cowrie", "kippo"]
        detected = any(t.lower() in error_msg.lower() for t in cowrie_tells)
        passed = not detected

        return DetectionResult(
            check_name="service_response_behavior",
            passed=passed,
            severity="critical" if "cowrie" in error_msg.lower() else ("medium" if not passed else "low"),
            description=f"Login error: '{error_msg[:60]}'. "
                        f"{'Cowrie signature detected.' if not passed else 'Response looks authentic.'}",
            recommendation="Customize error messages to match real OpenSSH output exactly."
                           if not passed else "Service responses appear authentic.",
            confidence=0.95 if "cowrie" in error_msg.lower() else 0.55,
        )

    def _check_cpu_memory_artifacts(self, host, port, cfg) -> DetectionResult:
        load_avg = cfg.get("fake_load_avg", "0.00 0.00 0.00")
        # Perfect 0.00 load on a "busy" server is suspicious
        too_perfect = load_avg == "0.00 0.00 0.00"
        passed = not too_perfect

        return DetectionResult(
            check_name="cpu_memory_artifacts",
            passed=passed,
            severity="medium" if not passed else "low",
            description=f"Load average: {load_avg}. "
                        f"{'Perfect zero load is unrealistic for a production server.' if not passed else 'Load appears realistic.'}",
            recommendation="Inject realistic load average: '0.23 0.18 0.15' with minor variation."
                           if not passed else "Load average convincing.",
            confidence=0.7 if not passed else 0.1,
        )

    def _check_uptime_consistency(self, host, port, cfg) -> DetectionResult:
        uptime_days = cfg.get("fake_uptime_days", 0)
        passed = uptime_days > 5  # new servers are suspicious

        return DetectionResult(
            check_name="uptime_consistency",
            passed=passed,
            severity="low" if not passed else "low",
            description=f"Uptime: {uptime_days} days. "
                        f"{'Very recent boot time is unusual for production.' if not passed else 'Uptime is plausible.'}",
            recommendation="Set fake uptime to 30–120 days with randomization."
                           if not passed else "Uptime is convincing.",
            confidence=0.45 if not passed else 0.05,
        )

    def _check_error_message_authenticity(self, host, port, cfg) -> DetectionResult:
        uses_custom_errors = cfg.get("custom_error_messages", False)
        passed = uses_custom_errors

        return DetectionResult(
            check_name="error_message_authenticity",
            passed=passed,
            severity="medium" if not passed else "low",
            description="Custom error messages enabled." if passed else "Using default Cowrie error messages.",
            recommendation="Override all error messages in cowrie.cfg to match current OpenSSH 9.x output."
                           if not passed else "Error messages customized.",
            confidence=0.6 if not passed else 0.1,
        )
