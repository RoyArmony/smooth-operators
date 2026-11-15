"""Which flood detector made each piece of NISAR data the site shows? Fails if anything shown is not detector v3.

Checks every data file the pages load:
  events/<id>/event.json (v1, listed in events/index.json), events/<place>/<flood>/event.json (v2),
  events/<place>/history/event.json (NISAR side), events/world/event.json (sum of the v1 bundles),
  site/viewer/sites/<id>/site.json (Explorer site pages).
Not NISAR-detector outputs (reported, not failed): Sentinel-1 / RADARSAT-1 only bundles, mock bundles, map tiles.

    python scripts/check_detector.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV, SITES = ROOT / "events", ROOT / "site" / "viewer" / "sites"
V3 = "fused v3"
KEEP = {"sylhet-haor-validation/2026-10-flood": "doc33"}     # kept on another detector by team decision (15.11)
bad, rows = [], []


def note(kind, path, det, ok, why=""):
    rows.append((kind, str(path.relative_to(ROOT)), (det or "-")[:60], "ok" if ok else ("n/a" if ok is None else "NOT v3"), why))
    if ok is False:
        bad.append(path)


idx = json.loads((EV / "index.json").read_text(encoding="utf-8"))
for e in idx.get("events", []):
    f = EV / e["id"] / "event.json"
    E = json.loads(f.read_text(encoding="utf-8"))
    det = (E.get("method") or {}).get("detector") if isinstance(E.get("method"), dict) else None
    if e["id"] == "world":
        continue
    if E.get("mock"):
        note("v1", f, det, None, "mock bundle (not real NISAR detection)")
    elif det and det.startswith("Sentinel-1"):
        note("v1", f, det, None, "Sentinel-1 change, no NISAR detector")
    else:
        note("v1", f, det, bool(det and det.startswith(V3)))
for p in idx.get("places", []):
    for fl in p.get("floods", []):
        f = EV / (p.get("folder") or p["id"]) / fl["id"] / "event.json"
        E = json.loads(f.read_text(encoding="utf-8"))
        det = E["method"]["detector"]
        keep = KEEP.get(f"{p.get('folder') or p['id']}/{fl['id']}")
        note("v2", f, det, None if keep else det.startswith(V3), f"kept on {keep} (team decision)" if keep else "")
    if p.get("history"):
        f = EV / (p.get("folder") or p["id"]) / "history" / "event.json"
        E = json.loads(f.read_text(encoding="utf-8"))
        det = (E.get("method") or {}).get("nisar")
        note("history", f, det, bool(det and det.startswith(V3)))
# world = sum over the v1 bundles it lists: each of those must be v3
W = json.loads((EV / "world" / "event.json").read_text(encoding="utf-8"))
wok = True
for s in W.get("sites", []):
    if not s.get("compared"):
        continue
    E = json.loads((EV / s["id"] / "event.json").read_text(encoding="utf-8"))
    b = next(t for t in E["timeline"] if t["date"] == E["headline"]["date"])
    same = abs(b["stats"]["nisar_adds"] - s["nisar_adds_km2"]) < 0.05
    wok &= E["method"]["detector"].startswith(V3) and same
note("world", EV / "world" / "event.json", "sum of v1 bundles", wok, "" if wok else "a site is not v3 or its number differs")
# Explorer site pages
for f in sorted(SITES.glob("*/site.json")):
    S = json.loads(f.read_text(encoding="utf-8"))
    if S.get("history"):
        note("site", f, "RADARSAT-1 history page", None, "superseded by events/<place>/history in the Explorer")
        continue
    det = (S.get("detector") or {}).get("detector")
    note("site", f, det, det == V3)

w = [max(len(r[i]) for r in rows) for i in range(4)]
for r in rows:
    print("  ".join(c.ljust(w[i]) for i, c in enumerate(r[:4])), r[4])
print(f"\n{len(rows)} outputs, {len(bad)} not v3")
sys.exit(1 if bad else 0)
