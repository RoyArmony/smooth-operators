"""People in a change zone (flooded, damaged, burned): WorldPop 2025 constrained 1 km population (CC BY 4.0).
One global GeoTIFF (~276 MB), downloaded once into data/ancillary/ (the server doesn't allow range reads).

people ≈ Σ over changed pixels of (population of its 1 km cell) × (pixel area / cell area)
"""
import numpy as np

from .config import DATA_DIR

URL = ("https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/0_Mosaicked/v1/1km/constrained/"
       "global_pop_2025_CN_1km_R2025A_v1.tif")
PATH = DATA_DIR / "ancillary" / "worldpop_2025_1km.tif"


def ensure(log=print):
    if PATH.exists():
        return PATH
    import requests
    PATH.parent.mkdir(parents=True, exist_ok=True)
    log("[population] downloading WorldPop 2025 1 km (276 MB, once)…")
    tmp = PATH.with_suffix(".part")
    with requests.get(URL, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(4 << 20):
                f.write(chunk)
    tmp.rename(PATH)
    return PATH


def people(mask, grid, bbox):
    """Estimated people living inside a boolean mask on a site grid (dict x, y, epsg, dx). None if no data."""
    if mask is None or not mask.any():
        return 0
    import rasterio
    from pyproj import Transformer
    from rasterio.windows import from_bounds
    p = ensure(log=lambda *a: None)
    with rasterio.open(p) as d:
        w = from_bounds(*bbox, d.transform).round_offsets().round_lengths()
        pop = d.read(1, window=w, boundless=True, fill_value=0).astype(np.float64)
        tr = d.window_transform(w)
        nod = d.nodata
    if nod is not None:
        pop[pop == nod] = 0
    pop[~np.isfinite(pop) | (pop < 0)] = 0
    r, c = np.nonzero(mask)
    lon, lat = Transformer.from_crs(grid["epsg"], 4326, always_xy=True).transform(grid["x"][c], grid["y"][r])
    pr = ((lat - tr.f) / tr.e).astype(int)
    pc = ((lon - tr.c) / tr.a).astype(int)
    ok = (pr >= 0) & (pr < pop.shape[0]) & (pc >= 0) & (pc < pop.shape[1])
    cell_km2 = (abs(tr.a) * 111.32) * (abs(tr.e) * 111.32) * np.cos(np.radians(lat[ok]))
    px_km2 = (grid["dx"] / 1000) ** 2
    return int(round(float((pop[pr[ok], pc[ok]] * px_km2 / cell_km2).sum())))
