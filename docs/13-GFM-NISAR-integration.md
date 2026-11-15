# 13 · Guide: adding NISAR L-band to Copernicus GFM

For the Copernicus **Global Flood Monitoring (GFM)** team. How to use NASA–ISRO **NISAR** L-band radar to map flood water
inside GFM's exclusion mask ("cannot see": dense forest, flooded vegetation, some urban areas).

From team Smooth Operators (NASA Space Apps 2026, Haifa). Live demo: **https://unseenearth.us** · Code: this repo, `pipeline/`.
Based on the NISAR Data User Guide (ASF), the NISAR Science Users' Handbook (JPL 2025, §6.3–6.4) and our tests.

## 1. Why

- GFM uses Sentinel-1 **C-band**. C-band scatters off the canopy, so water under trees and tall vegetation is not seen.
  GFM marks these pixels in its exclusion mask.
- NISAR **L-band** (24 cm) passes through the canopy. Water under trees gives a strong **double bounce** (HH up, HV steady).
  Open water stays dark (specular).
- NISAR covers all land every **12 days**, ascending + descending, free and open (NASA Earth science data policy).

Our first result (17 sites, Jun–Oct 2026, one pass each): NISAR found **2,177 km²** of water inside GFM's "cannot see" areas;
median **+20 %** flood area per site (74 % in total). Agreement with Canada's RCM radar (≤ 3 days apart): **90 %**
(Peace–Athabasca, Jul 2026). Candidate water, not ground-checked; NISAR products are still provisional.

## 2. Flow

```mermaid
flowchart LR
  A[GFM event / AOI] --> B[Find NISAR GCOV<br/>ASF, ±3 days]
  B --> C[Read HH, HV<br/>box only, over HTTP]
  C --> D[Water + flooded vegetation<br/>L-band classifier]
  D --> E[Keep pixels inside<br/>GFM exclusion mask]
  E --> F[New layer:<br/>'NISAR flood under vegetation']
  F --> G[GFM product / viewer]
```

GFM's own Sentinel-1 flood extent stays as is. NISAR only fills the exclusion mask. No change to GFM's ensemble.

## 3. Data

| Item | Value |
|---|---|
| Product | **NISAR L2 GCOV** (geocoded polarimetric covariance), L-band (NASA) |
| Collections | `NISAR_L2_GCOV_V1` (VALIDATED, from 21 Oct 2026) · PROVISIONAL (from 17 Jun 2026) · skip BETA |
| Bands | `science/LSAR/GCOV/grids/frequencyA` (20 MHz, ~20 m) and `frequencyB` (5 MHz, 80 m): `HHHH`, `HVHV` (γ⁰, linear power) |
| Format | HDF5, 0.2–8 GB per frame, 512 × 512 chunks: read only the AOI over HTTP (`h5py` + `fsspec`) |
| Revisit | 12 days per orbit direction (≈ 6 days with both) |
| Coherence (optional) | **NISAR L2 GUNW**: 12-day interferometric coherence; water decorrelates |
| Access | NASA Earthdata Login (free) → ASF DAAC. Search: `asf_search` or CMR |
| Latency | ASF publishes after processing; check the NISAR Data User Guide for current latency |

```python
import asf_search as asf
r = asf.search(dataset="NISAR", processingLevel="GCOV",
               intersectsWith=aoi_wkt, start=t0, end=t1)
```

Rules we use: one track + frame + direction + bandwidth mode per stack, ≥ 90 % AOI cover, NISAR date within ±2–3 days of the GFM date.

## 4. Method (handbook §6.3–6.4, plus our checks)

1. **Calibrate the stack** (handbook eq. 6.3-5/6): scale each pass so its scene mean matches the stack mean (per polarisation).
2. **Quality check:** drop a pass if its scene median HH is > 3 dB off the stack median.
3. **Classify each pass** (handbook eq. 6.4-1 … 6.4-3), with `r = HH/HV`:
   - **OW** open water: high `r`, HH very low (specular).
   - **IV** inundated vegetation: high `r`, HH high (double bounce). Allow only inside an a-priori wetland mask (e.g. ESA WorldCover wetland, mangrove).
   - **NI / NC**: not inundated / not classified.
4. **Change rules** (eq. 6.4-4 … 6.4-7): compare each pass with the pixel's own dry-season mean. Flood = new OW or new IV
   (HH up ≥ ~3 dB with HV steady → N2IV; HH down → N2O).
5. **Confidence:** P = Φ(m/σ) ≥ 0.8 (handbook), where m is the margin to the threshold.
6. **Open water, better F1** (our v3, `pipeline/unseen/fused.py`): per-scene Kittler–Illingworth threshold on tiles
   (Martinis et al. 2015, the DLR method in GFM) + HV + dry-season change + GUNW coherence, logistic score.
   Inner Niger, held-out track: F1 0.70 vs 0.57–0.61 (handbook classifier) and 0.61 (threshold only), truth = OPERA DSWx-HLS.
7. **Clean-up:** remove permanent water (open on ≥ 90 % of passes), 3 × 3 majority filter, patches < 0.1 km²,
   slopes > 5° (or HAND filter, GLO-30 HAND).
8. **Combine with GFM:** `nisar_add = NISAR_flood ∧ GFM_exclusion_mask ∧ both_valid`.
   Combined map = `GFM_ensemble_flood_extent ∨ nisar_add`. Keep `nisar_add` as its own class so users see the source.

GFM inputs (EODC STAC `https://stac.eodc.eu/api/v1`, collection `GFM`): `ensemble_flood_extent`, `exclusion_mask`,
`ensemble_water_extent`. Reproject to the NISAR grid with nearest neighbour.

## 5. Validation we suggest

| Check | How |
|---|---|
| Independent radar | RCM (CSA) or Sentinel-1 open water on near-same days, outside the exclusion mask: agreement, IoU, F1 |
| Optical | OPERA DSWx-HLS on clear days (open water only; optical can't see under canopy) |
| Ground | water-level gauges under forest (e.g. Everglades EDEN) for the IV class |
| Plausibility | wet % over the season should rise and fall with the river gauge; dry season should be near zero |

## 6. Integration options

| Option | Effort | What GFM gets |
|---|---|---|
| A · Extra layer | low | `nisar_flood_under_vegetation` + date, in the viewer, next to the exclusion mask |
| B · Fill the mask | medium | GFM flood extent with excluded pixels filled by NISAR, flagged by source |
| C · Fourth algorithm | high | NISAR as a new member of the ensemble (L-band, different revisit) |

Start with A: it needs no change to the Sentinel-1 ensemble and is easy to compare.

## 7. Limits

- NISAR is new: PROVISIONAL data until 21 Oct 2026; calibration still changing.
- 12-day revisit per direction: NISAR may miss a flood peak that Sentinel-1 caught; use the date offset in the layer.
- Thresholds depend on place and land cover; the handbook classifier needs a dry-season reference and a wetland prior.
- Wet soil after rain and some dry, smooth ground can look like water at L-band; coherence helps.
- Our tests cover a few sites (Inner Niger, Mekong, Tonle Sap, Peace–Athabasca); not a global validation.

## 8. References

- NISAR Data User Guide (ASF): https://nisar-docs.asf.alaska.edu/
- NISAR Mission Science Users' Handbook (JPL, 2025), §6.3–6.4 inundation: https://doi.org/10.48577/jpl.UD4HV3
- NISAR data use and citation: https://nisar-docs.asf.alaska.edu/data-use-citation-guidance/
- ASF search (Vertex / `asf_search`): https://search.asf.alaska.edu/ · https://docs.asf.alaska.edu/asf_search/basics/
- NASA Earthdata Login: https://urs.earthdata.nasa.gov
- Copernicus GFM: https://global-flood.emergency.copernicus.eu · STAC: https://stac.eodc.eu/api/v1
- Martinis S., Kersten J., Twele A. (2015). A fully automated TerraSAR-X based flood service. ISPRS J. Photogramm. Remote Sens. 104, 203–212. https://doi.org/10.1016/j.isprsjprs.2014.07.014
- OPERA DSWx: https://www.jpl.nasa.gov/go/opera
- RCM (CSA): https://donnees-data.asc-csa.gc.ca/en/dataset/rcm
- Our method and numbers: [07-Plan-algorithm.md](07-Plan-algorithm.md), [10-Results.md](10-Results.md), code `pipeline/unseen/` (MIT).
