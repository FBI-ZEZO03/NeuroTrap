"""
fallback_store.py — Embedded, zero-dependency document store used when MongoDB
is not reachable (e.g. running the capstone locally on Windows with no Docker).

It persists each collection to a single SQLite file (one row per document, the
document stored as JSON) and evaluates queries in Python. The public surface is a
faithful subset of the pymongo API the NeuroTrap codebase actually uses:

    db["name"].insert_one(doc)
    db["name"].update_one(filter, {"$set": {...}}, upsert=True)
    db["name"].find(query, projection).sort(field, dir).skip(n).limit(n)
    db["name"].find_one(query, projection)
    db["name"].count_documents(query)
    db["name"].create_index(...)            # accepted, no-op (SQLite handles scans)
    db["name"].aggregate(pipeline)          # $match / $group / $sort / $limit

This means the rest of the system (honeypots, detection pipeline, API,
behaviour engine) can read and write the same way regardless of whether a real
MongoDB is present. Documents are plain dicts; an "_id" hex string is added on
insert to mirror Mongo semantics (projections of {"_id": 0} strip it).
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from typing import Any, Iterable, Iterator, Optional

ASCENDING = 1
DESCENDING = -1


# ── Query / expression evaluation ───────────────────────────────────────────────

_COMPARATORS = {
    "$eq": lambda a, b: a == b,
    "$ne": lambda a, b: a != b,
    "$gt": lambda a, b: a is not None and a > b,
    "$gte": lambda a, b: a is not None and a >= b,
    "$lt": lambda a, b: a is not None and a < b,
    "$lte": lambda a, b: a is not None and a <= b,
    "$in": lambda a, b: a in b,
    "$nin": lambda a, b: a not in b,
}


def _get_path(doc: dict, dotted: str) -> Any:
    """Resolve a possibly dotted field path like 'connection.protocol'."""
    cur: Any = doc
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _matches(doc: dict, query: dict) -> bool:
    """Return True if `doc` satisfies a Mongo-style `query`."""
    for key, cond in query.items():
        if key == "$or":
            if not any(_matches(doc, sub) for sub in cond):
                return False
            continue
        if key == "$and":
            if not all(_matches(doc, sub) for sub in cond):
                return False
            continue

        value = _get_path(doc, key)
        if isinstance(cond, dict) and any(k.startswith("$") for k in cond):
            for op, operand in cond.items():
                fn = _COMPARATORS.get(op)
                if fn is None or not fn(value, operand):
                    return False
        else:
            if value != cond:
                return False
    return True


def _eval_expr(expr: Any, doc: dict) -> Any:
    """Evaluate an aggregation expression against a single document."""
    if isinstance(expr, str) and expr.startswith("$"):
        return _get_path(doc, expr[1:])
    if isinstance(expr, dict):
        if "$switch" in expr:
            spec = expr["$switch"]
            for branch in spec.get("branches", []):
                if _eval_expr(branch["case"], doc):
                    return _eval_expr(branch["then"], doc)
            return _eval_expr(spec.get("default"), doc)
        if "$eq" in expr:
            a, b = (_eval_expr(x, doc) for x in expr["$eq"])
            return a == b
        if "$ne" in expr:
            a, b = (_eval_expr(x, doc) for x in expr["$ne"])
            return a != b
    return expr  # literal


def _apply_projection(doc: dict, projection: Optional[dict]) -> dict:
    if not projection:
        return dict(doc)
    # Only the exclusion style used in the codebase ({"_id": 0}) is supported,
    # plus simple inclusion projections.
    includes = {k for k, v in projection.items() if v and k != "_id"}
    excludes = {k for k, v in projection.items() if not v}
    if includes:
        out = {k: doc[k] for k in includes if k in doc}
        if projection.get("_id", 1):
            out["_id"] = doc.get("_id")
        return out
    return {k: v for k, v in doc.items() if k not in excludes}


# ── Cursor ──────────────────────────────────────────────────────────────────────


class _Cursor:
    """In-memory cursor supporting the chained sort/skip/limit calls used here."""

    def __init__(self, docs: list[dict]):
        self._docs = docs

    def sort(self, key_or_list, direction: int = ASCENDING) -> "_Cursor":
        if isinstance(key_or_list, (list, tuple)):
            for field, dr in reversed(key_or_list):
                self._docs.sort(key=lambda d, f=field: _sort_key(_get_path(d, f)),
                                reverse=(dr == DESCENDING))
        else:
            self._docs.sort(key=lambda d: _sort_key(_get_path(d, key_or_list)),
                            reverse=(direction == DESCENDING))
        return self

    def skip(self, n: int) -> "_Cursor":
        self._docs = self._docs[n:]
        return self

    def limit(self, n: int) -> "_Cursor":
        if n:
            self._docs = self._docs[:n]
        return self

    def __iter__(self) -> Iterator[dict]:
        return iter(self._docs)

    def __len__(self) -> int:
        return len(self._docs)


def _sort_key(value: Any):
    """Total ordering helper so None sorts consistently below real values."""
    if value is None:
        return (0, 0)
    if isinstance(value, bool):
        return (1, int(value))
    if isinstance(value, (int, float)):
        return (2, value)
    return (3, str(value))


# ── Collection ──────────────────────────────────────────────────────────────────


class FallbackCollection:
    def __init__(self, store: "FallbackDB", name: str):
        self._store = store
        self._name = name
        self._store._ensure_table(name)

    # writes ---------------------------------------------------------------------

    def insert_one(self, document: dict):
        doc = dict(document)
        doc.setdefault("_id", uuid.uuid4().hex)
        self._store._write(self._name, doc["_id"], doc)
        return type("InsertOneResult", (), {"inserted_id": doc["_id"]})()

    def insert_many(self, documents: Iterable[dict]):
        ids = [self.insert_one(d).inserted_id for d in documents]
        return type("InsertManyResult", (), {"inserted_ids": ids})()

    def update_one(self, filter: dict, update: dict, upsert: bool = False):
        rows = self._store._all(self._name)
        target = next((d for d in rows if _matches(d, filter)), None)
        set_fields = update.get("$set", {})
        inc_fields = update.get("$inc", {})
        push_fields = update.get("$push", {})

        if target is not None:
            for k, v in set_fields.items():
                target[k] = v
            for k, v in inc_fields.items():
                target[k] = (target.get(k) or 0) + v
            for k, v in push_fields.items():
                target.setdefault(k, []).append(v)
            self._store._write(self._name, target["_id"], target)
            return type("UpdateResult", (), {"matched_count": 1, "modified_count": 1, "upserted_id": None})()

        if upsert:
            doc = {k: v for k, v in filter.items() if not k.startswith("$")}
            doc.update(set_fields)
            for k, v in inc_fields.items():
                doc[k] = v
            for k, v in push_fields.items():
                doc.setdefault(k, []).append(v)
            res = self.insert_one(doc)
            return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0, "upserted_id": res.inserted_id})()

        return type("UpdateResult", (), {"matched_count": 0, "modified_count": 0, "upserted_id": None})()

    def delete_many(self, filter: dict):
        rows = self._store._all(self._name)
        removed = [d for d in rows if _matches(d, filter)]
        for d in removed:
            self._store._delete(self._name, d["_id"])
        return type("DeleteResult", (), {"deleted_count": len(removed)})()

    def create_index(self, *args, **kwargs):  # noqa: D401 - accepted, no-op
        return self._name

    # reads ----------------------------------------------------------------------

    def find(self, query: Optional[dict] = None, projection: Optional[dict] = None) -> _Cursor:
        rows = self._store._all(self._name)
        matched = [d for d in rows if _matches(d, query or {})]
        return _Cursor([_apply_projection(d, projection) for d in matched])

    def find_one(self, query: Optional[dict] = None, projection: Optional[dict] = None) -> Optional[dict]:
        for d in self._store._all(self._name):
            if _matches(d, query or {}):
                return _apply_projection(d, projection)
        return None

    def count_documents(self, query: Optional[dict] = None) -> int:
        return sum(1 for d in self._store._all(self._name) if _matches(d, query or {}))

    def aggregate(self, pipeline: list[dict]) -> list[dict]:
        docs = self._store._all(self._name)
        for stage in pipeline:
            op, spec = next(iter(stage.items()))
            if op == "$match":
                docs = [d for d in docs if _matches(d, spec)]
            elif op == "$group":
                docs = _group(docs, spec)
            elif op == "$sort":
                for field, dr in reversed(list(spec.items())):
                    docs.sort(key=lambda d, f=field: _sort_key(_get_path(d, f)),
                              reverse=(dr == DESCENDING))
            elif op == "$limit":
                docs = docs[:spec]
            elif op == "$skip":
                docs = docs[spec:]
            elif op == "$project":
                docs = [_apply_projection(d, spec) for d in docs]
        return docs


def _group(docs: list[dict], spec: dict) -> list[dict]:
    id_expr = spec["_id"]
    buckets: dict[Any, list[dict]] = {}
    order: list[Any] = []
    for d in docs:
        key = _eval_expr(id_expr, d)
        hkey = json.dumps(key, sort_keys=True, default=str)
        if hkey not in buckets:
            buckets[hkey] = []
            order.append((hkey, key))
        buckets[hkey].append(d)

    results = []
    for hkey, key in order:
        members = buckets[hkey]
        out = {"_id": key}
        for field, acc in spec.items():
            if field == "_id":
                continue
            op, expr = next(iter(acc.items()))
            if op == "$sum":
                total = sum(_num(_eval_expr(expr, m)) for m in members)
                out[field] = int(total) if total.is_integer() else total
            elif op == "$avg":
                vals = [_num(_eval_expr(expr, m)) for m in members]
                out[field] = (sum(vals) / len(vals)) if vals else 0
            elif op == "$max":
                out[field] = max(_eval_expr(expr, m) for m in members)
            elif op == "$min":
                out[field] = min(_eval_expr(expr, m) for m in members)
            elif op == "$first":
                out[field] = _eval_expr(expr, members[0])
            elif op == "$last":
                out[field] = _eval_expr(expr, members[-1])
        results.append(out)
    return results


def _num(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


# ── Database ────────────────────────────────────────────────────────────────────


class FallbackDB:
    """SQLite-backed stand-in for a pymongo Database object."""

    def __init__(self, path: str):
        self.path = path
        directory = os.path.dirname(os.path.abspath(path))
        if directory and not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._tables: set[str] = set()
        self._collections: dict[str, FallbackCollection] = {}

    # mapping interface used everywhere: db["collection"]
    def __getitem__(self, name: str) -> FallbackCollection:
        if name not in self._collections:
            self._collections[name] = FallbackCollection(self, name)
        return self._collections[name]

    def get_collection(self, name: str) -> FallbackCollection:
        return self[name]

    def list_collection_names(self) -> list[str]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            return [r[0] for r in cur.fetchall()]

    def command(self, *args, **kwargs):  # e.g. ping
        return {"ok": 1}

    def close(self):
        with self._lock:
            self._conn.close()

    # storage helpers ------------------------------------------------------------

    def _ensure_table(self, name: str):
        if name in self._tables:
            return
        with self._lock:
            self._conn.execute(
                f'CREATE TABLE IF NOT EXISTS "{name}" '
                "(_id TEXT PRIMARY KEY, doc TEXT NOT NULL)"
            )
            self._conn.commit()
            self._tables.add(name)

    def _write(self, name: str, _id: str, doc: dict):
        self._ensure_table(name)
        payload = json.dumps(doc, default=str)
        with self._lock:
            self._conn.execute(
                f'INSERT INTO "{name}" (_id, doc) VALUES (?, ?) '
                "ON CONFLICT(_id) DO UPDATE SET doc=excluded.doc",
                (_id, payload),
            )
            self._conn.commit()

    def _delete(self, name: str, _id: str):
        with self._lock:
            self._conn.execute(f'DELETE FROM "{name}" WHERE _id=?', (_id,))
            self._conn.commit()

    def _all(self, name: str) -> list[dict]:
        self._ensure_table(name)
        with self._lock:
            cur = self._conn.execute(f'SELECT doc FROM "{name}"')
            return [json.loads(r[0]) for r in cur.fetchall()]
