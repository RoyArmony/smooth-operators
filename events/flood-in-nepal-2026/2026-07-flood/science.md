# Nepal floods flood, Jul 2026

On 2026-07-26, NISAR adds 1 km² of flood (+None%) where the official flood map (Copernicus GFM) cannot see.

**Window:** 2026-06-26 → 2026-08-25 (flood date ± 30 days), 4 NISAR passes, every 12 days.

**Baselines:** Copernicus GFM (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow)
and NASA OPERA DSWx-HLS (optical; "cannot see" = clouds). Matched to each pass: GFM ± 2 d, DSWx ± 3 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; paddies are flooded on purpose in season; numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.
