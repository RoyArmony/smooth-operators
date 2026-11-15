# Mekong delta, 1998–2026: flood history

**What:** the same 66 × 66 km of the Mekong delta (Dong Thap / An Giang), flooded every year Aug–Dec.
Same delta, 25 years apart: RADARSAT-1 saw 2,830 km² flooded on 2001-08-30; NISAR saw 1,854 km² on 2026-09-23, the official map (GFM) 706 km².

**Data:** RADARSAT-1 (CSA, C-band HH; 1998, 2001, 2005, 2006 Mar–Dec, 2007) and NISAR (L-band HH+HV, Jun–Oct 2026),
on one 80 m grid. On NISAR dates, Copernicus GFM (Sentinel-1) the same day ± 3 d.

**Method** (`pipeline/unseen/history.py`): RADARSAT-1 warped with its GCPs and aligned to NISAR by edges; one water
threshold per image (Otsu on tiles holding both river and land). NISAR: our detector, thresholds calibrated on clear
optical days. Flood = water beyond permanent water. `agreement`: both / only NISAR / only GFM.

**Limits:** two radars (C vs L band) and two methods: compare the pattern (dry ≈ 100–350 km², flood ≈ 1,500–2,800 km²),
not exact km². Paddies are flooded on purpose; dikes keep some fields dry. Numbers: docs/10-Results.md.
