"""
bait_injector.py — Generates targeted bait asset injection commands
based on the attacker's dominant cognitive bias.

Outputs structured BaitInjection objects that the Deception Engine's
fake filesystem factory and credential manager execute.
"""

from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional
from .bias_scorer import BiasProfile


@dataclass
class BaitAsset:
    asset_type: str          # file | credential | directory | process | log_entry
    path: str
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class BaitInjection:
    injection_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    env_id: str = ""
    src_ip: str = ""
    bias_trigger: str = ""
    bias_score: float = 0.0
    assets: list[BaitAsset] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    executed: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


class BaitInjector:
    """
    Selects and generates bait assets tuned to the attacker's dominant bias.

    Each bias maps to a different psychological lever:
      curiosity_gap    → incomplete secret files with tantalizing names
      confirmation_bias → fake evidence validating what attacker believes
      sunk_cost        → 'valuable' files to justify their time investment
      authority_signal → high-privilege artifacts (root creds, admin memos)
      scarcity_framing → time-stamped urgent docs ("DELETE BEFORE AUDIT")
    """

    def generate(self, profile: BiasProfile, env_id: str, src_ip: str) -> BaitInjection:
        inj = BaitInjection(env_id=env_id, src_ip=src_ip,
                            bias_trigger=profile.dominant, bias_score=profile.overall)
        bias = profile.dominant
        inj.assets = getattr(self, f"_bait_{bias}", self._bait_curiosity_gap)(profile)
        return inj

    # ── Bait templates per bias ───────────────────────────────────────────────

    def _bait_curiosity_gap(self, p: BiasProfile) -> list[BaitAsset]:
        return [
            BaitAsset("file", "/home/admin/.ssh/id_rsa_backup",
                "-----BEGIN RSA PRIVATE KEY-----\n[REDACTED - PARTIAL]\nMIIEowIBAAKCAQEA... [content truncated]\n# Full key in /root/.vault/master.key\n-----END RSA PRIVATE KEY-----",
                {"canarytoken": True, "lure_type": "curiosity_gap"}),
            BaitAsset("file", "/var/www/.env.production.bak",
                "# PRODUCTION BACKUP — DO NOT COMMIT\n# Full config at /etc/app/secrets/\nDB_PASS=... [truncated]\nAWS_KEY=... [see /root/.aws/credentials]",
                {"canarytoken": True}),
            BaitAsset("directory", "/root/.vault", "", {"hidden": True, "lure_type": "breadcrumb"}),
        ]

    def _bait_confirmation_bias(self, p: BiasProfile) -> list[BaitAsset]:
        return [
            BaitAsset("file", "/etc/app/config.yml",
                "# Financial Services Configuration\ndatabase:\n  host: db-prod-01.internal\n  name: customer_records\n  user: svc_account\n  password: Prod@cc3ss2024!\npayment_gateway:\n  api_key: sk_live_AbCdEfGhIjKlMnOpQrSt\n  secret: whsec_XXXXXXXXXXXXXXXXXXXX",
                {"canarytoken": True, "lure_type": "confirmation_bias"}),
            BaitAsset("file", "/var/log/auth_audit.log",
                "2026-06-01 09:12:44 WARN: Multiple failed login attempts from external IP\n2026-06-01 09:15:02 INFO: Admin account 'svc_deploy' authenticated from 10.0.0.5\n2026-06-01 10:30:11 CRITICAL: Unpatched CVE-2024-3094 detected on this host\n# Remediation scheduled for Q3 2026",
                {"lure_type": "vulnerability_confirmation"}),
        ]

    def _bait_sunk_cost(self, p: BiasProfile) -> list[BaitAsset]:
        return [
            BaitAsset("file", "/tmp/customer_data_export_2026.csv.gpg",
                "# GPG encrypted — passphrase in /etc/app/.master_pass\n# Contains: 2.4M customer records, PII, payment data\n# Encryption: AES-256",
                {"canarytoken": True, "lure_type": "sunk_cost_reward"}),
            BaitAsset("file", "/home/deploy/backup_keys.tar.gz.part1",
                "# Multi-part archive — 3 of 5 parts present\n# Remaining parts on NAS: \\\\nas01\\backup\\keys\\\n# Script to reassemble: /home/deploy/restore.sh",
                {"lure_type": "sunk_cost_progress"}),
            BaitAsset("file", "/home/deploy/restore.sh",
                "#!/bin/bash\n# Restore encryption keys from backup\necho 'Connecting to key server...'\ncurl -s http://keyserver.internal/api/v2/keys/master > /tmp/.master\necho 'Keys restored to /tmp/.master'",
                {"canarytoken": True}),
        ]

    def _bait_authority_signal(self, p: BiasProfile) -> list[BaitAsset]:
        return [
            BaitAsset("file", "/root/CONFIDENTIAL_IT_MEMO_2026.txt",
                "FROM: CTO <cto@company.internal>\nTO: IT Security Team\nSUBJECT: Emergency Credential Rotation — DO NOT FORWARD\n\nEffective immediately, all service account passwords are being rotated.\nTemporary master credential (valid 48h): Adm1n_Temp_2026#Secure\nApply to: prod-db-01, prod-app-cluster, payment-gateway-02\n\nDO NOT store this in any ticketing system.",
                {"canarytoken": True, "lure_type": "authority_memo"}),
            BaitAsset("file", "/etc/sudoers.d/emergency_access",
                "# EMERGENCY ACCESS — REMOVE AFTER INCIDENT\n# Created by: security@company.internal\n# Ticket: INC-20260601-0042\ndeploy ALL=(ALL) NOPASSWD: ALL\nsvc_monitor ALL=(ALL) NOPASSWD: /usr/bin/systemctl",
                {"lure_type": "authority_escalation"}),
        ]

    def _bait_scarcity_framing(self, p: BiasProfile) -> list[BaitAsset]:
        return [
            BaitAsset("file", "/root/URGENT_DELETE_BEFORE_AUDIT.sh",
                "#!/bin/bash\n# URGENT: Delete before compliance audit on 2026-06-07\n# Auditors arrive at 09:00 UTC\nrm -f /var/log/access_old.log\nrm -rf /home/admin/.bash_history\n# Backup first: scp /etc/shadow backup@10.0.0.99:/backups/pre_audit/",
                {"canarytoken": True, "lure_type": "scarcity_urgency"}),
            BaitAsset("file", "/tmp/.cron_backup_now",
                "# LAST CHANCE BACKUP — SYSTEM DECOMMISSION IN 2 DAYS\n# All data will be wiped 2026-06-06 00:00 UTC\n# Critical files: /etc/app/secrets/, /var/db/prod/, /root/.ssh/\nrsync -avz /etc/app/secrets/ backup@192.168.1.200:/emergency/",
                {"lure_type": "scarcity_deadline"}),
        ]
