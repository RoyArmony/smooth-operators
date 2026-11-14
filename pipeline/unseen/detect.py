"""Change detection on a NISAR GCOV time series (HH+HV, linear gamma0).

Physics (L-band, ~24 cm):
  * open water is a smooth (specular) surface -> very dark in HH and HV
  * vegetation volume scattering keeps HV high; it collapses when trees are cut, burned, or the understory floods
  * shallow water among vegetation and freshly burned/bare land reach the SAME backscatter levels, so radar values
    alone can't separate them -> use context: floods spread from existing open water, burns are isolated patches
Per-pixel change is measured against the pixel's own baseline (first dates), corrected for the drift of stable land
(seasonal soil moisture, small radiometric differences between dates).
"""
import datetime as dt
import numpy as np
from scipy.ndimage import distance_transform_edt, label, uniform_filter

from .gcov import fill_time_gaps

OPEN_HH, OPEN_HV = -17.0, -24.0      # dB, open-water thresholds (L-band gamma0)
DARKEN_DB = 2.5                      # drop in both HH and HV vs. baseline -> "darkened"
HV_DROP_DB = 3.0                     # vegetation volume loss
VEG_HV = -15.0                       # baseline HV above this = vegetated
# v2 (Nov 2026): floods in fields / paddies that never get as dark as a lake (Thailand), double bounce, permanent water
FIELD_MIN_KM2 = 0.5                  # a darkened patch this big counts as flood on its own ...
FIELD_MAX_HH = -12.0                 # ... if it ends up this dark in HH ...
SPECULAR_MARGIN = 1.0                # ... and HH dropped at least (HV drop - this): mirror-like water, not lost leaves
DB_RISE = 3.0                        # double bounce: HH rises this much ...
DB_HV_MAX = 1.5                      # ... while HV changes less than this (water under standing vegetation)
PERMANENT_FRAC = 0.9                 # open water on >= 90 % of passes = permanent (sea, lake core): not flood


def _near(masks, dist_px):
    """Per date: pixels within dist_px of a True pixel."""
    return np.stack([(distance_transform_edt(~m) <= dist_px) if m.any() else np.zeros_like(m) for m in masks])


def _db(stack):
    s = fill_time_gaps(stack)
    s = np.where(np.isfinite(s) & (s > 0), s, np.nan)
    sm = np.stack([np.stack([uniform_filter(np.nan_to_num(s[t, p], nan=np.nanmedian(s[t, p])), 3) for p in range(2)])
                   for t in range(len(s))])                      # 3x3 boxcar against speckle
    valid = np.isfinite(s).all(axis=(0, 1))
    db = 10 * np.log10(np.maximum(sm, 1e-6))
    return db[:, 0], db[:, 1], valid


def calibrate(stack, dates, odates, clear, owat, oopen, pixel_m=80.0, min_km2=5.0):
    """Optical teaches radar: on clear days, pick the open-water thresholds (HH, HV in dB) that best match OPERA
    DSWx-HLS open water, then use them on every pass (cloudy ones too). Fixed thresholds fail across places: calm
    lake water at Tonle Sap is ~-20 dB HH, fish ponds in Thailand ~-15 dB. Honest score: each clear day is tested with
    thresholds learned on the OTHER clear days (leave-one-out). Returns None when there are no usable clear days."""
    hh, hv, valid = _db(stack)
    px = (pixel_m / 1000) ** 2
    perm = ((hh < OPEN_HH) & (hv < OPEN_HV)).mean(0) >= PERMANENT_FRAC     # calm sea / lake core: easy, would bias the fit
    valid = valid & ~perm
    days = []
    for t, d in enumerate(dates):
        seen, ow, oo, near = optical_view(d, odates, clear, owat, oopen)
        m = seen & near & valid
        if m.sum() * px >= 50 and (oo & m).sum() * px >= min_km2:
            days.append((t, d, m, oo))
    if not days:
        return None
    grid = [(th, th + off) for th in np.arange(-21.0, -10.9, 0.5) for off in (-9.0, -8.0, -7.0, -6.0, -5.0)]

    def counts(t, m, oo, th, tv):
        w = (hh[t] < th) & (hv[t] < tv)
        return np.array([(w & oo & m).sum(), (w & ~oo & m).sum(), (~w & oo & m).sum()])
    C = np.array([[counts(t, m, oo, th, tv) for th, tv in grid] for t, d, m, oo in days])     # (days, grid, 3)
    f1 = lambda c: 2 * c[..., 0] / np.maximum(2 * c[..., 0] + c[..., 1] + c[..., 2], 1)
    best = int(np.argmax(f1(C.sum(0))))
    loo = []
    for i, (t, d, m, oo) in enumerate(days):
        rest = np.delete(C, i, axis=0).sum(0) if len(days) > 1 else C.sum(0)
        j = int(np.argmax(f1(rest)))
        loo.append(dict(date=d, f1=float(f1(C[i, j])), thresholds=[float(v) for v in grid[j]]))
    ok = len(days) >= 2 and float(np.mean([x["f1"] for x in loo])) >= 0.5          # otherwise keep the defaults
    return dict(used=ok, open_hh=float(grid[best][0]), open_hv=float(grid[best][1]), f1_fit=float(f1(C.sum(0))[best]),
                f1_default=float(f1(C.sum(0))[grid.index((-17.0, -24.0))] if (-17.0, -24.0) in grid else np.nan),
                n_days=len(days), loo=loo)


def detect(stack, pixel_m=80.0, v2=True, open_hh=OPEN_HH, open_hv=OPEN_HV):
    """stack (T,2,H,W) linear (HV may be NaN on single-pol dates). Returns dict of layers (T,H,W) / (H,W).
    v2=False reproduces the first (Oct 2026) detector, for comparison. open_hh/open_hv: from calibrate()."""
    hh, hv, valid = _db(stack)
    open_w = (hh < open_hh) & (hv < open_hv)
    nb = min(2, len(hh))
    b_hh, b_hv = np.median(hh[:nb], 0), np.median(hv[:nb], 0)
    quiet = (~open_w.any(0)) & valid & (np.std(hh, 0) < np.percentile(np.std(hh, 0)[valid], 30))
    if quiet.sum() < 100:
        quiet = (~open_w.any(0)) & valid
    drift_hh = np.array([np.median(h[quiet]) for h in hh]); drift_hh -= drift_hh[:nb].mean()
    drift_hv = np.array([np.median(h[quiet]) for h in hv]); drift_hv -= drift_hv[:nb].mean()
    d_hh = hh - b_hh - drift_hh[:, None, None]
    d_hv = hv - b_hv - drift_hv[:, None, None]
    darkened = (d_hh < -DARKEN_DB) & (d_hv < -DARKEN_DB) & ~open_w
    near_open = _near(open_w, 1000 / pixel_m)
    min_px = FIELD_MIN_KM2 / (pixel_m / 1000) ** 2
    water = np.zeros_like(open_w)
    for t in range(len(open_w)):       # whole darkened regions connected to open water = flood
        lab, nlab = label(darkened[t] | open_w[t])
        keep = set(np.unique(lab[(open_w[t] | (darkened[t] & near_open[t])) & (lab > 0)]))
        if v2 and nlab:                                     # flooded fields: big, dark, mirror-like patches
            idx = np.arange(1, nlab + 1)
            from scipy.ndimage import sum as nd_sum, mean as nd_mean
            area = nd_sum(np.ones_like(lab), lab, idx)
            mhh = nd_mean(hh[t], lab, idx)
            spec = nd_mean((d_hh[t] <= d_hv[t] + SPECULAR_MARGIN).astype(float), lab, idx)
            keep |= set(idx[(area >= min_px) & (mhh <= FIELD_MAX_HH) & (spec >= 0.6)].tolist())
        water[t] = np.isin(lab, list(keep)) & (lab > 0)
    hv_drop = (b_hv > VEG_HV)[None] & ~water & (d_hv < -HV_DROP_DB)
    near_w = _near(water, 3000 / pixel_m)
    canopy_w = hv_drop & near_w                                   # vegetation losing volume right next to water
    if v2:                                                        # double bounce: HH up, HV steady, next to water
        canopy_w |= (d_hh > DB_RISE) & (np.abs(d_hv) < DB_HV_MAX) & near_w & ~water
    veg_change = (hv_drop | darkened) & ~water & ~canopy_w        # burns, clearing, harvest, ...
    # permanent water (sea, lake core): dark on >= 90 % of passes by a lenient test, independent of the calibrated
    # water thresholds, so a rough sea that only sometimes passes the strict test still counts as permanent
    permanent = (((hh < -13.0) & (hv < -19.0)).mean(0) >= PERMANENT_FRAC) & valid if v2 else np.zeros_like(valid)
    return dict(hh=hh, hv=hv, water=water & valid, canopy=canopy_w & valid, veg_change=veg_change & valid,
                valid=valid, drift_hh=drift_hh, permanent=permanent)


def optical_view(day, odates, clear, owat, oopen, win=5):
    """Per pixel, the best clear optical observation within +-win days of `day`.
    Returns (seen, water, open_water, within_2_days) boolean maps."""
    shape = clear.shape[1:]
    c_best = np.zeros(shape, np.float32); w_best = np.zeros(shape, np.float32); o_best = np.zeros(shape, np.float32)
    gap = np.full(shape, 99.)
    d0 = dt.date.fromisoformat(day)
    for i, od in enumerate(odates):
        g = abs((dt.date.fromisoformat(od) - d0).days)
        if g > win:
            continue
        ci = clear[i].astype(np.float32)
        better = (ci > 0.6) & ((c_best <= 0.6) | (g < gap))
        c_best = np.where(better, ci, c_best); w_best = np.where(better, owat[i], w_best)
        o_best = np.where(better, oopen[i], o_best); gap = np.where(better, g, gap)
    return c_best > 0.6, w_best > 0.5, o_best > 0.5, gap <= 2
