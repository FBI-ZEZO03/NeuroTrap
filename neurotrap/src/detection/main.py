"""
Entry point for the packet-monitor container.
Starts PacketMonitor + LogIngestionPipeline together.
"""

import os
import logging

from ..db import get_db, backend
from .packet_monitor import PacketMonitor
from .log_pipeline import LogIngestionPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("neurotrap.monitor")


def main():
    db = get_db()
    logger.info("Storage backend: %s", backend())
    collection = db["alert_events"]

    # Ensure indexes
    collection.create_index("src_ip")
    collection.create_index("timestamp")
    collection.create_index("attack_type")

    pipeline = LogIngestionPipeline(
        collection=collection,
        cowrie_log=os.getenv("COWRIE_LOG", "/cowrie/logs/cowrie.json"),
        dionaea_log=os.getenv("DIONAEA_LOG", "/opt/dionaea/var/log/dionaea/dionaea.json"),
    )
    pipeline.start()

    iface = os.getenv("MONITOR_INTERFACE", "eth0")
    monitor = PacketMonitor(
        interface=iface,
        on_alert=pipeline.ingest,
    )

    logger.info("NeuroTrap packet monitor starting on %s", iface)
    try:
        monitor.start()   # blocking
    except KeyboardInterrupt:
        monitor.stop()
        pipeline.stop()


if __name__ == "__main__":
    main()
