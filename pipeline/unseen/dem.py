"""Copernicus DEM GLO-30 (ESA / EU, AWS open data) sampled onto a site / InSAR grid: elevation for the
troposphere correction (phase that follows height) and a hillshade under interferograms. Cached in data/dem/."""
import math
import numpy as np

from .config import DATA_DIR

URL = "https://copernicus-dem-30m.s3.amazonaws.com/{n}/{n}.tif"


def _name(lat, lon):
    return f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"


def on_grid(grid, bbox, key=None):
    """Elevation (m) per pixel of grid (dict x, y, epsg). 0 over sea / missing tiles. None if nothing reachable."""
    import rasterio, requests
    from pyproj import Transformer
    from rasterio.windows import from_bounds
    from .remote import RangeFile
    cache = DATA_DIR / "dem" / f"{key}.npy" if key else None
    if cache is not None and cache.exists():
        a = np.load(cache)
        if a.shape == (len(grid["y"]), len(grid["x"])):
            return a
    X, Y = np.meshgrid(grid["x"], grid["y"])
    lon, lat = Transformer.from_crs(grid["epsg"], 4326, always_xy=True).transform(X, Y)
    out = np.zeros(X.shape, np.float32)
    s, got = requests.Session(), False
    for la in range(math.floor(bbox[1]), math.floor(bbox[3]) + 1):
        for lo in range(math.floor(bbox[0]), math.floor(bbox[2]) + 1):
            n = _name(la, lo)
            try:
                with rasterio.open(RangeFile(URL.format(n=n), s, block=2 << 20)) as d:
                    b = d.bounds
                    w = from_bounds(max(bbox[0], b.left), max(bbox[1], b.bottom), min(bbox[2], b.right), min(bbox[3], b.top), d.transform)
                    w = w.round_offsets().round_lengths()
                    if w.width <= 0 or w.height <= 0:
                        continue
                    a = d.read(1, window=w).astype(np.float32)
                    tr = d.window_transform(w)
            except Exception:  # noqa: BLE001  (sea: no tile)
                continue
            c = ((lon - tr.c) / tr.a).astype(int)
            r = ((lat - tr.f) / tr.e).astype(int)
            m = (r >= 0) & (r < a.shape[0]) & (c >= 0) & (c < a.shape[1])
            out[m] = a[r[m], c[m]]
            got = True
    if not got:
        return None
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache, out)
    return out


def hillshade(h, dx, az=315, alt=45):
    """0..1 shaded relief."""
    gy, gx = np.gradient(h, dx)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, z = np.radians(az), np.radians(90 - alt)
    v = np.cos(z) * np.cos(slope) + np.sin(z) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(v, 0, 1)
