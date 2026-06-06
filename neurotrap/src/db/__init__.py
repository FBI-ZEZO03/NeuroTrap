"""NeuroTrap data-access layer (MongoDB with embedded SQLite fallback)."""

from .database import (
    DB_NAME,
    backend,
    get_collection,
    get_db,
    reset,
)

__all__ = ["get_db", "get_collection", "backend", "reset", "DB_NAME"]
