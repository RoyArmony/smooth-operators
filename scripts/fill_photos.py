"""Add an optical photo to every flood pass that has none (event folders v2, events/<place>/<flood>/).

    python scripts/fill_photos.py                     # all floods
    python scripts/fill_photos.py gerd-blue-nile-ethiopia

For each NISAR pass without a photo: NASA GIBS true colour within ± 5 days, tried in this order of detail:
HLS Sentinel-2 / Landsat (30 m), VIIRS NOAA-20 / Suomi NPP (375 m), MODIS Terra / Aqua (250 m, wide swath).
Kept: the image that covers >= 70 % of the box with the least cloud (bright white pixels); ties go to the
sharper sensor, then the closer day. Writes layers/photo_<date>.jpg, records the source per file
(layers.photo.sources) and the pass's matched.photo / clouds_pct. No login needed (GIBS is open).
"""
import datetime as dt
import io
import json
import sys
from pathlib import Path

import numpy as np
import requests
from PIL import Image

EV = Path(__file__).resolve().parents[1] / "events"
GIBS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
DAYS, MIN_COVER = 5, 0.7
SOURCES = [  # (GIBS layer, name shown, pixel m, picture width px)
    ("HLS_S30_Nadir_BRDF_Adjusted_Reflectance", "HLS Sentinel-2 (30 m)", 30, 1024),
    ("HLS_L30_Nadir_BRDF_Adjusted_Reflectance", "HLS Landsat (30 m)", 30, 1024),
    ("VIIRS_NOAA20_CorrectedReflectance_TrueColor", "VIIRS NOAA-20 (375 m)", 375, 512),
    ("VIIRS_SNPP_CorrectedReflectance_TrueColor", "VIIRS Suomi NPP (375 m)", 375, 512),
    ("MODIS_Terra_CorrectedReflectance_TrueColor", "MODIS Terra (250 m)", 250, 512),
    ("MODIS_Aqua_CorrectedReflectance_TrueColor", "MODIS Aqua (250 m)", 250, 512),
]
D = dt.date.fromisoformat


def fetch(layer, bbox, day, width):
    w, s, e, n = bbox
    h = max(64, round(width * (n - s) / (e - w)))
    p = dict(SERVICE="WMS", REQUEST="GetMap", VERSION="1.3.0", LAYERS=layer, CRS="EPSG:4326",
             BBOX=f"{s},{w},{n},{e}", WIDTH=width, HEIGHT=h, FORMAT="image/jpeg", TIME=day)
    r = requests.get(GIBS, params=p, timeout=90)
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
        return None
    return np.array(Image.open(io.BytesIO(r.content)).convert("RGB"))


def best_photo(bbox, date):
    """-> (day, source name, RGB array, cloud fraction) or None."""
    best = None
    for k in sorted(range(-DAYS, DAYS + 1), key=abs):
        day = (D(date) + dt.timedelta(days=k)).isoformat()
        for rank, (layer, name, _, width) in enumerate(SOURCES):
            try:
                im = fetch(layer, bbox, day, width)
            except Exception:  # noqa: BLE001
                continue
            if im is None:
                continue
            cover = float((im.max(-1) > 12).mean())                 # black = outside the swath / no data
            if cover < MIN_COVER:
                continue
            cloud = float((im.min(-1) > 190).mean())                 # bright white = cloud
            key = (round(cloud, 1), rank, abs(k))                    # least cloud (10 % steps), sharper, closer
            if best is None or key < best[0]:
                best = (key, day, name, im, cloud)
        if best and best[0][0] == 0.0 and best[0][1] <= 1:          # clear HLS found: good enough
            break
    return None if best is None else best[1:]


def fill(folder):
    f = folder / "event.json"
    if not (folder / "layers").is_dir():                      # numbers-only folder (no pictures committed): nothing to show
        print("  no layers/ here (numbers only): skipped")
        return 0
    E = json.loads(f.read_text(encoding="utf-8"))
    missing = [q for q in E.get("passes", []) if "photo" not in (q.get("matched") or {})]
    if not missing:
        return 0
    lay = E["layers"].setdefault("photo", dict(group="optical", sensor="Optical true colour via NASA GIBS",
                                               label="Optical photo (true colour)", legend=None, default=False,
                                               files={}, bounds=[[E["bbox"][1], E["bbox"][0]], [E["bbox"][3], E["bbox"][2]]]))
    src = lay.setdefault("sources", {d: lay.get("sensor", "") for d in lay["files"]})
    n = 0
    for q in missing:
        got = best_photo(E["bbox"], q["date"])
        if not got:
            print(f"  {q['date']}: no optical image within ± {DAYS} d")
            continue
        day, name, im, cloud = got
        out = f"layers/photo_{day}.jpg"
        Image.fromarray(im).save(folder / out, quality=78, optimize=True)
        lay["files"][day] = out
        src[day] = name + " via NASA GIBS"
        q.setdefault("matched", {})["photo"] = day
        q["clouds_pct"] = round(100 * cloud)
        q.setdefault("layers", []).insert(0, "photo") if "photo" not in q.get("layers", []) else None
        n += 1
        print(f"  {q['date']}: {name} {day}, cloud {round(100 * cloud)} %")
    if len(set(src.values())) > 1:
        lay["sensor"] = "Optical true colour via NASA GIBS (HLS / VIIRS / MODIS, see sources)"
    f.write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
    return n


def main(only=None):
    for pl in sorted(EV.glob("*/place.json")):
        if only and pl.parent.name not in only:
            continue
        for fl in json.loads(pl.read_text(encoding="utf-8")).get("floods", []):
            folder = pl.parent / fl["id"]
            if (folder / "event.json").exists():
                print(f"{pl.parent.name}/{fl['id']}")
                print(f"  added {fill(folder)} photo(s)")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
