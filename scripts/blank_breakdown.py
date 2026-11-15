"""Split each official map's "cannot see" area into main groups, for one event folder with both baselines.

Radar map (Copernicus GFM, Sentinel-1): blank = its exclusion mask (vegetation, city, radar shadow). Never cloud.
Optical map (NASA OPERA DSWx-HLS): blank = cloud / cloud shadow (WTR class 253; snow/ice 252 if any).
Each blank is split by ESA WorldCover 2021 land cover underneath, and we measure where BOTH maps are blind
(only NISAR sees there). Inputs: the folder's gfm_classes / dswx_classes PNG layers (same grid, EPSG:4326).

    python scripts/blank_breakdown.py mekong-delta-vietnam/2026-09-flood    # -> <folder>/blanks.json
"""
import json
import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gfm_blank_landcover import GROUP, ORDER, worldcover  # noqa: E402

EV = pathlib.Path(__file__).resolve().parents[1] / "events"
GREY, CLOUD = (140, 140, 150), (235, 235, 240)      # eventfolder.C["blank"], C["clouds"]
MAIN = ["forest", "cropland", "built-up", "wetland", "shrub & grass", "water", "other"]


def mask(path, rgb):
    a = np.array(Image.open(path).convert("RGBA"))
    return (a[..., 3] > 0) & np.all(a[..., :3] == rgb, -1)


def main(folder):
    F = EV / folder
    e = json.loads((F / "event.json").read_text())
    g, o = e["layers"]["gfm_classes"], e["layers"]["dswx_classes"]
    (s, w), (n, east) = g["bounds"]
    H, W = np.array(Image.open(F / next(iter(g["files"].values())))).shape[:2]
    lat = n - (np.arange(H) + .5) * (n - s) / H; lon = w + (np.arange(W) + .5) * (east - w) / W
    LON, LAT = np.meshgrid(lon, lat)
    px = ((n - s) / H * 111.32) * ((east - w) / W * 111.32 * np.cos(np.radians(LAT)))     # km² per pixel
    print("land cover ...", file=sys.stderr)
    lc = np.vectorize(lambda c: GROUP.get(int(c), "other"))(worldcover(LAT, LON, (s, w, n, east), overview=2))
    lc = np.where(np.isin(lc, MAIN), lc, "other")
    out = dict(what="Each official map's 'cannot see' area split by cause and by land cover underneath (ESA WorldCover 2021)",
               script="scripts/blank_breakdown.py", box_km2=round(float(px.sum()), 1), passes=[])
    for p in e["passes"]:
        m = p.get("matched", {})
        if "gfm" not in m or "dswx" not in m:
            continue
        G = mask(F / g["files"][m["gfm"]], GREY); O = mask(F / o["files"][m["dswx"]], CLOUD)
        km = lambda x: round(float(px[x].sum()), 1)                                        # noqa: E731
        split = lambda x: {k: km(x & (lc == k)) for k in MAIN if km(x & (lc == k)) >= 0.5}  # noqa: E731
        r = dict(nisar=p["date"], gfm=m["gfm"], dswx=m["dswx"],
                 gfm_blank=dict(km2=km(G), cause={"vegetation, city, radar shadow": km(G), "cloud": 0.0}, landcover=split(G)),
                 dswx_blank=dict(km2=km(O), cause={"cloud / cloud shadow": km(O)}, landcover=split(O)),
                 both_blind=dict(km2=km(G & O), landcover=split(G & O)),
                 stored=dict(gfm=p["baselines"]["gfm"]["cannot_see_km2"], dswx=p["baselines"]["dswx"]["cannot_see_km2"]))
        out["passes"].append(r)
        print(f"{p['date']}  GFM {m['gfm']} blank {r['gfm_blank']['km2']:7.1f} (stored {r['stored']['gfm']})  "
              f"DSWx {m['dswx']} cloud {r['dswx_blank']['km2']:7.1f} (stored {r['stored']['dswx']})  both {r['both_blind']['km2']:7.1f}")
        for k in ("gfm_blank", "dswx_blank", "both_blind"):
            print(f"   {k:10}", "  ".join(f"{a} {v:,.0f}" for a, v in r[k]["landcover"].items()))
    (F / "blanks.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "mekong-delta-vietnam/2026-09-flood")
