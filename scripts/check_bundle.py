"""Check the event bundles in events/ against contract v1 (docs/08-Plan-data.md section 3).

Run before every push that touches events/:
    python scripts/check_bundle.py            # checks events/
    python scripts/check_bundle.py path/to/events

Checks: index.json shape, each event.json against events/schema.json, every layer file exists,
PNGs are <= 2048 px, total size of events/ < 20 MB. Exit code 1 if anything fails.
Uses the `jsonschema` package if installed, otherwise a small built-in validator (enough for our schema).
"""
import json
import re
import struct
import sys
from pathlib import Path

MAX_PX = 2048
MAX_TOTAL_MB = 20
INDEX_REQUIRED = ["id", "title", "date", "bbox", "kind", "headline"]


# ---------- minimal JSON Schema subset (used when `jsonschema` is not installed) ----------
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool}


def _is_type(value, t):
    if isinstance(t, list):
        return any(_is_type(value, x) for x in t)
    if t == "null":
        return value is None
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, TYPES[t])


def _validate(value, schema, root, path, errors):
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        schema = node
    if "type" in schema and not _is_type(value, schema["type"]):
        errors.append(f"{path}: expected {schema['type']}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not one of {schema['enum']}")
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: at most {schema['maxItems']} items")
        if "items" in schema:
            for i, v in enumerate(value):
                _validate(v, schema["items"], root, f"{path}[{i}]", errors)
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing '{key}'")
        props = schema.get("properties", {})
        for key, v in value.items():
            if "propertyNames" in schema:
                _validate(key, schema["propertyNames"], root, f"{path}.<key {key}>", errors)
            if key in props:
                _validate(v, props[key], root, f"{path}.{key}", errors)
            elif isinstance(schema.get("additionalProperties"), dict):
                _validate(v, schema["additionalProperties"], root, f"{path}.{key}", errors)


def validate(doc, schema):
    try:
        import jsonschema
    except ImportError:
        errors = []
        _validate(doc, schema, schema, "$", errors)
        return errors
    v = jsonschema.Draft202012Validator(schema)
    return [f"$.{'.'.join(map(str, e.path))}: {e.message}" for e in v.iter_errors(doc)]


# ---------- helpers ----------
def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", head[16:24])


def check_bbox(bbox, where, errors):
    if isinstance(bbox, list) and len(bbox) == 4:
        w, s, e, n = bbox
        if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
            errors.append(f"{where}: bbox {bbox} is not [west, south, east, north]")


def main(root):
    errors = []
    schema_path = root / "schema.json"
    if not schema_path.exists():
        print(f"FAIL: {schema_path} not found")
        return 1
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    index_path = root / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else None
    if index is None:
        errors.append("index.json: missing")
        index = {"events": []}
    events = index.get("events", [])
    if not isinstance(events, list) or not events:
        errors.append("index.json: 'events' must be a non-empty list")
        events = []

    for i, entry in enumerate(events):
        where = f"index.json events[{i}]"
        for key in INDEX_REQUIRED:
            if key not in entry:
                errors.append(f"{where}: missing '{key}'")
        check_bbox(entry.get("bbox"), where, errors)
        eid = entry.get("id")
        if not eid:
            continue
        ev_path = root / eid / "event.json"
        if not ev_path.exists():
            errors.append(f"{where}: {ev_path} not found")
            continue
        ev = json.loads(ev_path.read_text(encoding="utf-8"))
        errors += [f"{eid}/event.json {e}" for e in validate(ev, schema)]
        if ev.get("id") != eid:
            errors.append(f"{eid}/event.json: id {ev.get('id')!r} differs from folder")
        check_bbox(ev.get("bbox"), f"{eid}/event.json", errors)
        layer_ids = set(ev.get("layers", {}))
        for step in ev.get("timeline", []):
            for lid in step.get("layers", []):
                if lid not in layer_ids:
                    errors.append(f"{eid}: timeline {step.get('date')} uses undefined layer '{lid}'")
        for lid, layer in ev.get("layers", {}).items():
            for date, rel in layer.get("files", {}).items():
                f = root / eid / rel
                if not f.exists():
                    errors.append(f"{eid}: layer {lid} {date}: {rel} not found")
                    continue
                size = png_size(f)
                if size is None:
                    errors.append(f"{eid}: {rel} is not a PNG")
                elif max(size) > MAX_PX:
                    errors.append(f"{eid}: {rel} is {size[0]}x{size[1]} px (max {MAX_PX})")
        if not (root / eid / "science.md").exists():
            errors.append(f"{eid}: science.md missing")

    total = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    if total > MAX_TOTAL_MB * 1024 * 1024:
        errors.append(f"events/ is {total / 1e6:.1f} MB (max {MAX_TOTAL_MB} MB)")

    for e in errors:
        print("FAIL:", e)
    print(f"{len(events)} events, {total / 1e6:.2f} MB, {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "events")))
