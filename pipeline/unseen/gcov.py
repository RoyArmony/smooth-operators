"""NISAR L2 GCOV reader. Layout verified on NISAR_L2_PR_GCOV PROVISIONAL_V1 granules (Oct 2026):

  science/LSAR/GCOV/grids/frequencyA|B/{HHHH,HVHV,...}   float32 linear gamma0 (RTC), NaN fill, 512x512 gzip chunks
  .../xCoordinates, yCoordinates                         map coordinates (UTM), pixel centres
  .../projection                                         EPSG code (int)
  science/LSAR/identification/zeroDopplerStartTime        acquisition time
Frequency A = 20 m (mode 2005) or 10 m (mode 4005); frequency B = 80 m. Single-pol (SHSH) dates have no HVHV.
"""
import datetime as dt
import os
import numpy as np

from .remote import open_h5

GRID = "/science/LSAR/GCOV/grids/frequency{freq}"
TIME = "/science/LSAR/identification/zeroDopplerStartTime"


def read(url, terms=("HHHH", "HVHV"), freq="B", window=None, session=None):
    """Returns (array (P,H,W) float32 linear, meta). Missing terms come back all-NaN."""
    with open_h5(url, session) as f:
        g = f[GRID.format(freq=freq)]
        sl = np.s_[:, :] if window is None else np.s_[window[0]:window[1], window[2]:window[3]]
        x, y = g["xCoordinates"][()], g["yCoordinates"][()]
        if window is not None:
            y, x = y[window[0]:window[1]], x[window[2]:window[3]]
        layers = [np.asarray(g[t][sl], np.float32) if t in g else np.full((len(y), len(x)), np.nan, np.float32) for t in terms]
        epsg = int(g["projection"][()])
        date = dt.date.fromisoformat(f[TIME][()].decode()[:10])
    arr = np.stack(layers)
    arr[~(arr > 0)] = np.nan
    return arr, dict(x=x, y=y, epsg=epsg, date=date, source=os.path.basename(str(url)))


def fill_time_gaps(stack):
    """Fill all-NaN (date, pol) layers (e.g. HV on single-pol dates) with the nearest-in-time valid layer."""
    out = stack.copy()
    T, P = stack.shape[:2]
    for p in range(P):
        valid = [t for t in range(T) if np.isfinite(stack[t, p]).any()]
        for t in range(T):
            if t not in valid and valid:
                out[t, p] = stack[min(valid, key=lambda v: abs(v - t)), p]
    return out
