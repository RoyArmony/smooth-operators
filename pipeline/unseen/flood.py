"""One flood site, end to end: best NISAR stack -> water maps -> per-pass comparison with Copernicus GFM.

The gap NISAR fills = NISAR water (open + under vegetation, minus permanent water) inside GFM's exclusion mask
("cannot see"), where both have data. Area = pixels x 80 m x 80 m."""
import datetime as dt
import numpy as np

from . import gfm, nisar, optical
from .auth import session as earthdata_session
from .config import DATA_DIR, MAX_DEG, MIN_DATES
from .detect import calibrate, detect


def load(bbox, sid, refresh=False):
    """Best consistent NISAR GCOV stack over bbox, cached in data/stacks/<sid>-*.npz.
    refresh=False: use the cache as is if present (no search). Returns stack, dates, grid, stack info (or None)."""
    hit = sorted((DATA_DIR / "stacks").glob(f"{sid}-*.npz"))
    if hit and not refresh:
        z = np.load(hit[0], allow_pickle=True)
        tr, fr = hit[0].stem.rsplit("-", 2)[-2:]                     # cache name <sid>-<track>-<frame>.npz
        st = dict(track=int(tr), frame=int(fr) if fr.isdigit() else None, direction=None, cached=True)
        return z["stack"], [str(d) for d in z["dates"]], z["grid"].item(), st
    lon0, lat0, lon1, lat1 = bbox
    if not (lon0 < lon1 and lat0 < lat1) or max(lon1 - lon0, lat1 - lat0) > MAX_DEG:
        raise ValueError(f"bbox must be lon0,lat0,lon1,lat1, at most {MAX_DEG} deg per side")
    usable = [c for c in nisar.stacks(bbox) if c["n_dates"] >= MIN_DATES]
    if not usable:
        raise RuntimeError(f"no NISAR stack with >= {MIN_DATES} passes covers this box yet")
    st = usable[0]
    cache = DATA_DIR / "stacks" / f"{sid}-{st['track']}-{st['frame']}.npz"
    scenes = [g["sceneName"] for g in st["granules"]]
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        if list(z["scenes"]) == scenes:
            return z["stack"], [str(d) for d in z["dates"]], z["grid"].item(), st
    stack, dates, grid = nisar.read_stack(st, bbox, freq="B", cache_dir=DATA_DIR / "scenes")
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, stack=stack, dates=np.array(dates), scenes=np.array(scenes), grid=np.array(grid, dtype=object))
    return stack, dates, grid, st


def water(stack, dates, grid, bbox, use_optical=True, detector="v3", st=None, dry_dates=None, fill=False, key=None):
    """Water layers per pass. detector="v3" (default): fused.detect_fused (docs/07 §2b: per-scene threshold, change
    from the dry season, HV, GUNW coherence). detector="v2": detect.detect with thresholds calibrated on clear optical
    days. Both add the optical ocean mask to permanent water. Returns (L, calibration or None)."""
    cal, files = None, []
    if detector == "v3":
        from .fused import detect_fused
        L = detect_fused(stack, dates, grid, bbox, track=(st or {}).get("track"), frame=(st or {}).get("frame"), dry_dates=dry_dates)
        if fill:                                                # optional: smart fill with HAND (fill.py)
            from .fill import apply
            L = apply(L, grid, bbox, key=key)
        if use_optical:
            try:
                d0 = (dt.date.fromisoformat(dates[0]) - dt.timedelta(days=6)).isoformat()
                d1 = (dt.date.fromisoformat(dates[-1]) + dt.timedelta(days=6)).isoformat()
                og = optical.search(bbox, d0, d1)
                files = optical.download(og, earthdata_session()) if og else []
                if files:
                    L["permanent"] = L["permanent"] | optical.ocean_mask(files, grid)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] ocean mask skipped: {e}")
        return L, None
    if use_optical:
        d0 = (dt.date.fromisoformat(dates[0]) - dt.timedelta(days=6)).isoformat()
        d1 = (dt.date.fromisoformat(dates[-1]) + dt.timedelta(days=6)).isoformat()
        og = optical.search(bbox, d0, d1)
        files = optical.download(og, earthdata_session()) if og else []
        if files:
            odates, clear, owat, oopen = optical.regrid(files, grid)
            cal = calibrate(stack, dates, odates, clear, owat, oopen, grid["dx"])
    L = detect(stack, pixel_m=grid["dx"], **({"open_hh": cal["open_hh"], "open_hv": cal["open_hv"]} if cal and cal["used"] else {}))
    if files:
        try:
            L["permanent"] = L["permanent"] | optical.ocean_mask(files, grid)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] ocean mask skipped: {e}")
    return L, cal


def gap(L, dates, grid, bbox, days=2, lc=None):
    """Per NISAR pass: GFM nearest in time (± days) and what NISAR adds. Yields one dict per pass with masks + km².
    lc: ESA WorldCover classes on our grid (optional) -> split of the added area by land cover."""
    px = (grid["dx"] / 1000) ** 2
    perm = L["permanent"]
    for t, d in enumerate(dates):
        try:
            G = gfm.on_grid(bbox, d, grid, L["valid"].shape, days=days)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] GFM {d}: {e!r}"[:120])
            continue
        if not G:
            continue
        v = L["valid"] & G["seen"]          # valid is one map for the whole stack
        wet = (L["water"][t] | L["canopy"][t]) & ~perm & v
        add = wet & G["excluded"]
        yield dict(nisar_date=d, gfm_date=G["date"], valid=v, wet=wet, canopy=L["canopy"][t] & ~perm & v,
                   gfm_flood=G["flood"] & v, gfm_excluded=G["excluded"] & v, adds=add,
                   km2=dict(gfm_flood=round(float((G["flood"] & v).sum() * px), 1),
                            gfm_excluded=round(float((G["excluded"] & v).sum() * px), 1),
                            nisar_wet=round(float(wet.sum() * px), 1),
                            nisar_adds=round(float(add.sum() * px), 1),
                            nisar_adds_canopy=round(float((add & L["canopy"][t]).sum() * px), 1),
                            **({} if lc is None else dict(
                                nisar_adds_forest=round(float((add & (lc == 10)).sum() * px), 1),
                                nisar_adds_wetland=round(float((add & (lc == 90)).sum() * px), 1),
                                nisar_adds_cropland=round(float((add & (lc == 40)).sum() * px), 1)))))
