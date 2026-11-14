"""Canadian RADARSAT Constellation Mission (RCM, C-band, compact-pol) analysis-ready data on our NISAR grid.
Open CEOS-ARD on AWS (Canada only), found via the EODMS STAC search. Licence: RCM Public User Licence (CSA).
Bands: RR (same sense: double bounce, e.g. water under trees), RL (opposite sense: surface / volume).
Used to show what short-wave C-band sees vs NISAR's L-band on the same days."""
import datetime as dt
import os

import numpy as np
import requests

STAC = "https://eodms-sgdot.nrcan-rncan.gc.ca/search/search"


def search(bbox, start, end):
    p = dict(collections="rcm-ard", bbox=",".join(map(str, bbox)), limit=200,
             datetime=f"{start}T00:00:00Z/{end}T23:59:59Z")
    r = requests.get(STAC, params=p, timeout=60)
    r.raise_for_status()
    return sorted(r.json().get("features", []), key=lambda f: f["properties"]["datetime"])


def nearest(feats, date, max_days=3):
    """Scenes of the RCM day closest to `date` (within max_days)."""
    d0 = dt.date.fromisoformat(str(date))
    day = lambda f: dt.date.fromisoformat(f["properties"]["datetime"][:10])
    ok = [f for f in feats if abs((day(f) - d0).days) <= max_days]
    if not ok:
        return []
    best = min(abs((day(f) - d0).days) for f in ok)
    return [f for f in ok if abs((day(f) - d0).days) == best]


def on_grid(feats, grid, shape, bands=("rr", "rl")):
    """Mean of each band (linear power) over the scenes, warped onto our grid (bilinear, from an overview)."""
    import rasterio
    from rasterio.vrt import WarpedVRT
    from rasterio.transform import from_origin
    from rasterio.enums import Resampling
    os.environ.setdefault("GDAL_CURL_CA_BUNDLE", os.path.expanduser("~/.ccr/ca-bundle.crt"))
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    T = from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx)
    out = {}
    for b in bands:
        acc, n = np.zeros(shape, np.float64), np.zeros(shape, np.int16)
        for f in feats:
            href = f["assets"][b]["href"]
            ca = os.path.expanduser("~/.ccr/ca-bundle.crt")
            with rasterio.Env(GDAL_CURL_CA_BUNDLE=ca, CURL_CA_BUNDLE=ca, GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), \
                    rasterio.open("/vsicurl/" + href, OVERVIEW_LEVEL=1) as src, \
                    WarpedVRT(src, crs=f"EPSG:{grid['epsg']}", transform=T, width=shape[1], height=shape[0],
                              resampling=Resampling.average, src_nodata=0, nodata=0) as v:
                a = v.read(1).astype(np.float64)
            ok = a > 0
            acc[ok] += a[ok]; n[ok] += 1
        out[b] = np.where(n > 0, acc / np.maximum(n, 1), np.nan).astype(np.float32)
    return out
