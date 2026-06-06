#!/usr/bin/env python3
"""
validate_samples.py — validate every samples/<c>.sample.json against
schemas/<c>.schema.json ($jsonSchema). Understands MongoDB Extended JSON
($oid/$date/$numberLong/$numberInt/$numberDouble) and the bsonType keyword.

Exit code 0 = all samples valid; 1 = at least one violation.
Pure standard library (no pip installs).
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
SAMPLES = ROOT / "samples"

# Extended-JSON wrapper -> a marker we can type-check.
class Oid(str): pass
class BDate(str): pass

def decode(v):
    if isinstance(v, dict):
        if set(v.keys()) == {"$oid"}:
            return Oid(v["$oid"])
        if set(v.keys()) == {"$date"}:
            return BDate(v["$date"])
        if set(v.keys()) == {"$numberLong"}:
            return int(v["$numberLong"])
        if set(v.keys()) == {"$numberInt"}:
            return int(v["$numberInt"])
        if set(v.keys()) == {"$numberDouble"}:
            return float(v["$numberDouble"])
        return {k: decode(x) for k, x in v.items()}
    if isinstance(v, list):
        return [decode(x) for x in v]
    return v

def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)

def type_ok(value, bson):
    types = bson if isinstance(bson, list) else [bson]
    for t in types:
        if t == "null" and value is None: return True
        if t == "string" and isinstance(value, str) and not isinstance(value, (Oid, BDate)): return True
        if t == "objectId" and isinstance(value, Oid): return True
        if t == "date" and isinstance(value, BDate): return True
        if t == "bool" and isinstance(value, bool): return True
        if t == "int" and is_int(value): return True
        if t == "long" and is_int(value): return True
        if t == "double" and (is_int(value) or isinstance(value, float)): return True
        if t == "object" and isinstance(value, dict): return True
        if t == "array" and isinstance(value, list): return True
    return False

def validate(value, schema, path, errors):
    # enum
    if "enum" in schema:
        if value not in schema["enum"]:
            errors.append(f"{path}: {value!r} not in enum {schema['enum']}")
        return
    if "bsonType" in schema:
        if not type_ok(value, schema["bsonType"]):
            errors.append(f"{path}: expected bsonType {schema['bsonType']}, got {type(value).__name__} ({value!r})")
            return
    # numeric ranges
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")
    # string constraints
    if isinstance(value, str) and not isinstance(value, (Oid, BDate)):
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match /{schema['pattern']}/")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: length {len(value)} < minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: length {len(value)} > maxLength {schema['maxLength']}")
    # objects
    if isinstance(value, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for r in required:
            if r not in value:
                errors.append(f"{path}: missing required '{r}'")
        if schema.get("additionalProperties", True) is False:
            for k in value:
                if k not in props:
                    errors.append(f"{path}: additional property '{k}' not allowed")
        for k, sub in props.items():
            if k in value:
                validate(value[k], sub, f"{path}.{k}", errors)
    # arrays
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: {len(value)} items < minItems {schema['minItems']}")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(value):
                validate(item, item_schema, f"{path}[{i}]", errors)

def main():
    schema_files = sorted(SCHEMAS.glob("*.schema.json"))
    total_docs = 0
    total_fail = 0
    missing = []
    print(f"Validating {len(schema_files)} collections\n")
    for sf in schema_files:
        name = sf.name[: -len(".schema.json")]
        root = json.loads(sf.read_text(encoding="utf-8"))
        schema = root.get("$jsonSchema", root)
        sample_file = SAMPLES / f"{name}.sample.json"
        if not sample_file.exists():
            missing.append(name)
            print(f"  ✗ {name}: MISSING sample file")
            total_fail += 1
            continue
        data = decode(json.loads(sample_file.read_text(encoding="utf-8")))
        docs = data if isinstance(data, list) else [data]
        coll_errors = []
        for i, doc in enumerate(docs):
            errs = []
            validate(doc, schema, f"{name}[{i}]", errs)
            coll_errors.extend(errs)
        total_docs += len(docs)
        if coll_errors:
            total_fail += 1
            print(f"  ✗ {name}: {len(coll_errors)} error(s)")
            for e in coll_errors:
                print(f"      - {e}")
        else:
            print(f"  ✓ {name}: {len(docs)} doc(s) valid")
    print(f"\nCollections: {len(schema_files)} | docs checked: {total_docs} | collections failing: {total_fail}")
    return 1 if total_fail else 0

if __name__ == "__main__":
    sys.exit(main())
