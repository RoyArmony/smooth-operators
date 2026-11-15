# Dead Sea (validation), Oct 2026

Clear sky, no vegetation: NASA's DSWx map and NISAR agree on 74% of pixels (open water IoU 0.46, 5 passes). NASA's LANCE flood map and NISAR agree on 73% of pixels (open water IoU 0.36, 5 passes).

**Window:** 2026-09-10 → 2026-11-09 (flood date ± 30 days), 5 NISAR passes, every 12 days.

**Baselines:** Copernicus GFM (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow)
and NASA OPERA DSWx-HLS (optical; "cannot see" = clouds). Matched to each pass: GFM ± 2 d, DSWx ± 3 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; validation site, not a flood: desert valley floor (open water, salt ponds, bare shore), no vegetation, almost always cloud-free; numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.

**Check against NASA's map (DSWx-HLS):** NASA's DSWx map and NISAR agree on 74% of pixels (open water IoU 0.46, 5 passes).  Same open-water masks, only where DSWx has no cloud.
Layer `dswx_water`.

**Check against the other official maps:** NISAR water (incl. permanent) vs each map's water (flood + normal water),
only where that map can see (LANCE: no cloud or terrain mask; GFM: outside its exclusion mask) and NISAR is valid.
Layers `lance_water`, `gfm_water`, `nisar_open`.

- NASA's LANCE flood map and NISAR agree on 73% of pixels (open water IoU 0.36, 5 passes).
