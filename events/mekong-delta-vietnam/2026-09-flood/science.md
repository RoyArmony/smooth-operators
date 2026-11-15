# Mekong delta flood, Sep 2026

On 2026-09-23, NISAR adds 90 km² of flood (+13%) where the official flood map (Copernicus GFM) cannot see.

**Window:** 2026-08-24 → 2026-10-23 (flood date ± 30 days), 5 NISAR passes, every 12 days.

**Baseline:** Copernicus GFM only (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow).
Matched to each pass: GFM ± 2 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; paddies are flooded on purpose in season; numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.
