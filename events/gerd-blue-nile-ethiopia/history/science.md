# GERD reservoir, Blue Nile, 1998–2026: flood history

Same 12,866 km² box: RADARSAT-1 picture on 1998-07-09; flood 399 km² on 2026-11-02 (NISAR).

**Images:** 5, about one every month or two (each year's wettest kept). RADARSAT-1 (CSA, C-band),
NISAR (L-band) 2026 (years: see the image list). Each with our flood map, a photo near the same day (MODIS from 2000, HLS in 2026), and the
official flood maps where they exist (GFM from 2015, NASA DSWx-HLS from 2023: 2026 only).

**Method:** everything on NISAR's 80 m grid. RADARSAT-1: GCP warp, edge alignment, one threshold per image.
NISAR: our detector. Flood = water beyond permanent water.

**Limits:** Only one RADARSAT-1 scene reaches GERD (9 Jul 1998, ScanSAR, 74 % of the box; the dam site is just outside it): a before-the-dam picture, no flood km². The reservoir fills every rainy season, so 'flood' here = water beyond the lake on ≥ 90 % of NISAR passes, i.e. how far the lake grows. No GFM (server down at build time). Audit: docs/10-Results.md.
