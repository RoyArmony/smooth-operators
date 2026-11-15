# GERD reservoir, Blue Nile, 2016–2026: flood history

Same 12,866 km² box, early October each year (Sentinel-1): open water 31 km² in 2016 (river, before the dam), 1,518 km² in 2025 (the reservoir). Flood beyond the lake: 399 km² on 2026-11-02 (NISAR).

**Images:** 14. Sentinel-1 (ESA Copernicus, C-band): 10, one a year near 1 October, always the same orbit track,
so the years compare. NISAR (L-band) 2026 passes, each with NASA OPERA DSWx-HLS where it exists.

**Method:** everything on NISAR's 80 m grid. Sentinel-1: terrain-corrected gamma0 (RTC), water = VV < -13.2 dB
and VH < -18.9 dB (Otsu on 2025-09-29, the same for every year). NISAR: our detector. Flood = water beyond the lake
NISAR sees on ≥ 90 % of its passes, so "open water" shows the reservoir filling and "flood" shows how far it spreads past it.

**Limits:** C-band and L-band differ (wind-roughened water, shadows in the gorge); one threshold for all Sentinel-1 years:
compare the pattern, not exact km². One image a year cannot catch the yearly peak. Audit: docs/10-Results.md.
