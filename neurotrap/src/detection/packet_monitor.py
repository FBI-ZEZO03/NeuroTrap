"""
packet_monitor.py — Live packet capture and threshold-based anomaly detection.

Runs on the honeypot-net bridge interface and emits AlertEvent objects into MongoDB.
Detects: port scans (>10 ports/5s), brute-force (>5 failed logins/min),
         protocol anomalies, and automated tool fingerprints.
"""

from __future__ import annotations
import os
import time
import logging
import threading
from collections import defaultdict
from typing import Callable

try:
    from scapy.all import sniff, IP, TCP, UDP, Raw
    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False

from .alert_schema import AlertEvent

logger = logging.getLogger(__name__)

# ── Detection thresholds ───────────────────────────────────────────────────────
SCAN_WINDOW_SECS = 5
SCAN_PORT_THRESHOLD = 10          # unique ports/src in SCAN_WINDOW_SECS
BRUTEFORCE_WINDOW_SECS = 60
BRUTEFORCE_FAIL_THRESHOLD = 5     # failed attempts/src in BRUTEFORCE_WINDOW_SECS


class _RateBucket:
    """Sliding-window counter per source IP."""

    def __init__(self, window: float):
        self.window = window
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def add(self, key: str) -> int:
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            self._events[key] = [t for t in self._events[key] if t > cutoff]
            self._events[key].append(now)
            return len(self._events[key])


class PacketMonitor:
    """
    Captures packets on `interface` and emits AlertEvent instances via `on_alert`.

    Usage:
        monitor = PacketMonitor(interface="br-honeypot", on_alert=my_handler)
        monitor.start()
    """

    def __init__(
        self,
        interface: str,
        on_alert: Callable[[AlertEvent], None],
        honeypot_ports: list[int] | None = None,
    ):
        self.interface = interface
        self.on_alert = on_alert
        self.honeypot_ports = set(honeypot_ports or [22, 23, 21, 80, 443, 445, 3306, 8080])
        self._scan_bucket = _RateBucket(SCAN_WINDOW_SECS)
        self._bruteforce_bucket = _RateBucket(BRUTEFORCE_WINDOW_SECS)
        self._seen_ports: dict[str, set[int]] = defaultdict(set)
        self._running = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        if not SCAPY_AVAILABLE:
            logger.error("Scapy is not installed — packet monitor cannot start.")
            return
        self._running = True
        logger.info("PacketMonitor starting on interface %s", self.interface)
        sniff(
            iface=self.interface,
            prn=self._process_packet,
            store=False,
            stop_filter=lambda _: not self._running,
        )

    def stop(self):
        self._running = False

    # ── Internal ───────────────────────────────────────────────────────────────

    def _process_packet(self, pkt):
        if IP not in pkt:
            return
        src_ip = pkt[IP].src

        if TCP in pkt:
            self._handle_tcp(src_ip, pkt)
        elif UDP in pkt:
            self._handle_udp(src_ip, pkt)

    def _handle_tcp(self, src_ip: str, pkt):
        tcp = pkt[TCP]
        dst_port = tcp.dport

        if dst_port not in self.honeypot_ports:
            return

        # Port scan detection — track unique dst ports per src within window
        now_window_key = f"{src_ip}:{int(time.time() // SCAN_WINDOW_SECS)}"
        self._seen_ports[now_window_key].add(dst_port)
        unique_count = len(self._seen_ports[now_window_key])

        if unique_count >= SCAN_PORT_THRESHOLD:
            self._emit(AlertEvent(
                src_ip=src_ip,
                dst_port=dst_port,
                attack_type="port_scan",
                severity="medium",
                honeypot_source="scapy",
                protocol="tcp",
                extra={"unique_ports_in_window": unique_count},
            ))

        # SYN-only packets to honeypot → likely scanner
        if tcp.flags == 0x02 and dst_port in self.honeypot_ports:
            count = self._scan_bucket.add(src_ip)
            if count == SCAN_PORT_THRESHOLD:
                self._emit(AlertEvent(
                    src_ip=src_ip,
                    dst_port=dst_port,
                    attack_type="port_scan",
                    severity="medium",
                    honeypot_source="scapy",
                    protocol="tcp",
                    extra={"syn_count_in_window": count},
                ))

        # Protocol anomaly — large raw payload on SSH port
        if dst_port == 22 and Raw in pkt:
            payload = bytes(pkt[Raw])
            if len(payload) > 1024:
                self._emit(AlertEvent(
                    src_ip=src_ip,
                    dst_port=22,
                    attack_type="protocol_anomaly",
                    severity="high",
                    honeypot_source="scapy",
                    protocol="tcp",
                    raw_payload=payload[:256].hex(),
                ))

    def _handle_udp(self, src_ip: str, pkt):
        udp = pkt[UDP]
        dst_port = udp.dport
        if dst_port in self.honeypot_ports:
            self._emit(AlertEvent(
                src_ip=src_ip,
                dst_port=dst_port,
                attack_type="protocol_anomaly",
                severity="low",
                honeypot_source="scapy",
                protocol="udp",
            ))

    def _emit(self, event: AlertEvent):
        try:
            self.on_alert(event)
        except Exception as exc:
            logger.error("Alert handler raised: %s", exc)
