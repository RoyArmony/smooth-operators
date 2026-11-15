"""NISAR GCOV discovery + consistent-stack selection + windowed reads for an arbitrary bbox.

Rules learned on real data (Oct 2026):
  * only calibrated products: PROVISIONAL (from 2026-06-17) and VALIDATED (from 2026-10-21); never BETA (range-dependent
    radiometric bias) or urgent-response (UR) copies. A date with both prefers VALIDATED; the per-date drift
    correction in detect.py absorbs small offsets between processing versions (P05023 -> P05036)
  * one track/frame/direction AND one bandwidth mode per stack (modes are radiometrically offset)
  * full-frame granules only: some modes (e.g. 4005 over Tonle Sap) are narrow partial strips
  * one granule per date; HV may be missing on single-pol (SHSH) dates
"""
from __future__ import annotations

import collections
import datetime as dt
import numpy as np
from shapely.geometry import box, shape

from . import gcov
from .auth import session as earthdata_session
from .config import MIN_COVERAGE, MIN_DATES, PROVISIONAL_START
from .remote import open_h5


def maturity(url):
    """'VALIDATED' | 'PROVISIONAL' | None (BETA, urgent-response 'UR' copies, anything else = not used).
    VALIDATED (from 2026-10-21 acquisitions, released 2026-11-06) lives in .../NISAR/NISAR_L2_GCOV_V1/..."""
    if "/NISAR-UR/" in url or "BETA" in url:
        return None
    if "PROVISIONAL" in url:
        return "PROVISIONAL"
    if "/NISAR_L2_GCOV_V1/" in url:
        return "VALIDATED"
    return None


def _mode(p):
    return p["sceneName"].split("_")[8]


def _pols(p):
    return p["sceneName"].split("_")[9]


def search(bbox, start=PROVISIONAL_START, end=None):
    """bbox = (lon0, lat0, lon1, lat1). Returns provisional GCOV granule properties + geometry."""
    import asf_search as asf
    import time as _t
    for k in range(4):                                   # ASF search sometimes drops the connection: retry
        try:
            res = asf.search(dataset="NISAR", processingLevel="GCOV", intersectsWith=box(*bbox).wkt,
                             start=start, end=end, maxResults=2000)
            break
        except Exception:  # noqa: BLE001
            if k == 3:
                raise
            _t.sleep(3 * 2 ** k)
    out = []
    for r in res:
        p = dict(r.properties)
        p["maturity"] = maturity(p["url"])
        if p["maturity"] is None:
            continue
        p["geom"] = shape(r.geometry)
        out.append(p)
    return out


def stacks(bbox, granules=None):
    """Group into candidate stacks (track, frame, dir, mode) and score them for this bbox."""
    granules = granules if granules is not None else search(bbox)
    aoi = box(*bbox)
    groups = collections.defaultdict(list)
    for p in granules:
        groups[(p["pathNumber"], p["frameNumber"], p["flightDirection"][0], _mode(p))].append(p)
    cands = []
    for (track, frame, d, mode), gs in groups.items():
        per_date = {}
        for p in gs:
            cov = p["geom"].intersection(aoi).area / aoi.area
            dt_ = p["startTime"][:10]
            best = per_date.get(dt_)
            rank = lambda q, c: (c >= MIN_COVERAGE, q["maturity"] == "VALIDATED", c, _pols(q) != "SHSH")
            if best is None or rank(p, cov) > rank(best, best["cov"]):
                per_date[dt_] = dict(p, cov=cov)
        full = [p for p in per_date.values() if p["cov"] >= MIN_COVERAGE]
        dual = sum(_pols(p) != "SHSH" for p in full)
        cands.append(dict(track=track, frame=frame, direction="ascending" if d == "A" else "descending", mode=mode,
                          n_dates=len(full), n_dual=dual, coverage=float(np.median([p["cov"] for p in per_date.values()])),
                          dates=sorted(p["startTime"][:10] for p in full),
                          granules=sorted(full, key=lambda p: p["startTime"]),
                          footprint=max(per_date.values(), key=lambda p: p["cov"])["geom"]))
    cands.sort(key=lambda c: (c["n_dates"] >= MIN_DATES, c["n_dual"], c["n_dates"], c["coverage"]), reverse=True)
    return cands


def window_for_bbox(url, bbox, freq="B", session=None):
    """Pixel window (r0, r1, c0, c1) of the bbox in the granule's frequency grid, plus grid info."""
    from pyproj import Transformer
    with open_h5(url, session) as f:
        g = f[f"science/LSAR/GCOV/grids/frequency{freq}"]
        x, y, epsg = g["xCoordinates"][()], g["yCoordinates"][()], int(g["projection"][()])
    t = Transformer.from_crs(4326, epsg, always_xy=True)
    lon0, lat0, lon1, lat1 = bbox
    xs, ys = zip(*[t.transform(lo, la) for lo, la in [(lon0, lat0), (lon1, lat0), (lon1, lat1), (lon0, lat1)]])
    c0, c1 = int(np.searchsorted(x, min(xs))), int(np.searchsorted(x, max(xs)))
    r0, r1 = int(np.searchsorted(-y, -max(ys))), int(np.searchsorted(-y, -min(ys)))
    return (r0, r1, c0, c1), dict(x=x[c0:c1], y=y[r0:r1], epsg=epsg, dx=float(x[1] - x[0]))


def read_stack(stack, bbox, freq="B", progress=lambda f, m: None, cache_dir=None):
    """Read HH+HV for the bbox window on every date. Returns (T,2,H,W) linear, dates, grid.
    cache_dir: keep one small .npz per date (window only), so a re-run after a new pass reads 1 date,
    not the whole stack. Same track/frame => identical grid, so per-date windows stack pixel-on-pixel."""
    from concurrent.futures import ThreadPoolExecutor
    session = earthdata_session()
    gs = stack["granules"]
    win, grid = window_for_bbox(gs[0]["url"], bbox, freq, session)
    done = [0]
    tag = f"{freq}_{'_'.join(map(str, win))}"

    def one(p):
        cf = cache_dir / f"{p['sceneName']}_{tag}.npz" if cache_dir else None
        hit = cf is not None and cf.exists()
        if hit:
            z = np.load(cf)
            a, d = z["a"], dt.date.fromisoformat(str(z["date"]))
        else:
            a, m = gcov.read(p["url"], terms=("HHHH", "HVHV"), freq=freq, window=win, session=session)
            d = m["date"]
            if cf is not None:
                cf.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(cf, a=a.astype(np.float32), date=d.isoformat())
        done[0] += 1
        progress(done[0] / len(gs), f"read {done[0]}/{len(gs)} NISAR dates" + (" (cached)" if hit else ""))
        return a, d
    with ThreadPoolExecutor(5) as ex:
        res = list(ex.map(one, gs))
    stack_arr = np.stack([r[0] for r in res]).astype(np.float32)
    return stack_arr, [r[1].isoformat() for r in res], grid
