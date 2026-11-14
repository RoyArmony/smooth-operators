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


def _inner_box(poly, aoi_bounds, n=48):
    """Largest axis-aligned box inside poly (max rectangle on an n x n raster of the AOI), so every pixel has data."""
    from shapely import contains_xy
    x0, y0, x1, y1 = aoi_bounds
    xs, ys = np.linspace(x0, x1, n + 1), np.linspace(y0, y1, n + 1)
    cx, cy = (xs[:-1] + xs[1:]) / 2, (ys[:-1] + ys[1:]) / 2
    X, Y = np.meshgrid(cx, cy)
    ok = contains_xy(poly.buffer(-1e-4), X, Y)
    # a cell counts only if its four corners are inside too (no slivers of no-data at the edges)
    C = contains_xy(poly, *np.meshgrid(xs, ys))
    ok &= C[:-1, :-1] & C[1:, :-1] & C[:-1, 1:] & C[1:, 1:]
    best, h = (0, None), np.zeros(n, int)
    for r in range(n):                                   # maximal rectangle in a histogram, row by row
        h = np.where(ok[r], h + 1, 0)
        st = []
        for c in range(n + 1):
            hc = h[c] if c < n else 0
            while st and h[st[-1]] >= hc:
                top = st.pop(); w = c - (st[-1] + 1 if st else 0)
                if h[top] * w > best[0]:
                    best = (h[top] * w, (st[-1] + 1 if st else 0, c, r - h[top] + 1, r + 1))
            st.append(c)
    if not best[1]:
        return None
    c0, c1, r0, r1 = best[1]
    return [round(float(v), 4) for v in (xs[c0], ys[r0], xs[c1], ys[r1])]


def plan(bbox, max_parts=3, granules=None, min_frac=0.05):
    """Best effort when no stack covers the whole box: split it into up to `max_parts` sub-boxes, each fully covered
    by one consistent stack (same track/frame/mode) on >= MIN_DATES dates. Greedy: take the part with the most
    (covered area x passes), remove it, repeat on what is left. Returns [dict(bbox, coverage, stack...)]."""
    from .config import MIN_DEG
    granules = granules if granules is not None else search(bbox)
    aoi = box(*bbox)
    groups = collections.defaultdict(list)
    for p in granules:
        groups[(p["pathNumber"], p["frameNumber"], p["flightDirection"][0], _mode(p))].append(p)
    remaining, parts = aoi, []
    for _ in range(max_parts):
        best = None
        for (track, frame, d, mode), gs in groups.items():
            per_date = {}
            for p in gs:
                g = p["geom"].intersection(remaining)
                if g.area > 0 and (p["startTime"][:10] not in per_date or g.area > per_date[p["startTime"][:10]][1].area):
                    per_date[p["startTime"][:10]] = (p, g)
            items = sorted(per_date.values(), key=lambda t: -t[1].area)
            inter = None
            for k, (p, g) in enumerate(items, 1):
                inter = g if inter is None else inter.intersection(g)
                if inter.is_empty or inter.area < min_frac * aoi.area:
                    break
                if k >= MIN_DATES:
                    score = inter.area * min(k, 12)
                    if best is None or score > best[0]:
                        best = (score, (track, frame, d, mode), inter, items)
        if not best:
            break
        _, (track, frame, d, mode), inter, items = best
        sub = _inner_box(inter, bbox)
        if not sub or sub[2] - sub[0] < MIN_DEG or sub[3] - sub[1] < MIN_DEG or box(*sub).area < 0.08 * aoi.area:
            break
        sb = box(*sub)
        sel = sorted((p for p, _ in items if p["geom"].intersection(sb).area >= 0.98 * sb.area), key=lambda p: p["startTime"])
        if len(sel) < MIN_DATES:
            break
        parts.append(dict(bbox=sub, coverage=round(sb.area / aoi.area, 3), track=track, frame=frame,
                          direction="ascending" if d == "A" else "descending", mode=mode, n_dates=len(sel),
                          n_dual=sum(_pols(p) != "SHSH" for p in sel), dates=[p["startTime"][:10] for p in sel], granules=sel))
        remaining = remaining.difference(sb)
        if remaining.area < 0.1 * aoi.area:
            break
    return parts


def coverage_summary(bbox):
    """For the UI: footprints + candidate stacks, and a best-effort plan when nothing covers the whole box."""
    gr = search(bbox)
    cands = stacks(bbox, gr)
    full = any(c["n_dates"] >= MIN_DATES for c in cands)
    parts = [] if full else [{k: v for k, v in p.items() if k != "granules"} for p in plan(bbox, granules=gr)]
    return dict(stacks=_stack_list(cands), parts=parts, full=full)


def _stack_list(cands):
    return [dict(track=c["track"], frame=c["frame"], direction=c["direction"], mode=c["mode"], n_dates=c["n_dates"],
                 n_dual=c["n_dual"], coverage=round(c["coverage"], 3), first=c["dates"][0] if c["dates"] else None,
                 last=c["dates"][-1] if c["dates"] else None, usable=c["n_dates"] >= MIN_DATES,
                 footprint=c["footprint"].__geo_interface__) for c in cands]


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


def acquisitions(bbox, max_results=2000):
    """For the globe timeline: per acquisition date, how much of the view NISAR imaged (metadata only).
    Only calibrated (PROVISIONAL) GCOV products count. Returns dict(dates=[...], truncated=bool):
    each date = dict(date, coverage (0..1 of the view, union of granules), n_granules, tracks)."""
    from shapely.ops import unary_union
    aoi = box(*bbox)
    import asf_search as asf
    raw = asf.search(dataset="NISAR", processingLevel="GCOV", intersectsWith=aoi.wkt, start=PROVISIONAL_START,
                     maxResults=max_results)
    truncated = len(raw) >= max_results
    gs = [dict(r.properties, geom=shape(r.geometry)) for r in raw if maturity(r.properties["url"])]
    by_date = collections.defaultdict(list)
    for p in gs:
        by_date[p["startTime"][:10]].append(p)
    out = []
    for d, ps in sorted(by_date.items()):
        cov = unary_union([p["geom"] for p in ps]).intersection(aoi).area / aoi.area
        out.append(dict(date=d, coverage=round(min(1.0, cov), 3), n_granules=len(ps),
                        tracks=sorted({f'{p["pathNumber"]}{p["flightDirection"][0]}' for p in ps})))
    return dict(dates=out, truncated=truncated)


def archive_latest():
    """Newest calibrated GCOV acquisition anywhere (proxy for 'archive is processed up to')."""
    import asf_search as asf
    import datetime as dt
    start = (dt.date.today() - dt.timedelta(days=10)).isoformat()
    r = asf.search(dataset="NISAR", processingLevel="GCOV", start=start, maxResults=250)
    ds = [x.properties["startTime"][:10] for x in r if maturity(x.properties["url"])]
    return max(ds) if ds else None
