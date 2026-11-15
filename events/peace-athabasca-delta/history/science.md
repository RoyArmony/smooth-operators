# Peace-Athabasca Delta, 1997–2026: flood history

Same 3,147 km² box: flood 595 km² on 2012-07-04 (RADARSAT-1), 440 km² on 2026-06-24 (NISAR).

**Images:** 26, about one every month or two (each year's wettest kept). RADARSAT-1 (CSA, C-band),
NISAR (L-band) 2026 (years: see the image list). Each with our flood map, a photo near the same day (MODIS from 2000, HLS in 2026), and the
official flood maps where they exist (GFM from 2015, NASA DSWx-HLS from 2023: 2026 only).

**Method:** everything on NISAR's 80 m grid. RADARSAT-1: GCP warp, edge alignment, one threshold per image.
An image is dropped when its threshold does not separate the known permanent water from land
(Youden J < 0.5: wind on the lakes, wet snow, low contrast). NISAR: our detector. Flood = water beyond permanent water.

**Limits:** C-band misses water under willow and sedge that L-band sees; one threshold per image vs a calibrated detector: compare the pattern, not exact km². RADARSAT-1 May–Sep only (ice and freeze-up from Oct). MODIS is 250 m. Audit: docs/10-Results.md.
