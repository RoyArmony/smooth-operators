# Sylhet haor, 1996–2026: flood history

Same 4,011 km² box: flood 931 km² on 2002-07-01 (RADARSAT-1), 920 km² on 2026-07-24 (NISAR).

**Images:** 9, about one every month or two (each year's wettest kept). RADARSAT-1 (CSA, C-band),
NISAR (L-band) 2026 (years: see the image list). Each with our flood map, a photo near the same day (MODIS from 2000, HLS in 2026), and the
official flood maps where they exist (GFM from 2015, NASA DSWx-HLS from 2023: 2026 only).

**Method:** everything on NISAR's 80 m grid. RADARSAT-1: GCP warp, edge alignment, one threshold per image.
An image is dropped when its threshold does not separate the known permanent water from land
(Youden J < 0.5: wind on the lakes, wet snow, low contrast). NISAR: our detector. Flood = water beyond permanent water.

**Limits:** C-band misses some water under rice that L-band sees; one threshold per image vs a calibrated detector:
compare the pattern (dry vs flood, then vs now), not exact km². Paddies are flooded on purpose; dikes keep some fields
dry. MODIS is 250 m and often cloudy in the wet season. Audit: docs/10-Results.md.
