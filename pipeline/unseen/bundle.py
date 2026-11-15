"""Write site bundles for the web viewer, to the contract in docs/08-Plan-data.md §3:

  events/index.json                         all events (id, title, place, date, bbox, kind, headline)
  events/<id>/event.json                    headline, timeline, layers, validation, sources
  events/<id>/layers/<layer>_<YYYY-MM-DD>.png  RGBA, EPSG:4326 bounds, <= 2048 px

Every number the site shows comes from event.json; this module is the only writer."""
import json

import numpy as np
from PIL import Image

from .config import EVENTS_DIR

MAX_PX = 2048
# layer id -> (group, colour). Ids and groups from docs/09-Plan-UI.md.
STYLE = {
    "gfm_flood": ("official", (40, 130, 255, 235)),
    "gfm_excluded": ("official", "hatch"),
    "dswx_s1": ("official", (90, 200, 255, 220)),
    "nisar_water": ("result", (40, 130, 255, 235)),
    "nisar_floodveg": ("result", (40, 200, 120, 235)),
    "nisar_adds": ("result", (255, 150, 40, 245)),
    "rcm_water": ("validation", (255, 80, 80, 235)),
    "rs1_water": ("result", (40, 130, 255, 235)),          # RADARSAT-1 flood (history bundles)
}
HEX = lambda c: "#%02x%02x%02x" % c[:3]


def to_wgs84(arr, grid, nodata=0):
    """Reproject a (H,W) array on our UTM grid to EPSG:4326 (nearest). Returns (array, bounds [[s,w],[n,e]])."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, calculate_default_transform, reproject
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    H, W = arr.shape
    src_t = from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx)
    crs = f"EPSG:{grid['epsg']}"
    l, t = x[0] - dx / 2, y[0] + dx / 2
    r, b = l + W * dx, t - H * dx
    dst_t, w2, h2 = calculate_default_transform(crs, "EPSG:4326", W, H, l, b, r, t)
    out = np.full((h2, w2), nodata, arr.dtype)
    reproject(arr, out, src_transform=src_t, src_crs=crs, dst_transform=dst_t, dst_crs="EPSG:4326",
              resampling=Resampling.nearest, src_nodata=nodata, dst_nodata=nodata)
    w, n = dst_t.c, dst_t.f
    e, s = w + w2 * dst_t.a, n + h2 * dst_t.e
    return out, [[round(s, 5), round(w, 5)], [round(n, 5), round(e, 5)]]


def rgba(mask, colour):
    """Boolean mask -> RGBA uint8. colour: (r,g,b,a) or 'hatch' (grey diagonal stripes on dark, for "cannot see")."""
    H, W = mask.shape
    a = np.zeros((H, W, 4), np.uint8)
    if colour == "hatch":
        a[mask] = (60, 60, 70, 150)
        yy, xx = np.mgrid[:H, :W]
        a[((xx + yy) % 6 < 2) & mask] = (200, 200, 210, 230)
    else:
        a[mask] = colour
    return a


def _save_png(a, path):
    im = Image.fromarray(a)
    if max(im.size) > MAX_PX:
        k = MAX_PX / max(im.size)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, optimize=True)


def add_mask_layer(ev, lid, date, mask, grid, sensor, label=None, default=False):
    """Add one dated mask layer to an event dict (in memory) and write its PNG. Returns the layer entry."""
    group, colour = STYLE[lid]
    m, bounds = to_wgs84(mask.astype(np.uint8), grid)
    _save_png(rgba(m.astype(bool), colour), EVENTS_DIR / ev["id"] / "layers" / f"{lid}_{date}.png")
    lay = ev["layers"].setdefault(lid, dict(group=group, sensor=sensor, label=label or lid,
                                            legend="hatch" if colour == "hatch" else HEX(colour),
                                            files={}, bounds=bounds, default=default))
    lay["files"][date] = f"layers/{lid}_{date}.png"
    return lay


def add_image_layer(ev, lid, date, img, bounds, group, sensor, label=None, default=False):
    """Add an RGB(A) picture already in EPSG:4326 (e.g. an HLS photo) with its bounds [[s,w],[n,e]]."""
    _save_png(np.asarray(img.convert("RGBA")), EVENTS_DIR / ev["id"] / "layers" / f"{lid}_{date}.png")
    lay = ev["layers"].setdefault(lid, dict(group=group, sensor=sensor, label=label or lid, legend=None,
                                            files={}, bounds=bounds, default=default))
    lay["files"][date] = f"layers/{lid}_{date}.png"
    return lay


def new_event(eid, title, kind, bbox, place=None):
    return dict(id=eid, title=title, place=place or title, kind=kind, bbox=[round(v, 4) for v in bbox],
                headline=dict(date=None, sentence="", numbers=[], badge=None), timeline=[], layers={},
                validation={}, sources=[])


SCIENCE = """# {title}

**What:** water NISAR (L-band radar) sees inside the official flood map's "cannot see" area (Copernicus GFM exclusion mask).

**Method:** per NISAR pass: open water + water under vegetation from HH/HV (`pipeline/unseen/detect.py`), permanent water
removed; compared with GFM within 2 days; area = 80 m pixels. Shared method: `events/methods.md`.

**Limits:** a NISAR detection inside GFM's blank is a candidate, not proven flood; validation: docs/10-Results.md.
"""


def write_event(ev):
    d = EVENTS_DIR / ev["id"]
    d.mkdir(parents=True, exist_ok=True)
    ev["headline"]["numbers"] = ev["headline"]["numbers"][:3]           # contract: at most 3
    if not (d / "science.md").exists():
        (d / "science.md").write_text(SCIENCE.format(title=ev["title"]), encoding="utf-8")
    ev["timeline"].sort(key=lambda r: r["date"])
    (d / "event.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
    return d / "event.json"


def pooled(rows):
    """Improvement over the whole window, not one pass: rows = [(date, baseline flood km², NISAR addition km²)].
    pct = 100 × Σ NISAR addition / Σ baseline flood (None if Σ flood < 5 km²). Sums are km² × passes, not one area."""
    rows = [r for r in rows if r[1] is not None and r[2] is not None]
    if not rows:
        return None
    B, A = sum(r[1] for r in rows), sum(r[2] for r in rows)
    return dict(flood_km2=round(B, 1), adds_km2=round(A, 1), pct=round(100 * A / B) if B >= 5 else None,
                n=len(rows), first=min(r[0] for r in rows), last=max(r[0] for r in rows),
                rule="100 × Σ NISAR addition / Σ official flood, all passes")


def write_index():
    """Rebuild events/index.json: "events" from every events/<id>/event.json (v1), "places" from events/<place>/place.json (v2)."""
    out = []
    for f in sorted(EVENTS_DIR.glob("*/event.json")):
        e = json.loads(f.read_text(encoding="utf-8"))
        if e.get("hidden"):                         # kept on disk, left out of the Explorer list
            continue
        h = e.get("headline", {})
        tot = pooled([(r["date"], (r.get("stats") or {}).get("gfm_flood"), (r.get("stats") or {}).get("nisar_adds"))
                      for r in e.get("timeline", []) if r.get("date")])
        out.append(dict(id=e["id"], title=e["title"], place=e.get("place"), date=h.get("date"), bbox=e["bbox"],
                        kind=e["kind"], headline=dict(sentence=h.get("sentence"), numbers=h.get("numbers", [])),
                        **(dict(total=tot) if tot else {})))
    places = []                                    # v2 (docs/12): events/<place>/place.json -> its floods + history
    for f in sorted(EVENTS_DIR.glob("*/place.json")):
        p = json.loads(f.read_text(encoding="utf-8"))
        for fl in p.get("floods", []):              # v2 flood: pooled over its passes, against its main baseline
            ef = f.parent / fl["id"] / "event.json"
            if ef.exists():
                E = json.loads(ef.read_text(encoding="utf-8"))
                mb = (E.get("summary") or {}).get("baseline")
                tot = pooled([(q["date"], q["baselines"][mb].get("flood_km2"), q["baselines"][mb].get("nisar_adds_km2"))
                              for q in E.get("passes", []) if mb in q.get("baselines", {})])
                if tot:
                    fl["total"] = dict(tot, baseline=mb)
        places.append(dict(id=p["id"], folder=f.parent.name, name=p["name"], country=p.get("country"), bbox=p["bbox"],
                           floods=p.get("floods", []), history=p.get("history"), validation=p.get("validation") or []))
    idx = dict(version=2 if places else 1, events=out, **(dict(places=places) if places else {}))
    (EVENTS_DIR / "index.json").write_text(json.dumps(idx, indent=1, ensure_ascii=False), encoding="utf-8")
    return out
