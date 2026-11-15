"""Copernicus Global Flood Monitoring (GFM, Sentinel-1) on our NISAR grid: its flood extent and its exclusion mask
(where GFM says Sentinel-1 cannot map floods: dense forest, cities, radar shadow...). Open STAC, no login.
Lets us show what NISAR adds to the official map: water inside GFM's declared blind spots."""
import datetime as dt
import numpy as np
import requests

from .config import DATA_DIR

STAC = "https://stac.eodc.eu/api/v1/search"
CACHE = DATA_DIR / "gfm"


def search(bbox, date, days=3):
    d = dt.date.fromisoformat(str(date))
    q = dict(collections=["GFM"], bbox=list(bbox), limit=50,
             datetime=f"{d - dt.timedelta(days=days)}T00:00:00Z/{d + dt.timedelta(days=days)}T23:59:59Z")
    r = requests.post(STAC, json=q, timeout=60)
    r.raise_for_status()
    return r.json().get("features", [])


def _get(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / url.rsplit("/", 1)[-1]
    if not f.exists():
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        f.write_bytes(r.content)
    return f


def _warp(path, grid, out):
    """Nearest-neighbour onto our grid; keeps the max over tiles (0 = no, 1 = yes, 255 = no data → skipped)."""
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_origin
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    dst_t = from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx)
    tmp = np.full(out.shape, 255, np.uint8)
    with rasterio.open(path) as s:
        reproject(rasterio.band(s, 1), tmp, dst_transform=dst_t, dst_crs=f"EPSG:{grid['epsg']}",
                  resampling=Resampling.nearest, src_nodata=255, dst_nodata=255)
    ok = tmp != 255
    out[ok] = np.where(out[ok] == 255, tmp[ok], np.maximum(out[ok], tmp[ok]))


def _cached_feats(bbox, date, days):
    """Offline fallback when the GFM STAC is down: STAC-like items built from tiles already in data/gfm
    (ENSEMBLE_FLOOD / _EXCLAYER / _OBSWATER_<YYYYMMDDTHHMMSS>_..._<tile>.tif), kept if the tile overlaps the bbox."""
    import glob, os, re
    import rasterio
    from rasterio.warp import transform_bounds
    d0 = dt.date.fromisoformat(str(date))
    out = []
    for f in glob.glob(str(CACHE / "ENSEMBLE_FLOOD_*.tif")):
        m = re.match(r"ENSEMBLE_FLOOD_(\d{8})T(\d{6})_(.*)\.tif$", os.path.basename(f))
        if not m:
            continue
        day = dt.date(int(m[1][:4]), int(m[1][4:6]), int(m[1][6:]))
        if abs((day - d0).days) > days:
            continue
        with rasterio.open(f) as s:
            w, so, e, n = transform_bounds(s.crs, "EPSG:4326", *s.bounds)
        if e < bbox[0] or w > bbox[2] or n < bbox[1] or so > bbox[3]:
            continue
        rest = f"{m[1]}T{m[2]}_{m[3]}"
        assets = {"ensemble_flood_extent": {"href": f}}
        for key, pre in (("exclusion_mask", "ENSEMBLE_EXCLAYER_"), ("ensemble_water_extent", "ENSEMBLE_OBSWATER_")):
            g = CACHE / f"{pre}{rest}.tif"
            if g.exists():
                assets[key] = {"href": str(g)}
        out.append({"properties": {"datetime": f"{day.isoformat()}T{m[2][:2]}:{m[2][2:4]}:{m[2][4:]}Z"}, "assets": assets})
    return out


def on_grid(bbox, date, grid, shape, days=3, min_cover=0.3):
    """GFM flood extent and exclusion mask nearest to `date`, on our grid. Returns dict or None.
    Takes the closest day whose scenes cover >= min_cover of our grid AND carry an exclusion mask
    (some GFM items lack it; without it the gap can't be measured)."""
    try:
        feats = search(bbox, date, days)
    except Exception as e:  # noqa: BLE001
        feats = _cached_feats(bbox, date, days)          # server down: use the tiles we already have
        if not feats:
            raise
        print(f"[gfm] server down ({e.__class__.__name__}): {len(feats)} cached GFM tiles near {date}")
    d0 = dt.date.fromisoformat(str(date))
    day = lambda f: f["properties"]["datetime"][:10]
    by_day = {}
    for f in feats:
        if "exclusion_mask" in f["assets"] and "ensemble_flood_extent" in f["assets"]:
            by_day.setdefault(day(f), []).append(f)
    for d in sorted(by_day, key=lambda d: abs((dt.date.fromisoformat(d) - d0).days)):
        flood = np.full(shape, 255, np.uint8)
        excl = np.full(shape, 255, np.uint8)
        water = np.full(shape, 255, np.uint8)
        for f in by_day[d]:
            _warp(_get(f["assets"]["ensemble_flood_extent"]["href"]), grid, flood)
            _warp(_get(f["assets"]["exclusion_mask"]["href"]), grid, excl)
            if "ensemble_water_extent" in f["assets"]:     # observed water incl. reference (normal) water
                _warp(_get(f["assets"]["ensemble_water_extent"]["href"]), grid, water)
        seen = (flood != 255) & (excl != 255)
        if seen.mean() >= min_cover:
            return dict(date=d, flood=flood == 1, excluded=excl == 1, seen=seen, n=len(by_day[d]),
                        water=water == 1, has_water=bool((water != 255).any()))
    return None
