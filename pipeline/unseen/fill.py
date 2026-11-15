"""Smart fill with height (GLO-30 HAND), docs/07 §2c. Optional step after the detector (`--fill`).

Grow the detected water into neighbouring pixels that are
  * low:   HAND <= local water level + tol, where the local water level = HAND of the nearest flood-edge pixel, and
  * near the radar's water threshold: water probability >= p_low (v3 calls water at 0.30),
within max_km of the flood. Grown step by step from the flood (connected), so isolated low spots are not added.

Inner Niger (very flat, median HAND 0.2 m): no F1 gain (0.70 -> 0.70); kept off by default until tested where
there is relief."""
import numpy as np
from scipy import ndimage as ndi

P_LOW, TOL_M, MAX_KM = 0.25, 0.0, 2.0      # best on Inner Niger track 145


def smart_fill(water, prob, hand, pixel_m=80.0, p_low=P_LOW, tol=TOL_M, max_km=MAX_KM, max_steps=60):
    """water (H,W) bool, prob (H,W) water probability, hand (H,W) metres. Returns the filled water mask."""
    if not water.any() or hand is None:
        return water
    edge = water & ~ndi.binary_erosion(water)
    _, (ri, ci) = ndi.distance_transform_edt(~edge, return_indices=True)
    level = hand[ri, ci]                                       # water level from the nearest flood edge
    dist = ndi.distance_transform_edt(~water) * pixel_m / 1000
    cand = np.isfinite(hand) & (hand <= level + tol) & (prob >= p_low) & (dist <= max_km)
    out = water.copy()
    for _ in range(max_steps):
        nxt = ndi.binary_dilation(out) & cand & ~out
        if not nxt.any():
            break
        out |= nxt
    return out


def apply(L, grid, bbox, key=None, **kw):
    """Fill every pass of a detector result L (needs L['prob']). Adds L['filled'] (km2 added per pass)."""
    from . import hand as handmod
    h = handmod.on_grid(grid, bbox, key=key)
    if h is None or "prob" not in L:
        print("[warn] smart fill skipped (no HAND or no probability layer)"); return L
    px = (grid["dx"] / 1000) ** 2; added = []
    for t in range(len(L["water"])):
        w = smart_fill(L["water"][t], L["prob"][t], h, grid["dx"], **kw) & L["valid"]
        added.append(round(float((w & ~L["water"][t]).sum() * px), 1)); L["water"][t] = w
    L["filled_km2"] = added
    return L
