"""What is inside the official flood map's "cannot see" area? Land cover of the GFM exclusion mask, per site.

For each compared site in events/world/event.json: take the GFM exclusion layer of the site's pass from its bundle
(events/<id>/layers/gfm_excluded_<date>.png, lat/lon bounds in event.json), overlay ESA WorldCover 2021 (public COGs on
AWS, ~80 m overview) and report the share of the blank per land class. Pixels weighted by cos(latitude).

GFM is Sentinel-1 C-band radar: clouds do not blank it. Its exclusion mask covers places where radar flood mapping
is unreliable (dense vegetation, cities, radar shadow / layover, permanently dark ground such as sand).

    python scripts/gfm_blank_landcover.py            # -> events/world/gfm_blank.json + table on stdout
"""
import json
import math
import os
import pathlib
import sys

import numpy as np
from PIL import Image
import rasterio
from rasterio.windows import from_bounds

ROOT = pathlib.Path(__file__).resolve().parents[1]
EV = ROOT / "events"
URL = "/vsicurl/https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{t}_Map.tif"
GROUP = {10: "forest", 95: "forest", 50: "built-up", 40: "cropland", 90: "wetland", 20: "shrub & grass", 30: "shrub & grass",
         60: "bare / sand", 80: "water", 70: "other", 100: "other", 0: "no data"}
ORDER = ["forest", "built-up", "cropland", "wetland", "shrub & grass", "bare / sand", "water", "other", "no data"]

os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
if os.path.exists("/root/.ccr/ca-bundle.crt"):
    os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt")


def tile(lat, lon):
    la, lo = 3 * math.floor(lat / 3), 3 * math.floor(lon / 3)
    return f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"


def worldcover(lat, lon, bbox, overview=3):
    """WorldCover class at each (lat, lon) point (arrays), reading only the bbox from each 3x3° tile."""
    out = np.zeros(lat.shape, np.uint8)
    s, w, n, e = bbox
    tiles = {tile(a, b) for a in np.arange(s, n + 1e-9, 1.0).tolist() + [n] for b in np.arange(w, e + 1e-9, 1.0).tolist() + [e]}
    for t in sorted(tiles):
        try:
            with rasterio.open(URL.format(t=t), overview_level=overview) as d:
                b = d.bounds
                win = from_bounds(max(w, b.left), max(s, b.bottom), min(e, b.right), min(n, b.top), d.transform)
                if win.width < 1 or win.height < 1:
                    continue
                win = win.round_offsets().round_lengths()
                a = d.read(1, window=win); tr = d.window_transform(win)
        except Exception as x:  # noqa: BLE001  (no tile = open ocean)
            print(f"  [skip tile {t}: {str(x)[:60]}]", file=sys.stderr)
            continue
        c = ((lon - tr.c) / tr.a).astype(int); r = ((lat - tr.f) / tr.e).astype(int)
        m = (r >= 0) & (r < a.shape[0]) & (c >= 0) & (c < a.shape[1]) & (out == 0)
        out[m] = a[r[m], c[m]]
    return out


def site(sid, date):
    ev = json.loads((EV / sid / "event.json").read_text())
    L = ev["layers"]["gfm_excluded"]
    f = L["files"].get(date)
    if not f:
        return None
    (s, w), (n, e) = L["bounds"]
    a = np.array(Image.open(EV / sid / f).convert("RGBA"))[..., 3] > 0
    H, W = a.shape
    k = max(1, round(max(H, W) / 1000))                      # ~1,000 px across is plenty at 80 m land cover
    a = a[::k, ::k]; H, W = a.shape
    lat = n - (np.arange(H) + .5) * (n - s) / H; lon = w + (np.arange(W) + .5) * (e - w) / W
    LON, LAT = np.meshgrid(lon, lat)
    lc = worldcover(LAT[a], LON[a], (s, w, n, e))
    wt = np.cos(np.radians(LAT[a]))
    tot = wt.sum()
    share = {}
    for code, g in GROUP.items():
        share[g] = share.get(g, 0) + float(wt[lc == code].sum() / tot) if tot else 0
    km2 = next((t["stats"]["gfm_excluded"] for t in ev.get("timeline", []) if t.get("date") == date), None)
    return dict(id=sid, date=date, cannot_see_km2=km2, share={g: round(share.get(g, 0), 3) for g in ORDER if share.get(g, 0) > 0})


def main():
    world = json.loads((EV / "world" / "event.json").read_text())
    rows = []
    for s in world["sites"]:
        if not s.get("compared"):
            continue
        r = site(s["id"], s["date"])
        if r is None:
            print(f"{s['id']}: no GFM blank layer for {s['date']}", file=sys.stderr); continue
        r["title"] = s["title"]; rows.append(r)
        print(f"{s['title'][:34]:34} {r['cannot_see_km2'] or 0:8.1f} km²  " + "  ".join(f"{g} {v:.0%}" for g, v in r["share"].items()))
    km = sum(r["cannot_see_km2"] or 0 for r in rows)
    tot = {g: round(sum((r["cannot_see_km2"] or 0) * r["share"].get(g, 0) for r in rows) / km, 3) for g in ORDER} if km else {}
    tot = {g: v for g, v in tot.items() if v > 0}
    print(f"\nAll {len(rows)} sites: {km:,.0f} km² cannot see · " + "  ".join(f"{g} {v:.0%}" for g, v in tot.items()))
    out = dict(what="Land cover (ESA WorldCover 2021) of the Copernicus GFM exclusion mask ('cannot see'), each site's compared pass",
               script="scripts/gfm_blank_landcover.py", clouds_note="GFM is Sentinel-1 radar: 0% of its blank is cloud.",
               total=dict(cannot_see_km2=round(km, 1), share=tot), sites=rows)
    (EV / "world" / "gfm_blank.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
