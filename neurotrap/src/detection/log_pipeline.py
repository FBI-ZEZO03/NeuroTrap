"""
log_pipeline.py — Tails Cowrie/Dionaea JSON logs and ingests them into MongoDB.

Runs as a background thread alongside packet_monitor.
"""

from __future__ import annotations
import json
import os
import time
import logging
import threading
from pathlib import Path
from typing import Callable

from .alert_schema import AlertEvent

logger = logging.getLogger(__name__)


class LogTailer:
    """Tails a JSON-lines log file and calls `on_line` for each new entry."""

    def __init__(self, path: str | Path, on_line: Callable[[dict], None], poll_interval: float = 0.5):
        self.path = Path(path)
        self.on_line = on_line
        self.poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._tail, daemon=True, name=f"tailer-{self.path.name}")
        self._thread.start()
        logger.info("LogTailer started for %s", self.path)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _tail(self):
        while not self.path.exists() and self._running:
            time.sleep(1)

        with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
            fh.seek(0, 2)  # seek to end — only new lines
            while self._running:
                line = fh.readline()
                if line:
                    try:
                        self.on_line(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
                else:
                    time.sleep(self.poll_interval)


class LogIngestionPipeline:
    """
    Coordinates multiple log tailers and normalizes all events into
    AlertEvent objects, then persists them to MongoDB.

    Usage:
        pipeline = LogIngestionPipeline(db_collection, cowrie_log_path, dionaea_log_path)
        pipeline.start()
    """

    def __init__(
        self,
        collection,                 # pymongo collection
        cowrie_log: str | None = None,
        dionaea_log: str | None = None,
    ):
        self.collection = collection
        self._tailers: list[LogTailer] = []

        if cowrie_log:
            self._tailers.append(LogTailer(cowrie_log, self._handle_cowrie))
        if dionaea_log:
            self._tailers.append(LogTailer(dionaea_log, self._handle_dionaea))

    def start(self):
        for tailer in self._tailers:
            tailer.start()

    def stop(self):
        for tailer in self._tailers:
            tailer.stop()

    def ingest(self, event: AlertEvent):
        """Persist a single AlertEvent (called from PacketMonitor too)."""
        try:
            doc = event.to_dict()
            self.collection.update_one(
                {"event_id": doc["event_id"]},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.error("DB write failed: %s", exc)

    def _handle_cowrie(self, raw: dict):
        event = AlertEvent.from_cowrie(raw)
        self.ingest(event)

    def _handle_dionaea(self, raw: dict):
        # Dionaea logs have their own schema; do a basic mapping
        event = AlertEvent(
            src_ip=raw.get("remote_host", "0.0.0.0"),
            dst_port=raw.get("remote_port", 0),
            attack_type="malware_upload",
            severity="high",
            honeypot_source="dionaea",
            protocol=raw.get("connection", {}).get("protocol"),
            extra=raw,
        )
        self.ingest(event)
