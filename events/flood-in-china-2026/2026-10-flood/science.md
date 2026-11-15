# Hubei floods flood, Oct 2026

On 2026-10-03, NISAR adds 5 km² of flood (+None%) where the official flood map (Copernicus GFM) cannot see.

**Window:** 2026-09-27 → 2026-11-26 (flood date ± 30 days), 3 NISAR passes, every 12 days.

**Baselines:** Copernicus GFM (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow)
and NASA OPERA DSWx-HLS (optical; "cannot see" = clouds). Matched to each pass: GFM ± 2 d, DSWx ± 3 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; paddies are flooded on purpose in season; numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.

**Check against NASA's map (DSWx-HLS):** NASA's DSWx map and NISAR agree on 92% of pixels (open water IoU 0.18, 2 passes).  Same open-water masks, only where DSWx has no cloud.
Layer `dswx_water`.
