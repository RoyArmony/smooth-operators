"""NASA's inundation method (NISAR Science Users' Handbook §6.3.2 + §6.4, eqs 6.3-5/6, 6.4-1..7), on a GCOV stack.

A second, independent opinion next to detect.py. Steps:
  1. relative calibration: rescale each date so a stable area A has the same mean on every date
        f_n = <sigma(A)>_t / sigma_n(A)            sigma^c_n = f_n * sigma_n          (6.3-5, 6.3-6, linear power)
  2. reference = multi-temporal average sigma_bar: handbook = the 2n calibrated passes around each date (window=
     'centered'); default here = the last n dry passes before it, per pixel (window='past': no look-ahead, a lasting flood isn't
     absorbed into its own reference); the pre-event passes when an event date is known
  3. class of the reference ("typical" state):
        IV  if HH/HV > T_r_iv  and HH > T_HH_iv                                      (6.4-1, double bounce)
        OW  if HH/HV > T_r_ow  and HH < T_HH_ow                                      (6.4-2, mirror-like water)
        NC  if T_r_in > HH/HV > T_r_ow and T_HH_in > HH > T_HH_ow                    (6.4-3, in between)
        NI  otherwise
  4. change of each date vs the reference (ratios = differences in dB):
        N2IV: C=NI, HH_n > T_HH_veg, HH_n/HH_bar > T_tr_min_iv, HV_n/HV_bar < T_tr_HV_max     (6.4-4)
        IV2N: C=IV, HH_n > T_HH_veg, HH_n/HH_bar < T_tr_max_iv, HV_n/HV_bar > T_tr_HV_min     (6.4-5)
        N2O : C=NI, HH_n < T_HH_veg, HH_n/HH_bar < T_tr_max_ow                                 (6.4-6)
        O2N : C=OW, HH_n < T_HH_veg, HH_n/HH_bar > T_tr_min_ow                                 (6.4-7)
  5. error layer: distance (dB) of each pixel from the decisive threshold vs the observed noise -> P(correct)
The handbook leaves every threshold to calibration and lets it depend on incidence angle. Our defaults (below) are
starting values: T_HH_ow comes from detect.calibrate() (learned from optical) when available; the change thresholds
match detect.py (DB_RISE, DB_HV_MAX, DARKEN_DB) so the two methods differ in *structure*, not in tuning.
See docs/20-Flood-method.md.
"""
import numpy as np
from scipy.special import erf

from .detect import _db, OPEN_HH, DB_RISE, DB_HV_MAX, DARKEN_DB, FIELD_MAX_HH

NI, IV, OW, NC = 0, 1, 2, 3                       # classes (handbook: NI, IV, OW, NC)
N2IV, IV2N, N2O, O2N = 1, 2, 3, 4                 # transitions
T = dict(                                         # dB (a ratio threshold = a difference in dB)
    r_iv=8.0, HH_iv=-6.0,                         # IV: bright HH, HH well above HV (double bounce keeps polarization)
    r_ow=0.0, HH_ow=OPEN_HH,                      # OW: dark HH; ratio test kept but lenient (HV sits near the noise floor)
    r_in=8.0, HH_in=OPEN_HH + 3.0,                # NC band between water and land
    HH_veg=FIELD_MAX_HH,                          # min HH of vegetated / non-water terrain
    tr_min_iv=DB_RISE, tr_HV_max=DB_HV_MAX,       # N2IV: HH up, HV steady
    tr_max_iv=-DB_RISE, tr_HV_min=-DB_HV_MAX,     # IV2N: HH down, HV steady
    tr_max_ow=-DARKEN_DB, tr_min_ow=DARKEN_DB)    # N2O / O2N: HH down / up


def _rel_cal(p_hh, p_hv, stable):
    """Eq 6.3-5/6 on linear power: f_n = mean_t <sigma(A)> / <sigma_n(A)>, per polarization."""
    if stable.sum() < 50:
        return p_hh, p_hv, np.ones(len(p_hh))
    m_hh = np.array([np.nanmean(x[stable]) for x in p_hh]); m_hv = np.array([np.nanmean(x[stable]) for x in p_hv])
    f_hh, f_hv = m_hh.mean() / m_hh, m_hv.mean() / m_hv
    return p_hh * f_hh[:, None, None], p_hv * f_hv[:, None, None], f_hh


def _ref_idx(dates, t, n, event_date, window):
    """Which passes form the reference sigma_bar for pass t.
    event_date: the pre-event passes. window='centered': handbook (n before + n after). window='past': the n passes
    before t only (no look-ahead: a later flood can't leak into the reference; each new pass needs only the last n).
    In classify(), 'past' is refined per pixel to the last n *dry* passes (the state before the flood)."""
    if event_date:
        pre = [i for i, d in enumerate(dates) if d < event_date]
        if pre:
            return pre if t >= len(pre) else [i for i in pre if i != t] or pre
    if window == "past" and t >= 1:
        return list(range(max(0, t - n), t))
    lo, hi = max(0, t - n), min(len(dates), t + n + 1)
    idx = [i for i in range(lo, hi) if i != t]
    return idx or [t]


def _p(margin, sd):
    """P(class is right) from the margin to the decisive threshold, Gaussian noise of sd dB."""
    z = np.clip(margin / max(sd, 0.3), -6, 6)
    return 0.5 * (1 + erf(z / np.sqrt(2)))


def classify(stack, dates, event_date=None, n=3, thresholds=None, window="past", wet_mask=None, no_iv=None):
    """stack (T,2,H,W) linear gamma0 (HH, HV). Returns dict:
      cls (T,H,W) final class per date (NI/IV/OW/NC), trans (T,H,W) transition code (0 = none),
      ref_cls (T,H,W) class of the reference state, conf (T,H,W) P(correct) 0..1, cal_factor (T,), flooded (T,H,W),
      new (T,H,W) flooded now but not in the reference (N2O / N2IV) = the flood.
    wet_mask (H,W): handbook a-priori wetland mask; the static IV class (6.4-1) is only allowed inside it, because
      cities, orchards and some crops double-bounce like flooded trees all year. None = everywhere.
    no_iv (H,W): where N2IV is not allowed either (built-up: buildings brighten with rain / moisture)."""
    th = dict(T, **(thresholds or {}))
    hh_db, hv_db, valid = _db(stack)                                      # same speckle filter as detect.py
    p_hh, p_hv = 10 ** (hh_db / 10), 10 ** (hv_db / 10)
    water_ever = (hh_db < th["HH_ow"]).any(0)
    sd_t = np.std(hh_db, 0)
    stable = valid & ~water_ever & (sd_t < np.percentile(sd_t[valid], 30)) if valid.any() else valid
    p_hh, p_hv, f = _rel_cal(p_hh, p_hv, stable)
    hh, hv = 10 * np.log10(np.maximum(p_hh, 1e-6)), 10 * np.log10(np.maximum(p_hv, 1e-6))
    noise = float(np.median(np.std(hh[:, stable], 0))) if stable.any() else 1.0    # observed dB scatter of stable land

    Tn, H, W = hh.shape
    cls = np.zeros((Tn, H, W), np.uint8); trans = np.zeros_like(cls); ref = np.zeros_like(cls)
    conf = np.zeros((Tn, H, W), np.float32)
    for t in range(Tn):
        idx = _ref_idx(dates, t, n, event_date, window)
        if window == "past" and not event_date and t >= 1:
            # per pixel: the last n passes that were NOT flooded (lookback 3n), so a lasting flood isn't absorbed into
            # the reference; pixels flooded on all of them (permanent water) fall back to every pass in the lookback
            look = list(range(max(0, t - 3 * n), t))
            dry = np.stack([cls[i] == NI for i in look]).astype(np.float32)
            keep = np.cumsum(dry[::-1], 0)[::-1] <= n                     # the n most recent dry ones
            w = dry * keep
            w = np.where(w.sum(0) > 0, w, 1.0)
            bh = 10 * np.log10(np.maximum((p_hh[look] * w).sum(0) / w.sum(0), 1e-6))
            bv = 10 * np.log10(np.maximum((p_hv[look] * w).sum(0) / w.sum(0), 1e-6))
        else:
            bh = 10 * np.log10(np.maximum(p_hh[idx].mean(0), 1e-6))      # sigma_bar (mean in linear, shown in dB)
            bv = 10 * np.log10(np.maximum(p_hv[idx].mean(0), 1e-6))
        r = bh - bv
        C = np.full((H, W), NI, np.uint8)
        C[(r > th["r_ow"]) & (r < th["r_in"]) & (bh > th["HH_ow"]) & (bh < th["HH_in"])] = NC           # 6.4-3
        C[(r > th["r_ow"]) & (bh < th["HH_ow"])] = OW                                                    # 6.4-2
        C[(r > th["r_iv"]) & (bh > th["HH_iv"]) & (True if wet_mask is None else wet_mask)] = IV          # 6.4-1, in mask
        dh, dv = hh[t] - bh, hv[t] - bv                                    # HH_n/HH_bar, HV_n/HV_bar in dB
        Tr = np.zeros((H, W), np.uint8)
        Tr[(C == NI) & (hh[t] > th["HH_veg"]) & (dh > th["tr_min_iv"]) & (dv < th["tr_HV_max"])
           & (True if no_iv is None else ~no_iv)] = N2IV                                                 # 6.4-4
        Tr[(C == IV) & (hh[t] > th["HH_veg"]) & (dh < th["tr_max_iv"]) & (dv > th["tr_HV_min"])] = IV2N  # 6.4-5
        Tr[(np.isin(C, (NI, NC))) & (hh[t] < th["HH_veg"]) & (dh < th["tr_max_ow"])] = N2O              # 6.4-6 (+NC)
        Tr[(C == OW) & (hh[t] < th["HH_veg"]) & (dh > th["tr_min_ow"])] = O2N                           # 6.4-7
        Cf = C.copy()                                                      # C replaced by C' where C' is nonzero
        Cf[Tr == N2IV] = IV; Cf[Tr == IV2N] = NI; Cf[Tr == N2O] = OW; Cf[Tr == O2N] = NI
        # error layer: margin of the decisive test, in dB, against the observed noise
        m = np.where(Cf == OW, th["HH_ow"] - hh[t],
            np.where(Cf == IV, np.minimum(hh[t] - th["HH_iv"], (hh[t] - hv[t]) - th["r_iv"]),
            np.where(Cf == NC, 0.0, np.minimum(hh[t] - th["HH_ow"], np.maximum(th["HH_iv"] - hh[t], th["r_iv"] - (hh[t] - hv[t]))))))
        m = np.where(Tr > 0, np.maximum(m, np.abs(dh) - abs(th["tr_min_iv"])), m)
        conf[t] = np.where(valid, _p(m, noise), 0)
        Cf[~valid] = NC; Tr[~valid] = 0
        cls[t], trans[t], ref[t] = Cf, Tr, C
    flooded = np.isin(cls, (OW, IV))
    new = np.isin(trans, (N2O, N2IV))
    return dict(cls=cls, trans=trans, ref_cls=ref, conf=conf, cal_factor=f, flooded=flooded, new=new, noise_db=noise,
                thresholds=th)


def masks_from_landcover(lc):
    """Handbook 6.4.2 a-priori mask from ESA WorldCover: wetland, mangrove, permanent water = where static IV may
    exist; built-up = no double-bounce flooding. Returns (wet_mask, no_iv); (None, None) without land cover."""
    if lc is None:
        return None, None
    return np.isin(lc, (80, 90, 95)), lc == 50


def to_hectare(cls, pixel_m):
    """1 ha cells by majority vote (handbook 6.4.2). At 80 m a pixel is already 0.64 ha: returned unchanged."""
    k = int(round(100 / pixel_m))
    if k <= 1:
        return cls
    H, W = cls.shape[-2] // k * k, cls.shape[-1] // k * k
    c = cls[..., :H, :W].reshape(*cls.shape[:-2], H // k, k, W // k, k)
    votes = np.stack([(c == v).sum((-1, -3)) for v in (NI, IV, OW, NC)])
    return votes.argmax(0).astype(np.uint8)
