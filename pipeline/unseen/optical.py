"""OPERA DSWx-HLS (optical water, 30 m) for a bbox/date range, regridded onto a NISAR window grid.

Per optical date and 80 m pixel: clear (observed, not cloud) fraction, water (open+partial) fraction, open-water fraction.
DSWx-HLS WTR classes: 0 not water, 1 open water, 2 partial surface water, 252 snow/ice, 253 cloud/shadow, 254 ocean mask, 255 fill.
"""
from __future__ import annotations

from .remote import get_retry
import collections, json, os, urllib.parse, urllib.request
import numpy as np

from .config import DATA_DIR

CACHE = str(DATA_DIR / "dswx")


def search(bbox, start, end):
    q = urllib.parse.urlencode(dict(short_name="OPERA_L3_DSWX-HLS_V1", bounding_box=",".join(map(str, bbox)),
                                    temporal=f"{start}T00:00:00Z,{end}T23:59:59Z", page_size=2000))
    es = json.load(urllib.request.urlopen(f"https://cmr.earthdata.nasa.gov/search/granules.json?{q}", timeout=120))["feed"]["entry"]
    out = []
    for e in es:
        u = [l["href"] for l in e["links"] if l["href"].startswith("https") and l["href"].endswith("_B01_WTR.tif")]
        if u:
            out.append(dict(title=e["title"], date=e["time_start"][:10], url=u[0]))
    return out


def download(granules, session, progress=lambda f, m: None, workers=8):
    from concurrent.futures import ThreadPoolExecutor
    os.makedirs(CACHE, exist_ok=True)
    done = [0]

    def one(g):
        path = os.path.join(CACHE, os.path.basename(g["url"]))
        if not (os.path.exists(path) and os.path.getsize(path) > 0):
            r = get_retry(session, g["url"], timeout=180)
            r.raise_for_status()
            tmp = path + ".part"
            open(tmp, "wb").write(r.content)
            os.replace(tmp, path)
        done[0] += 1
        if done[0] % 10 == 0 or done[0] == len(granules):
            progress(done[0] / len(granules), f"optical tiles {done[0]}/{len(granules)}")
        return dict(g, path=path)
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, granules))


def ocean_mask(files, grid):
    """Pixels DSWx marks as ocean (class 254) on any date: the sea is never flood (tides/wind make it look 'new')."""
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_origin
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    out = np.zeros((len(y), len(x)), np.float32)
    for f in files[:40]:
        with rasterio.open(f["path"]) as src:
            o = np.full(out.shape, np.nan, np.float32)
            reproject((src.read(1) == 254).astype(np.float32), o, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx), dst_crs=f"EPSG:{grid['epsg']}",
                      resampling=Resampling.average, dst_nodata=np.nan)
            np.fmax(out, np.nan_to_num(o), out=out)
    return out > 0.5


def regrid(files, grid):
    """files: list of dict(date, path). grid: dict(x, y, epsg, dx). Returns dates, clear, water, open arrays (T,H,W)."""
    import rasterio
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_origin
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    H, W = len(y), len(x)
    dst_tf = from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx)
    by_date = collections.defaultdict(list)
    for f in files:
        by_date[f["date"]].append(f["path"])
    dates, C, Wt, O = [], [], [], []
    for d in sorted(by_date):
        layers = [np.zeros((H, W), np.float32) for _ in range(3)]
        for path in by_date[d]:
            with rasterio.open(path) as src:
                a = src.read(1)
                for arr, ind in zip(layers, (np.isin(a, (0, 1, 2)), np.isin(a, (1, 2)), a == 1)):
                    out = np.full((H, W), np.nan, np.float32)
                    reproject(ind.astype(np.float32), out, src_transform=src.transform, src_crs=src.crs,
                              dst_transform=dst_tf, dst_crs=f"EPSG:{grid['epsg']}", resampling=Resampling.average, dst_nodata=np.nan)
                    np.fmax(arr, np.nan_to_num(out), out=arr)
        if layers[0].max() == 0:
            continue
        dates.append(d); C.append(layers[0]); Wt.append(layers[1]); O.append(layers[2])
    if not dates:
        return [], *(np.zeros((0, H, W), np.float16),) * 3
    return dates, np.stack(C).astype(np.float16), np.stack(Wt).astype(np.float16), np.stack(O).astype(np.float16)
