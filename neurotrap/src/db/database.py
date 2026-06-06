"""
database.py — Single entry point for all NeuroTrap data access.

Behaviour:
  * If pymongo is installed AND a MongoDB at MONGO_URI answers a ping within a
    short timeout, every call returns the real Mongo `neurotrap` database.
  * Otherwise it transparently falls back to an embedded SQLite document store
    (see fallback_store.py) at NEUROTRAP_DB_PATH (default ./data/neurotrap.db).

This lets the whole stack — honeypots, detection pipeline, behaviour engine and
the Flask API — run end to end on a laptop with zero infrastructure, while still
using a production MongoDB the moment one is available. No caller needs to know
which backend is active; the read/write surface is identical.

Usage:
    from src.db import get_db, get_collection
    db = get_db()
    db["alert_events"].insert_one({...})
    get_collection("attacker_profiles").find_one({"src_ip": ip})
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)

DB_NAME = "neurotrap"
DEFAULT_MONGO_URI = "mongodb://localhost:27017/neurotrap"
DEFAULT_FALLBACK_PATH = os.path.join("data", "neurotrap.db")

_lock = threading.Lock()
_db = None          # cached handle (real Mongo db or FallbackDB)
_backend = None     # "mongodb" | "sqlite-fallback"


def _connect_mongo():
    """Return a live Mongo `neurotrap` db, or None if unavailable."""
    if os.getenv("NEUROTRAP_FORCE_FALLBACK", "").lower() in ("1", "true", "yes"):
        return None
    try:
        from pymongo import MongoClient
    except ImportError:
        return None

    uri = os.getenv("MONGO_URI", DEFAULT_MONGO_URI)
    timeout = int(os.getenv("MONGO_TIMEOUT_MS", "1000"))
    try:
        client = MongoClient(
            uri,
            serverSelectionTimeoutMS=timeout,
            connectTimeoutMS=timeout,
        )
        client.admin.command("ping")
        return client[DB_NAME]
    except Exception as exc:  # connection refused, auth error, DNS, etc.
        logger.info("MongoDB unavailable (%s); using embedded fallback store.", exc)
        return None


def _connect_fallback():
    from .fallback_store import FallbackDB

    path = os.getenv("NEUROTRAP_DB_PATH", DEFAULT_FALLBACK_PATH)
    logger.info("Using embedded SQLite document store at %s", path)
    return FallbackDB(path)


def get_db():
    """Return the active database handle, connecting/falling back on first use."""
    global _db, _backend
    if _db is not None:
        return _db
    with _lock:
        if _db is not None:
            return _db
        mongo = _connect_mongo()
        if mongo is not None:
            _db, _backend = mongo, "mongodb"
        else:
            _db, _backend = _connect_fallback(), "sqlite-fallback"
        return _db


def get_collection(name: str):
    """Convenience accessor for a single collection."""
    return get_db()[name]


def backend() -> Optional[str]:
    """Return the active backend name once get_db() has been called."""
    return _backend


def reset():
    """Drop the cached handle so the next get_db() reconnects. For tests."""
    global _db, _backend
    with _lock:
        try:
            if _db is not None and hasattr(_db, "close"):
                _db.close()
        except Exception:
            pass
        _db = None
        _backend = None
