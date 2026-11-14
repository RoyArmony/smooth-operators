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


def on_grid(bbox, date, grid, shape, days=3, min_cover=0.3):
    """GFM flood extent and exclusion mask nearest to `date`, on our grid. Returns dict or None.
    Takes the closest day whose scenes cover >= min_cover of our grid AND carry an exclusion mask
    (some GFM items lack it; without it the gap can't be measured)."""
    feats = search(bbox, date, days)
    d0 = dt.date.fromisoformat(str(date))
    day = lambda f: f["properties"]["datetime"][:10]
    by_day = {}
    for f in feats:
        if "exclusion_mask" in f["assets"] and "ensemble_flood_extent" in f["assets"]:
            by_day.setdefault(day(f), []).append(f)
    for d in sorted(by_day, key=lambda d: abs((dt.date.fromisoformat(d) - d0).days)):
        flood = np.full(shape, 255, np.uint8)
        excl = np.full(shape, 255, np.uint8)
        for f in by_day[d]:
            _warp(_get(f["assets"]["ensemble_flood_extent"]["href"]), grid, flood)
            _warp(_get(f["assets"]["exclusion_mask"]["href"]), grid, excl)
        seen = (flood != 255) & (excl != 255)
        if seen.mean() >= min_cover:
            return dict(date=d, flood=flood == 1, excluded=excl == 1, seen=seen, n=len(by_day[d]))
    return None
