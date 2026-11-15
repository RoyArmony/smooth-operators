# Sylhet haor (validation), Oct 2026

Where the official maps can see: Copernicus GFM and NISAR agree on 79% of pixels (open water IoU 0.69, 5 passes). NASA's DSWx map and NISAR agree on 77% of pixels (open water IoU 0.61, 4 passes). NASA's LANCE flood map and NISAR agree on 80% of pixels (open water IoU 0.55, 6 passes).

**Window:** 2026-09-10 → 2026-11-09 (flood date ± 30 days), 6 NISAR passes, every 12 days.

**Baselines:** Copernicus GFM (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow)
and NASA OPERA DSWx-HLS (optical; "cannot see" = clouds). Matched to each pass: GFM ± 2 d, DSWx ± 3 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; validation site: seasonal haor wetland, mostly flooded farmland, little tree cover; GFM covers about half the box (its Sentinel-1 scene), so scores are where GFM sees; numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.

**Check against NASA's map (DSWx-HLS):** NASA's DSWx map and NISAR agree on 77% of pixels (open water IoU 0.61, 4 passes).  Same open-water masks, only where DSWx has no cloud.
Layer `dswx_water`.

**Check against the other official maps:** NISAR water (incl. permanent) vs each map's water (flood + normal water),
only where that map can see (LANCE: no cloud or terrain mask; GFM: outside its exclusion mask) and NISAR is valid.
Layers `lance_water`, `gfm_water`, `nisar_open`.

- NASA's LANCE flood map and NISAR agree on 80% of pixels (open water IoU 0.55, 6 passes).
- Copernicus GFM and NISAR agree on 79% of pixels (open water IoU 0.69, 5 passes).
