"""Give every pass of a v2 flood folder an optical photo: VIIRS true colour of the pass day (NASA GIBS, ~375 m).

Nearest day within ± 2 d when the pass day has a swath gap. Passes that already have an HLS photo keep it. Usage (from the repo root):
    python scripts/add_viirs_photos.py                      # all events/<place>/<YYYY-MM>-flood folders
    python scripts/add_viirs_photos.py assam-brahmaputra    # one place
"""
import datetime as dt
import glob
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline"))
from unseen import lance  # noqa: E402

only = set(sys.argv[1:])
for f in sorted(glob.glob("events/*/20*-flood/event.json")):
    p = pathlib.Path(f)
    if only and p.parts[1] not in only:
        continue
    E = json.loads(p.read_text(encoding="utf-8"))
    if E.get("kind") == "validation":
        continue
    lp = E["layers"].get("photo")
    changed = False
    for P in E["passes"]:
        if "photo" in P["layers"]:
            continue
        lay = None
        for off in (0, -1, 1, -2, 2):                       # the pass day, else the nearest day with an image (swath gaps)
            d = (dt.date.fromisoformat(P["date"]) + dt.timedelta(days=off)).isoformat()
            name = f"photo_{d}.jpg"
            try:
                lay = lance.truecolor(E["bbox"], d, p.parent / "layers" / name, width=512); break
            except Exception as e:  # noqa: BLE001
                print(f"[warn] {p.parts[1]} {d}: {e!r}"[:120])
        if not lay:
            continue
        sat = {"VIIRS_NOAA20": "VIIRS (NOAA-20)", "VIIRS_SNPP": "VIIRS (Suomi NPP)", "MODIS_Terra": "MODIS (Terra)"}
        sensor = next((v for k, v in sat.items() if lay.startswith(k)), lay)
        if lp is None:
            w, s, e, n = E["bbox"]
            lp = E["layers"]["photo"] = dict(group="optical", sensor=f"{sensor} true colour via NASA GIBS",
                                             label="Optical photo (true colour, same day)", legend=None, default=False,
                                             files={}, bounds=[[s, w], [n, e]], sensors={})
        lp.setdefault("sensors", {})[d] = f"{sensor} true colour via NASA GIBS"
        lp["files"][d] = f"layers/{name}"
        P["matched"]["photo"] = d
        P["layers"].append("photo")
        changed = True
        print(p.parts[1], d, sensor)
    if changed:
        p.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")

# v1 bundles (events/<id>/event.json, no v2 folder): a photo for each date that has an official map
for f in sorted(glob.glob("events/*/event.json")):
    p = pathlib.Path(f)
    if only and p.parts[1] not in only:
        continue
    E = json.loads(p.read_text(encoding="utf-8"))
    if E.get("version") == 2 or E.get("hidden") or "gfm_flood" not in E.get("layers", {}) or any(p.parent.glob("20*-flood/event.json")):
        continue
    lp = E["layers"].get("photo")
    have = set((lp or {}).get("files", {}))
    changed = False
    for d0 in E["layers"]["gfm_flood"]["files"]:
        if have:
            continue
        lay = None
        for off in (0, -1, 1, -2, 2):
            d = (dt.date.fromisoformat(d0) + dt.timedelta(days=off)).isoformat()
            name = f"photo_{d}.jpg"
            try:
                lay = lance.truecolor(E["bbox"], d, p.parent / "layers" / name, width=512); break
            except Exception as e:  # noqa: BLE001
                print(f"[warn] {p.parts[1]} {d}: {e!r}"[:120])
        if not lay:
            continue
        sat = {"VIIRS_NOAA20": "VIIRS (NOAA-20)", "VIIRS_SNPP": "VIIRS (Suomi NPP)", "MODIS_Terra": "MODIS (Terra)"}
        sensor = next((v for k, v in sat.items() if lay.startswith(k)), lay)
        if lp is None:
            lp = E["layers"]["photo"] = dict(group="optical", sensor=f"{sensor} true colour via NASA GIBS", label="Optical photo (true colour)",
                                             legend=None, default=False, files={}, bounds=E["layers"]["gfm_flood"]["bounds"])
        lp["files"][d] = f"layers/{name}"
        changed = True
        print(p.parts[1], d, sensor)
    if changed:
        p.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
