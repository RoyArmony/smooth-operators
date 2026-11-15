# Peace-Athabasca Delta flood, Jun 2026

On 2026-06-24, NISAR adds 3 km² of flood (+0%) where NASA's flood map (OPERA DSWx-HLS) cannot see.

**Window:** 2026-05-25 → 2026-07-24 (flood date ± 30 days), 3 NISAR passes, every 12 days.

**Baselines:** Copernicus GFM (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow)
and NASA OPERA DSWx-HLS (optical; "cannot see" = clouds). Matched to each pass: GFM ± 2 d, DSWx ± 3 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; shallow delta lakes roughened by wind are not dark on ≥ 90 % of passes, so part of them counts as flood here (in NISAR and in the baseline alike); numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.

**Independent check (RCM):** Canada's RCM radar, within 3 days of 2 NISAR passes, agrees on 90% of pixels (open water IoU 0.6). RCM (Canadian Space Agency, C-band, compact-pol) is a different radar,
band and orbit. Its water = one Otsu threshold per image on the RL band (tiles with both water and land), on our 80 m
grid; compared with NISAR open water only, where both see. Layers `rcm_water` and `agreement`.
