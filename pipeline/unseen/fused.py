"""Fused flood detector v3 (docs/07 §2b): per-scene threshold (Martinis et al. 2015) + change from the dry season
+ NISAR L-band HV and 12-day coherence (GUNW), combined by a logistic score.

Fitted on the Inner Niger Delta, track 145 (truth: OPERA DSWx-HLS on clear days); tested on track 138:
F1 0.70 vs 0.61 (paper method) and 0.57-0.60 (handbook classifier). One site so far: re-check elsewhere.

    L = detect_fused(stack, dates, grid, bbox, track=145, frame=9)      # same keys as detect.detect()

Water under vegetation (double bounce) still comes from detect.detect() ('canopy')."""
import datetime as dt
import numpy as np
from scipy import ndimage as ndi

from .config import DATA_DIR

QA_DB = 3.0          # drop a pass whose scene-median HH is > 3 dB from the stack median (corrupt granule)
TILE = 40            # tile size in pixels for the per-scene threshold (40 x 80 m = 3.2 km)
N_DRY = 2            # passes used as the dry reference: the first passes of the stack (NISAR data start mid-June,
                     # before the flood season at our sites), unless the site gives its own dry dates
COH_BAD = 0.2        # a GUNW pair whose scene-median coherence is below this is corrupt
MIN_PATCH_KM2 = 0.1

# Logistic models fitted on Inner Niger track 145 (standardised features; see docs/07 §2b).
# Feature order: HH-tHH, HV-tHV, HH-HHdry, HV-HVdry, HH-HV, rel_height(unused: fixed at mean), HHdry-tHH, coherence
MODEL_COH = dict(w=[-0.2304, -1.0976, -0.4078, 0.0783, -0.5771, -0.0028, 0.0696, -1.4015], b=-3.0262,
                 mu=[1.4888, -2.1592, 0.0791, 0.4405, 6.788, 14.8786, 1.4096, 0.4581],
                 sd=[3.8295, 3.5414, 2.7194, 1.9825, 2.3138, 56.1413, 3.2545, 0.2318], cut=0.30)
MODEL_NOCOH = dict(w=[-0.3525, -1.3784, -0.684, 0.3002, -0.7366, 0.0459, 0.1627], b=-2.3321,
                   mu=[1.263, -1.8986, -0.076, 0.4425, 6.6385, 14.8312, 1.339],
                   sd=[3.8219, 3.5862, 2.751, 1.9601, 2.3678, 56.0538, 3.2849], cut=0.30)


def qa(stack, dates):
    """Drop corrupt passes. Returns (stack, dates, dropped_dates)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        med = np.array([np.nanmedian(10 * np.log10(s[0])) for s in stack])
    ok = np.abs(med - np.nanmedian(med)) <= QA_DB
    return stack[ok], [d for d, k in zip(dates, ok) if k], [d for d, k in zip(dates, ok) if not k]


def ki_threshold(x):
    """Kittler-Illingworth minimum-error threshold of a 1-D sample (dB), on its 1-99 % range."""
    x = x[np.isfinite(x)]
    if x.size < 100:
        return None
    lo, hi = np.percentile(x, [1, 99])
    h, e = np.histogram(x, 256, range=(lo, hi)); c = (e[:-1] + e[1:]) / 2; p = h / max(h.sum(), 1)
    best, bt = np.inf, None
    for k in range(5, 250):
        p1, p2 = p[:k].sum(), p[k:].sum()
        if p1 < 1e-3 or p2 < 1e-3:
            continue
        m1 = (p[:k] * c[:k]).sum() / p1; m2 = (p[k:] * c[k:]).sum() / p2
        s1 = np.sqrt((p[:k] * (c[:k] - m1) ** 2).sum() / p1); s2 = np.sqrt((p[k:] * (c[k:] - m2) ** 2).sum() / p2)
        if s1 <= 0 or s2 <= 0:
            continue
        J = 1 + 2 * (p1 * np.log(s1) + p2 * np.log(s2)) - 2 * (p1 * np.log(p1) + p2 * np.log(p2))
        if J < best:
            best, bt = J, c[k]
    return bt


def tile_threshold(img, ts=TILE):
    """Martinis et al. (2015) split-based threshold: KI per tile, keep clearly two-class tiles (Ashman D > 2, each
    class >= 10 %, dark class < -14 dB), median of their thresholds (>= 5 tiles), else KI on the whole scene."""
    H, W = img.shape; th = []
    for r in range(0, H - ts + 1, ts):
        for c in range(0, W - ts + 1, ts):
            t = img[r:r + ts, c:c + ts]; t = t[np.isfinite(t)]
            if t.size < 0.9 * ts * ts:
                continue
            k = ki_threshold(t)
            if k is None:
                continue
            a, b = t[t < k], t[t >= k]
            if min(a.size, b.size) < 0.1 * t.size:
                continue
            D = np.sqrt(2) * abs(a.mean() - b.mean()) / np.sqrt(a.var() + b.var())
            if D > 2 and a.mean() < -14:
                th.append(k)
    if len(th) >= 5:
        return float(np.median(th))
    k = ki_threshold(img.ravel())
    return float(k) if k is not None else -16.0


def _fill_hv(hv):
    """HV missing on single-pol passes: take the nearest pass that has HV."""
    out = hv.copy(); have = [t for t in range(len(hv)) if np.isfinite(hv[t]).any()]
    for t in range(len(hv)):
        if t not in have and have:
            out[t] = hv[min(have, key=lambda s: abs(s - t))]
    return out


def coherence(bbox, grid, track, frame, dates, log=print):
    """Mean GUNW coherence per pass on the GCOV grid (pairs that include the pass), or None where no pair exists.
    Pairs cached in data/coh/."""
    import asf_search as asf
    from shapely.geometry import box
    from .nisar import maturity
    from .remote import open_h5
    from .auth import session
    try:
        res = asf.search(dataset="NISAR", processingLevel="GUNW", intersectsWith=box(*bbox).wkt, start="2026-06-17", maxResults=2000)
    except Exception as e:  # noqa: BLE001
        log(f"[warn] GUNW search failed: {e!r}"[:120]); return [None] * len(dates)
    pairs = {}
    for r in res:
        p = r.properties
        if p.get("pathNumber") != track or (frame is not None and p.get("frameNumber") not in (frame, None)) or maturity(p["url"]) is None:
            continue
        import re
        d = re.findall(r"_(\d{8})T\d{6}", p["sceneName"])
        ref, sec = (f"{x[:4]}-{x[4:6]}-{x[6:]}" for x in (d[0], d[2]))
        pairs[(ref, sec)] = p["url"]
    cdir = DATA_DIR / "coh"; cdir.mkdir(parents=True, exist_ok=True)
    s, maps = session(), {}
    for (ref, sec), url in pairs.items():
        if ref not in dates and sec not in dates:
            continue
        cf = cdir / f"{track}_{ref}_{sec}_{grid['x'][0]:.0f}_{grid['y'][0]:.0f}_{len(grid['x'])}x{len(grid['y'])}.npy"
        if cf.exists():
            c = np.load(cf)
        else:
            try:
                with open_h5(url, s) as f:
                    h = f["/science/LSAR/GUNW/grids/frequencyA/unwrappedInterferogram"]
                    hh = h["HH"] if "HH" in h else h[[k for k in h if len(k) == 2][0]]
                    x, y = h["xCoordinates"][()], h["yCoordinates"][()]
                    if int(h["projection"][()]) != grid["epsg"]:
                        continue
                    ci = np.clip(np.searchsorted(x, grid["x"]), 0, len(x) - 1)
                    ri = np.clip(np.searchsorted(-y, -np.asarray(grid["y"])), 0, len(y) - 1)
                    r0, r1, c0, c1 = ri.min(), ri.max() + 1, ci.min(), ci.max() + 1
                    a = np.asarray(hh["coherenceMagnitude"][r0:r1, c0:c1], np.float32)
                    c = a[np.ix_(ri - r0, ci - c0)]
                np.save(cf, c)
            except Exception as e:  # noqa: BLE001
                log(f"[warn] GUNW {ref}->{sec}: {e!r}"[:120]); continue
        if np.nanmedian(c) > COH_BAD:
            maps[(ref, sec)] = c
    out = []
    for d in dates:
        cs = [c for (a, b), c in maps.items() if d in (a, b)]
        out.append(np.nanmean(cs, 0) if cs else None)
    log(f"coherence: {len(maps)} GUNW pairs, {sum(c is not None for c in out)}/{len(dates)} passes covered")
    return out


def _score(x, m):
    z = (x - np.array(m["mu"])) / np.array(m["sd"])
    z = np.nan_to_num(z)
    p = 1 / (1 + np.exp(-(z @ np.array(m["w"]) + m["b"])))
    return p >= m["cut"]


def _clean(w, pixel_m):
    w = ndi.median_filter(w.astype(np.uint8), size=3).astype(bool)          # 3x3 majority
    lab, n = ndi.label(w)
    if n == 0:
        return w
    sz = ndi.sum(np.ones_like(w, float), lab, np.arange(1, n + 1)) * (pixel_m / 1000) ** 2
    return np.isin(lab, np.arange(1, n + 1)[sz >= MIN_PATCH_KM2])


def detect_fused(stack, dates, grid, bbox, track=None, frame=None, dry_dates=None, log=print):
    """stack (T,2,H,W) linear gamma0 HH, HV after qa(). Returns dict like detect.detect(): water, canopy, valid,
    permanent (+ thresholds, dry passes, coherence coverage).
    dry_dates: passes known to be before the flood (else the first N_DRY passes)."""
    from .detect import detect
    with np.errstate(divide="ignore", invalid="ignore"):
        hh = 10 * np.log10(stack[:, 0]); hv = _fill_hv(10 * np.log10(stack[:, 1]))
    T = len(dates)
    th = [tile_threshold(hh[t]) for t in range(T)]; tv = [tile_threshold(hv[t]) for t in range(T)]
    dry = [i for i, d in enumerate(dates) if dry_dates and d in dry_dates] or list(range(min(N_DRY, T)))
    with np.errstate(all="ignore"):
        rh = np.nanmedian(hh[dry], 0); rv = np.nanmedian(hv[dry], 0)
    coh = coherence(bbox, grid, track, frame, dates, log) if track is not None else [None] * T
    water = np.zeros(hh.shape, bool); used_coh = []
    for t in range(T):
        f = [hh[t] - th[t], hv[t] - tv[t], hh[t] - rh, hv[t] - rv, hh[t] - hv[t], np.full(hh[t].shape, MODEL_COH["mu"][5]), rh - th[t]]
        if coh[t] is not None:
            w = _score(np.stack(f + [coh[t]], -1), MODEL_COH); used_coh.append(True)
        else:
            w = _score(np.stack(f, -1), MODEL_NOCOH); used_coh.append(False)
        water[t] = _clean(w, grid["dx"])
    valid = np.isfinite(hh).all(0)
    water &= valid[None]
    old = detect(stack, pixel_m=grid["dx"])                                # double bounce = water under vegetation
    canopy = old["canopy"] & ~water
    permanent = (water.mean(0) >= 0.9) & valid
    return dict(water=water, canopy=canopy, valid=valid, permanent=permanent,
                info=dict(detector="fused v3", thresholds_hh=[round(v, 1) for v in th], thresholds_hv=[round(v, 1) for v in tv],
                          dry_passes=[dates[i] for i in dry], coherence=used_coh))
