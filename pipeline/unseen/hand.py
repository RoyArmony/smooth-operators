"""GLO-30 HAND (Height Above Nearest Drainage, m) on our grid. ASF, derived from Copernicus DEM GLO-30;
open on AWS (s3://glo-30-hand), 1-degree COG tiles, no login. Cached in data/hand/."""
import math
import numpy as np

from .config import DATA_DIR

URL = "https://glo-30-hand.s3.us-west-2.amazonaws.com/v1/2021/Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_HAND.tif"


def _url(lat, lon):
    return URL.format(ns="N" if lat >= 0 else "S", lat=abs(lat), ew="E" if lon >= 0 else "W", lon=abs(lon))


def on_grid(grid, bbox, key=None):
    """Mean HAND (m) per grid pixel (dict x, y, epsg, dx). NaN where no tile (sea). None if nothing reachable."""
    import os
    import rasterio
    from rasterio.warp import reproject, Resampling
    from affine import Affine
    cache = DATA_DIR / "hand" / f"{key}.npy" if key else None
    H, W = len(grid["y"]), len(grid["x"])
    if cache is not None and cache.exists():
        a = np.load(cache)
        if a.shape == (H, W):
            return a
    ca = os.environ.get("CURL_CA_BUNDLE") or os.path.expanduser("~/.ccr/ca-bundle.crt")
    dy = grid["y"][0] - grid["y"][1]
    dst_t = Affine(grid["dx"], 0, grid["x"][0] - grid["dx"] / 2, 0, -dy, grid["y"][0] + dy / 2)
    out = np.full((H, W), np.nan, np.float32); got = False
    with rasterio.Env(GDAL_CURL_CA_BUNDLE=ca, CURL_CA_BUNDLE=ca, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        for la in range(math.floor(bbox[1]), math.floor(bbox[3]) + 1):
            for lo in range(math.floor(bbox[0]), math.floor(bbox[2] - 1e-9) + 1):
                try:
                    with rasterio.open(_url(la, lo)) as d:
                        tmp = np.full((H, W), np.nan, np.float32)
                        reproject(rasterio.band(d, 1), tmp, dst_transform=dst_t, dst_crs=f"EPSG:{grid['epsg']}",
                                  resampling=Resampling.average, dst_nodata=np.nan)
                except Exception:  # noqa: BLE001  (no tile: sea)
                    continue
                m = np.isfinite(tmp); out[m] = tmp[m]; got = True
    if not got:
        return None
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True); np.save(cache, out)
    return out
