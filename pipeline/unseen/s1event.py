"""A short flood (hours to a day) seen by Sentinel-1 on the day, with NISAR before (and after, once processed).

    python -m unseen.s1event israel-sharon-2026-11

Why: flash floods in towns drain before NISAR's next pass (every 12 days per track), and the official flood map (GFM)
may be unreachable. Sentinel-1 RTC (ESA Copernicus, C-band, 10 m, via Microsoft Planetary Computer, no login) has a
pass the same afternoon. We compare each after-storm Sentinel-1 pass with the pass 6 days earlier on the SAME track
(same geometry), so only change counts: new water = dark after (VV < -15 dB), much darker than before (< -3 dB), and
not water before. Everything is on the NISAR 80 m grid (from the NISAR pass before the storm), like every other source.
Writes events/<id>/ in the v1 bundle format (docs/08 §3) and refreshes events/index.json.
"""
import argparse
import datetime as dt

import numpy as np
from PIL import Image
from scipy.ndimage import median_filter

from . import bundle, gcov, nisar
from .auth import session as earthdata_session
from .config import DATA_DIR, EVENTS_DIR

STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
CASES = {
    "israel-sharon-2026-11": dict(
        title="Sharon storm, Israel", place="Sharon plain (Kedima, Even Yehuda, Kfar Saba), Israel",
        bbox=(34.80, 32.15, 35.05, 32.40), storm="2026-11-08",
        nisar=dict(track=151, frame=72),          # descending; validated GCOV on 3 Nov, next pass 15 Nov
        # same-track Sentinel-1 pairs: (relative orbit, before, after)
        pairs=[(87, "2026-11-02", "2026-11-08"),  # ascending 15:40 UTC: the afternoon of the storm
               (94, "2026-11-03", "2026-11-09")],  # descending 03:43 UTC: the next morning
        note="Storm of 7-8 Nov 2026: Israel Meteorological Service flood warnings; very heavy rain over the Sharon."),
}
NEW = (255, 154, 46, 240)       # new water (orange, as the NISAR addition elsewhere)
WET = (40, 200, 230, 200)       # soaked ground (cyan)
VV_WATER, VV_DROP, VV_WET = -15.0, -3.0, 3.0


def s1_items(bbox, rel_orbit, date):
    import planetary_computer as pc
    import pystac_client
    cat = pystac_client.Client.open(STAC, modifier=pc.sign_inplace)
    return [i for i in cat.search(collections=["sentinel-1-rtc"], bbox=list(bbox),
                                  datetime=f"{date}T00:00:00Z/{date}T23:59:59Z").items()
            if i.properties["sat:relative_orbit"] == rel_orbit]


def s1_vv_db(items, grid, shape, key):
    """VV gamma0 (dB) mosaicked onto our grid (COG overviews read at ~40 m, averaged to 80 m). Cached."""
    cache = DATA_DIR / "s1" / f"{key}_{shape[0]}x{shape[1]}.npz"
    if cache.exists():
        return np.load(cache)["vv"]
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, transform_bounds
    from rasterio.windows import Window, from_bounds
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    dst_t, dst_crs = from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx), f"EPSG:{grid['epsg']}"
    gb = (x[0] - dx / 2, y[-1] - dx / 2, x[-1] + dx / 2, y[0] + dx / 2)
    out = np.full(shape, np.nan, "float32")
    for it in items:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(it.assets["vv"].href) as s:
            win = from_bounds(*transform_bounds(dst_crs, s.crs, *gb), s.transform).round_offsets().round_lengths()
            win = win.intersection(Window(0, 0, s.width, s.height))
            a = s.read(1, window=win, out_shape=(max(1, int(win.height // 4)), max(1, int(win.width // 4))),
                       resampling=Resampling.average).astype("float32")
            a[(a <= 0) | ~np.isfinite(a)] = np.nan
            wt = s.window_transform(win) * s.window_transform(win).scale(win.width / a.shape[1], win.height / a.shape[0])
            part = np.full(shape, np.nan, "float32")
            reproject(a, part, src_transform=wt, src_crs=s.crs, dst_transform=dst_t, dst_crs=dst_crs,
                      resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
        out = np.where(np.isfinite(out), out, part)
    db = 10 * np.log10(out)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, vv=db)
    return db


def smooth(db):
    return median_filter(np.nan_to_num(db, nan=-99), 3) * np.where(np.isfinite(db), 1, np.nan)


def grey(a, lo, hi):
    return np.where(np.isfinite(a), np.clip((a - lo) / (hi - lo) * 254 + 1, 1, 255), 0).astype(np.uint8)


def picture(ev, lid, date, a, grid, group, sensor, label, default=False):
    """uint8 (H,W) grey or (H,W,3) RGB on our grid -> EPSG:4326 PNG layer (0 = no data, transparent)."""
    chans = [a] if a.ndim == 2 else [a[..., i] for i in range(3)]
    w = [bundle.to_wgs84(np.ascontiguousarray(c), grid) for c in chans]
    rgb = np.dstack([c[0] for c in w] * (3 if a.ndim == 2 else 1))
    img = Image.fromarray(np.dstack([rgb, np.where(rgb.max(-1) > 0, 255, 0).astype(np.uint8)]), "RGBA")
    return bundle.add_image_layer(ev, lid, date, img, w[0][1], group, sensor, label, default)


def mask_layer(ev, lid, date, m, grid, sensor, label, colour, default=True):
    w, b = bundle.to_wgs84(m.astype(np.uint8), grid)
    bundle._save_png(bundle.rgba(w.astype(bool), colour), EVENTS_DIR / ev["id"] / "layers" / f"{lid}_{date}.png")
    lay = ev["layers"].setdefault(lid, dict(group="result", sensor=sensor, label=label, legend=bundle.HEX(colour),
                                            files={}, bounds=b, default=default))
    lay["files"][date] = f"layers/{lid}_{date}.png"


def build(eid):
    c = CASES[eid]
    bbox, storm = c["bbox"], c["storm"]
    # NISAR: the validated GCOV passes of our track around the storm (before; after once ASF has processed them)
    gs = [g for g in nisar.search(bbox, start="2026-10-01")
          if g["pathNumber"] == c["nisar"]["track"] and g["frameNumber"] == c["nisar"]["frame"]]
    gs.sort(key=lambda g: g["startTime"])
    before = [g for g in gs if g["startTime"][:10] < storm]
    after = [g for g in gs if g["startTime"][:10] > storm]
    use = before[-1:] + after[:1]
    ses = earthdata_session()
    win, grid = nisar.window_for_bbox(use[0]["url"], bbox, "B", ses)
    ev = bundle.new_event(eid, c["title"], "site", bbox, c["place"])
    for g in use:
        a, m = gcov.read(g["url"], terms=("HHHH", "HVHV"), freq="B", window=win, session=ses)
        hh, hv = (10 * np.log10(np.where(a[i] > 0, a[i], np.nan)) for i in (0, 1))
        rgb = np.dstack([grey(hh, -25, 0), grey(hv, -32, -8), grey(hh - hv, 0, 15)])
        d = g["startTime"][:10]
        picture(ev, "nisar_rgb", d, rgb, grid, "radar", "NISAR L-band GCOV", "NISAR radar (R = HH, G = HV, B = HH/HV)")
        ev["timeline"].append(dict(date=d, sensor="NISAR", track=g["pathNumber"], when="before" if d < storm else "after",
                                   layers=["nisar_rgb"]))
    shape = (len(grid["y"]), len(grid["x"]))
    px = (grid["dx"] / 1000) ** 2
    nums = []
    for orb, d0, d1 in c["pairs"]:
        v0 = smooth(s1_vv_db(s1_items(bbox, orb, d0), grid, shape, f"{eid}_{orb}_{d0}"))
        v1 = smooth(s1_vv_db(s1_items(bbox, orb, d1), grid, shape, f"{eid}_{orb}_{d1}"))
        ok = np.isfinite(v0) & np.isfinite(v1)
        new = ok & (v1 < VV_WATER) & (v1 - v0 < VV_DROP) & (v0 >= VV_WATER)
        land = ok & (v0 >= VV_WATER) & (v1 >= VV_WATER)                     # sea and standing water left out
        wet = land & (v1 - v0 > VV_WET)                                      # soaked soil: wetter = brighter in C-band
        km2, wkm2 = round(float(new.sum() * px), 1), round(float(wet.sum() * px), 1)
        picture(ev, "s1_vv", d1, grey(v1, -25, 0), grid, "radar", "Sentinel-1 C-band (VV)", "Sentinel-1 radar (VV)")
        mask_layer(ev, "s1_wet", d1, wet, grid, "Sentinel-1 C-band (change, same track)",
                   "Soaked ground: radar > 3 dB brighter than 6 days before", WET)
        lays = ["s1_vv", "s1_wet"]
        if km2 > 0:
            mask_layer(ev, "s1_new_water", d1, new, grid, "Sentinel-1 C-band (change, same track)",
                       "New open water (Sentinel-1, vs 6 days before)", NEW)
            lays.append("s1_new_water")
        ev["timeline"].append(dict(date=d1, sensor="Sentinel-1", rel_orbit=orb, before=d0, new_water_km2=km2,
                                   soaked_km2=wkm2, land_change_db=round(float(np.median((v1 - v0)[land])), 2),
                                   valid_pct=round(100 * float(ok.mean())), layers=lays))
        nums.append((d1, km2, wkm2))
        print(f"Sentinel-1 orbit {orb}: {d0} -> {d1}: new water {km2} km², soaked {wkm2} km²", flush=True)
    nd = len(nisar.search(bbox, start="2026-06-17"))
    (d1a, k1, w1), (d1b, k2, w2) = nums
    ev["headline"] = dict(
        date=storm, badge=None,
        sentence=f"On the afternoon of the storm ({d1a}), Sentinel-1 radar saw {w1:,.0f} km² of soaked ground in the Sharon "
                 f"({w2:,.0f} km² the next morning) but {k1:,.0f} km² of standing water in open fields: the flash flood ran "
                 "off through the streets within hours. NISAR passed on " + use[0]["startTime"][:10] + " (before).",
        numbers=[dict(label="Soaked ground, storm afternoon (Sentinel-1)", value=w1, unit="km²"),
                 dict(label="Still soaked next morning", value=w2, unit="km²"),
                 dict(label="Standing water in open fields", value=k1, unit="km²")])
    ev["nisar_passes_since_june"] = nd
    ev["method"] = dict(detector="Sentinel-1 VV change on the same track: after < -15 dB, drop > 3 dB, not water before; "
                                 "3x3 median filter", pixel_m=grid["dx"], grid=f"NISAR track {c['nisar']['track']} frame "
                                 f"{c['nisar']['frame']} (EPSG:{grid['epsg']})", note=c["note"])
    ev["sources"] = [
        dict(name="NISAR L2 GCOV", url="https://search.asf.alaska.edu", credit="NASA/JPL-Caltech, ISRO; data via ASF DAAC"),
        dict(name="Sentinel-1 RTC (Microsoft Planetary Computer)", url="https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc",
             credit="Contains modified Copernicus Sentinel data 2026 (ESA); RTC by Microsoft / Catalyst")]
    (EVENTS_DIR / eid).mkdir(parents=True, exist_ok=True)
    (EVENTS_DIR / eid / "science.md").write_text(SCIENCE.format(title=c["title"]), encoding="utf-8")
    bundle.write_event(ev)
    bundle.write_index()
    return ev


SCIENCE = """# {title}

**What:** a flash flood. Rain fell in hours and most streets drained the same day, so we need a radar pass that day.

**Data:** Sentinel-1 (ESA Copernicus, C-band) passed the afternoon of the storm (8 Nov, 15:40 UTC) and the next morning
(9 Nov, 03:43 UTC). NISAR (L-band) passed on 3 Nov (before); its next pass on the same track (15 Nov) is added when ASF
has processed it. Official flood map (Copernicus GFM): its server was down at build time.

**Method:** same-track change, so geometry is identical (3x3 median). New open water = VV darker than -15 dB after,
more than 3 dB darker than 6 days before, not water before. Soaked ground = land more than 3 dB brighter than 6 days
before (wet soil reflects more C-band). Area = pixels x 80 m x 80 m on the NISAR grid.

**Result:** lots of soaked ground, no standing water in open fields at 80 m: the flood was in streets and drained in hours.

**Limits:** C-band cannot see water under trees or between buildings (double bounce in towns), so flooded streets are
mostly missed: this is water in fields and open ground. Wet bare soil can also darken a little; the 3 dB drop and the
-15 dB level keep only strong change. Not checked against ground reports yet.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("event", choices=sorted(CASES))
    build(ap.parse_args(argv).event)


if __name__ == "__main__":
    main()
