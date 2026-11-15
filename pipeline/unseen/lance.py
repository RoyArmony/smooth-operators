"""NASA LANCE NRT Global Flood Product (MODIS = MCDWD, VIIRS = VCDWD; optical, ~250 m, daily) on our NISAR grid.
This is the product behind NASA's FLOOD viewer (earthdata.nasa.gov/data/tools/flood). Read from GIBS WMS (no login):
layers {MODIS,VIIRS}_Combined_Flood_{1,2,3}-Day. NASA recommends the 2-day composite for a first look (1-day can show
cloud-shadow false floods). Classes (GIBS colormap MODIS_Flood.xml):
  0 no water · 1 surface water (normal/reference) · 2 recurring flood · 3 flood · 255 insufficient data (cloud etc.)
"Insufficient data" is the optical map's own "cannot see" class, the counterpart of GFM's exclusion mask."""
import datetime as dt
import io
import pathlib

import numpy as np
import requests

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
from .config import DATA_DIR
CACHE = DATA_DIR / "lance"
NOWATER, SURFACE, RECURRING, FLOOD, NODATA = 0, 1, 2, 3, 255
_RGB = {(0, 0, 1): NOWATER, (50, 210, 245): SURFACE, (255, 255, 0): RECURRING, (250, 30, 36): FLOOD,
        (175, 175, 175): NODATA}
RES = 0.00125                                   # deg per pixel requested (~140 m, half the product's 250 m)


def layer(sensor="MODIS", days=2):
    return f"{sensor}_Combined_Flood_{days}-Day"


def fetch(bbox, date, sensor="MODIS", days=2):
    """Class raster (uint8, north-up, EPSG:4326) of the composite dated `date` over bbox. Cached as .npy.
    Pixels with an unknown colour (outside the product) become 254."""
    lon0, lat0, lon1, lat1 = bbox
    lay = layer(sensor, days)
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{lay}_{date}_{lon0:.4f}_{lat0:.4f}_{lon1:.4f}_{lat1:.4f}.npy"
    if f.exists():
        return np.load(f)
    w, h = int(round((lon1 - lon0) / RES)), int(round((lat1 - lat0) / RES))
    q = dict(SERVICE="WMS", REQUEST="GetMap", VERSION="1.3.0", LAYERS=lay, STYLES="", CRS="EPSG:4326",
             BBOX=f"{lat0},{lon0},{lat1},{lon1}", WIDTH=w, HEIGHT=h, FORMAT="image/png", TRANSPARENT="TRUE", TIME=str(date))
    r = requests.get(WMS, params=q, timeout=120)
    r.raise_for_status()
    if not r.headers.get("content-type", "").startswith("image/"):
        raise RuntimeError(r.text[:200])
    from PIL import Image
    a = np.asarray(Image.open(io.BytesIO(r.content)).convert("RGBA"))
    out = np.full(a.shape[:2], 254, np.uint8)
    out[a[..., 3] == 0] = NOWATER               # transparent = "no water" (rgb 0,0,1 is drawn transparent)
    for rgb, c in _RGB.items():
        out[(a[..., 0] == rgb[0]) & (a[..., 1] == rgb[1]) & (a[..., 2] == rgb[2]) & (a[..., 3] > 0)] = c
    np.save(f, out)
    return out


def on_grid(bbox, date, grid, shape, sensor="MODIS", days=2):
    """LANCE classes on our grid (nearest). Returns dict(flood, recurring, surface, nodata, cls) or None if empty.
    The composite dated `date` + 1 is used: a 2-day composite ends on its date, so it then covers the NISAR day and the
    day after (the radar pass sits inside the optical window)."""
    from rasterio.warp import reproject, Resampling
    from rasterio.transform import from_origin, from_bounds
    d = dt.date.fromisoformat(str(date)) + dt.timedelta(days=1 if days > 1 else 0)
    lon0, lat0, lon1, lat1 = bbox
    pad = 0.05
    bb = (lon0 - pad, lat0 - pad, lon1 + pad, lat1 + pad)
    src = fetch(bb, d.isoformat(), sensor, days)
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    dst = np.full(shape, 253, np.uint8)
    reproject(src, dst, src_transform=from_bounds(*bb, src.shape[1], src.shape[0]), src_crs="EPSG:4326",
              dst_transform=from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx), dst_crs=f"EPSG:{grid['epsg']}",
              resampling=Resampling.nearest, src_nodata=None, dst_nodata=253)
    return dict(date=d.isoformat(), sensor=sensor, days=days, cls=dst, flood=(dst == FLOOD) | (dst == RECURRING),
                surface=dst == SURFACE, nodata=dst == NODATA, seen=dst <= FLOOD)


def truecolor(bbox, date, path, width=640):
    """VIIRS NOAA-20 true colour (GIBS, daily, ~375 m) over bbox on `date` as JPEG: the optical view, clouds included.
    Falls back to Suomi-NPP, then MODIS Terra."""
    lon0, lat0, lon1, lat1 = bbox
    h = max(1, int(width * (lat1 - lat0) / (lon1 - lon0)))
    for lay in ("VIIRS_NOAA20_CorrectedReflectance_TrueColor", "VIIRS_SNPP_CorrectedReflectance_TrueColor",
                "MODIS_Terra_CorrectedReflectance_TrueColor"):
        q = dict(SERVICE="WMS", REQUEST="GetMap", VERSION="1.3.0", LAYERS=lay, STYLES="", CRS="EPSG:4326",
                 BBOX=f"{lat0},{lon0},{lat1},{lon1}", WIDTH=width, HEIGHT=h, FORMAT="image/jpeg", TIME=str(date))
        r = requests.get(WMS, params=q, timeout=120)
        if r.ok and r.headers.get("content-type", "").startswith("image/") and len(r.content) > 8000:
            pathlib.Path(path).write_bytes(r.content)
            return lay
    raise RuntimeError("no true-colour image")


def composite(bbox, date, grid, shape):
    """NASA LANCE flood map for a NISAR pass: VIIRS 2-day; where VIIRS has no data, MODIS 2-day.
    Returns dict(date, flood, water (flood + normal water), seen, nodata)."""
    V = on_grid(bbox, date, grid, shape, "VIIRS", 2)
    M = on_grid(bbox, date, grid, shape, "MODIS", 2)
    fill = V["nodata"] & M["seen"]
    pick = lambda k: np.where(fill, M[k], V[k])
    return dict(date=V["date"], flood=pick("flood"), water=pick("flood") | pick("surface"),
                seen=V["seen"] | M["seen"], nodata=V["nodata"] & ~M["seen"])
