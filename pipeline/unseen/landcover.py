"""ESA WorldCover 2021 (10 m, CC BY 4.0) sampled onto a site grid, so changes can be reported by land type
(cropland flooded, buildings in the damage zone, forest burned). Read straight from the public COGs on AWS with our
range reader (overview ~75 m, a few MB per area). Cached per site in data/landcover/.

Classes: 10 tree, 20 shrub, 30 grass, 40 cropland, 50 built-up, 60 bare, 70 snow/ice, 80 water, 90 herbaceous wetland,
95 mangroves, 100 moss/lichen.
"""
import math
import numpy as np

from .config import DATA_DIR

URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif"
NAMES = {10: "forest", 20: "shrubland", 30: "grassland", 40: "cropland", 50: "built-up", 60: "bare", 70: "snow/ice",
         80: "water", 90: "wetland", 95: "mangroves", 100: "moss"}


def _tile(lat, lon):
    la, lo = 3 * math.floor(lat / 3), 3 * math.floor(lon / 3)
    return f"{'N' if la >= 0 else 'S'}{abs(la):02d}{'E' if lo >= 0 else 'W'}{abs(lo):03d}"


def on_grid(grid, bbox, key=None, overview=3):
    """WorldCover class per pixel of a site grid (dict x, y, epsg). Returns uint8 (H, W) or None if unreachable."""
    import rasterio, requests
    from pyproj import Transformer
    from rasterio.windows import from_bounds
    from .remote import RangeFile
    cache = DATA_DIR / "landcover" / f"{key}.npy" if key else None
    if cache is not None and cache.exists():
        a = np.load(cache)
        if a.shape == (len(grid["y"]), len(grid["x"])):
            return a
    X, Y = np.meshgrid(grid["x"], grid["y"])
    lon, lat = Transformer.from_crs(grid["epsg"], 4326, always_xy=True).transform(X, Y)
    out = np.zeros(X.shape, np.uint8)
    lon0, lat0, lon1, lat1 = bbox
    tiles = {_tile(la, lo) for la in np.arange(lat0, lat1 + 3, 3)[:4] for lo in np.arange(lon0, lon1 + 3, 3)[:4]
             if la <= lat1 + 3 and lo <= lon1 + 3}
    tiles = {t for t in tiles} | {_tile(lat0, lon0), _tile(lat1, lon1), _tile(lat0, lon1), _tile(lat1, lon0)}
    s = requests.Session()
    got = False
    for t in sorted(tiles):
        try:
            with rasterio.open(RangeFile(URL.format(tile=t), s, block=4 << 20), overview_level=overview) as d:
                b = d.bounds
                w = from_bounds(max(lon0, b.left), max(lat0, b.bottom), min(lon1, b.right), min(lat1, b.top), d.transform)
                if w.width <= 0 or w.height <= 0:
                    continue
                w = w.round_offsets().round_lengths()
                a = d.read(1, window=w)
                tr = d.window_transform(w)
        except Exception:  # noqa: BLE001  (no tile = open ocean, or no network)
            continue
        c = ((lon - tr.c) / tr.a).astype(int)
        r = ((lat - tr.f) / tr.e).astype(int)
        m = (r >= 0) & (r < a.shape[0]) & (c >= 0) & (c < a.shape[1]) & (out == 0)
        out[m] = a[r[m], c[m]]
        got = True
    if not got:
        return None
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, out)
    return out


def breakdown(mask, lc, px_km2, classes=(40, 50, 10, 20, 30, 90, 95)):
    """km² of a boolean change mask per land class (only classes that matter)."""
    if lc is None:
        return {}
    return {NAMES[c]: round(float((mask & (lc == c)).sum() * px_km2), 2) for c in classes if (mask & (lc == c)).any()}
