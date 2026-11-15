# 10 · Results

Every number we show (site, deck, submission) gets one audit line here: **what, value, script, input, date, who**.
Re-run the script to reproduce. Newest at the bottom of each section.

## Peace–Athabasca Delta, Canada

| What | Value | Script | Input | Date (who) |
|---|---|---|---|---|
| RADARSAT-1 scenes over the box | 619 scenes, 1996–2013; 359 cover ≥ 90% of the box; full-cover scenes in Jan and Apr–Dec (most Jun–Nov); most scenes 2010–12 (149 / 135 / 142) | `scripts/rs1_coverage.py` | EODMS STAC `Radarsat-1-L1-COG`, bbox [-112.0, 58.3, -110.8, 59.0] | 14.11.26 (Roy) |

## Mekong delta, Vietnam: flood history 1998–2026

Box [105.0, 10.4, 105.6, 11.0] (Dong Thap / An Giang). Script `python -m unseen.history` (`pipeline/unseen/history.py`).
Input: RADARSAT-1 L1 COGs (EODMS STAC `Radarsat-1-L1-COG`, ≥ 90 % cover), NISAR GCOV track 83 frame 7 ascending, GFM (EODC STAC) ± 3 d.
Flood = water beyond permanent water (dark on ≥ 90 % of NISAR passes). Area = pixels × 80 m × 80 m.

| What | Value | Date (who) |
|---|---|---|
| Images | 17 RADARSAT-1 (1998, 2001, 2005, 2006 Mar–Dec, 2007) + 11 NISAR (19 Jun – 29 Oct 2026) | 14.11.26 (Noa) |
| RADARSAT-1 flood, wet season | 2001-08-30: 2,830 km² · 2005-10-27: 2,592 · 2006-10-22: 2,680 | 14.11.26 (Noa) |
| RADARSAT-1 flood, dry season | 2006-03-13: 115 km² · 2006-06-17: 110 · 1998-01-10: 232 · 2007-05-04: 182 | 14.11.26 (Noa) |
| NISAR flood, 2026 peak | 2026-09-23: 1,854 km² (matches the 2026 Mekong site's "Flooded at peak") | 14.11.26 (Noa) |
| NISAR vs GFM, same day 2026-09-23 | NISAR 1,854 · GFM 706 · both 550 · only NISAR 1,304 (170 of it in GFM's "cannot see") · only GFM 156 km² | 14.11.26 (Noa) |
| RADARSAT-1 threshold per image | 31.4–37.1 dB (DN), Otsu on 22–24 river/land tiles; alignment shift to NISAR 0–1 px, except 1998-07-29 (−34, −15) and 2001-11-07 (+42, −4) px | 14.11.26 (Noa) |

| ~~`events/mekong-delta-history/` bundle~~ (replaced by `events/mekong-delta-vietnam/history/`, 15.11) | headline: flood 2001-08-30 2,830 km² (RADARSAT-1) · 2026-09-23 1,854 km² (NISAR) · GFM same day 706 km²; layers `rs1_water` (17 dates), `agreement` (11 NISAR dates), `rs1_rgb` (4 key dates, 160 m); 3.1 MB. GFM read back from `events/mekong-delta-vietnam` (EODC STAC down, HTTP 502): same numbers as the direct fetch | 15.11.26 (Noa) |

Caveats: C-band (RADARSAT-1) and L-band (NISAR) see flooded rice differently, and the methods differ (one threshold per
image vs our calibrated detector), so compare the pattern (dry ≈ 100–350 km², wet ≈ 1,500–2,800 km²), not exact km².
1998 and 2007 have dry-season images only.

## Mekong delta, Vietnam: flood Sep 2026 (event folder v2)

`python -m unseen.eventfolder mekong-delta-vietnam` → `events/mekong-delta-vietnam/2026-09-flood/`. Window 2026-08-24 → 2026-10-23.
NISAR track 83 frame 7, detect.py v2 (HH −13 / HV −18 dB). Baselines: GFM (± 2 d; read from the v1 bundle, GFM server down 15.11),
DSWx-HLS (± 3 d). Permanent water removed. Date (who): 15.11.26 (Noa).

| Pass | GFM flood | NISAR adds (GFM blank) | vs GFM | DSWx flood (date) | NISAR adds (clouds) | vs DSWx |
|---|---|---|---|---|---|---|
| 2026-08-30 | 1,081 | 129 | +12% | 55 (2026-09-01) | 1,067 | +1,927% |
| 2026-09-11 | 585 | 167 | +29% | – | – | – |
| **2026-09-23** | **706** | **170** | **+24%** | 278 (2026-09-21) | 1,618 | +581% |
| 2026-10-05 | 429 | 161 | +38% | 725 (2026-10-05) | 370 | +51% |
| 2026-10-17 | 345 | 142 | +41% | 1,031 (2026-10-16) | 811 | +79% |

km². GFM "cannot see" on 2026-09-23: 1,050 km² (all vegetation / city). DSWx % are large because clouds hid most of the box.

## Mekong delta, Vietnam: history folder v2

`python -m unseen.historyfolder mekong-delta-vietnam` → `events/mekong-delta-vietnam/history/`. 17 of 28 images kept
(each year's wettest, then ≥ 30 days apart). Same grid, detectors and flood definition as above. Date (who): 15.11.26 (Noa).

| Year | Images | Most flood (date, sensor) | Optical | Official maps |
|---|---|---|---|---|
| 1998 | 2 | 232 km² (01-10, RADARSAT-1), dry season only | none (before MODIS) | none |
| 2001 | 2 | 2,830 km² (08-30, RADARSAT-1) | MODIS | none |
| 2005 | 2 | 2,592 km² (10-27, RADARSAT-1) | MODIS | none |
| 2006 | 6 | 2,680 km² (10-22, RADARSAT-1); dry 110–343 km² | MODIS | none |
| 2007 | 1 | 182 km² (05-04, RADARSAT-1), dry season only | MODIS | none |
| 2026 | 4 | 1,854 km² (09-23, NISAR) | HLS | GFM 706 km², DSWx-HLS 278 km² (09-21; 3,894 km² under cloud) |

## Detector v2 (`detect.py`): F1 vs optical, tuned per site

Leave-one-out: each clear OPERA DSWx-HLS day is scored with HH/HV thresholds tuned on the other days (`detect.calibrate`).
Read from each bundle's `method.calibration.loo` in `events/*/event.json`. Date (who): 15.11.26 (Noa).

| What | Value |
|---|---|
| Mean F1, all passes | **0.70** (74 passes, 10 sites) |
| Mean F1 per site | Likouala 0.91 · Amazon várzea 0.86 · Sylhet 0.72 · Thailand 0.70 · Congo 0.68 · China 0.64 · Tonle Sap 0.64 · Assam 0.63 · Irrawaddy 0.63 · Mekong 0.63 |
| Tonle Sap, all 9 days fitted (no leave-out) | 0.78 (default thresholds −17 / −24 dB: 0.43) |

Not the same test as Inner Niger. There (flood season, both tracks, same truth) v2's tuned fixed thresholds score
F1 **0.22–0.33** vs 0.64–0.75 for a per-scene threshold (prep repo docs/34, option 2d; Noa, 14.11.26): dry Sahel soil is as
dark as water at L-band. The Science page's F1 chart uses 0.22–0.33 so all its rows share one test. The earlier 0.01
(docs/07 §2b) was v2 broken by a corrupt pass, not the detector itself.

## Peace–Athabasca Delta, Canada: flood Jun 2026 + history (event folder v2, RCM check)

`python -m unseen.eventfolder peace-athabasca-delta` and `python -m unseen.historyfolder peace-athabasca-delta` →
`events/peace-athabasca-delta/`. Box [-111.8, 58.3, -111.0, 58.9], NISAR track 143 frame 59 descending, detect.py v2
(HH −12 / HV −18 dB). Window 2026-05-25 → 2026-07-24. GFM server 502 → DSWx-HLS only. Date (who): 15.11.26 (Noa).

| Pass | DSWx flood (date) | DSWx cannot see (clouds) | NISAR adds | NISAR water | RCM day | Agreement / IoU / F1 |
|---|---|---|---|---|---|---|
| **2026-06-24** | 974 (06-24) | 10 | 3 | 440 | none ± 3 d | – |
| 2026-07-06 | 835 (07-07) | 292 | 9 | 311 | 07-03 (79 % of box) | 88.9 % / 0.58 / 0.74 |
| 2026-07-18 | 12 (07-18) | 2,578 | 371 | 373 | 07-18 (41 %) | 90.1 % / 0.63 / 0.77 |

km². RCM = open water (RL band, Otsu per image) vs NISAR open water incl. permanent water. DSWx counts more "flood" than
NISAR on clear days: wind-roughened shallow lakes are not dark on ≥ 90 % of NISAR passes, so they are not "permanent".

History: RADARSAT-1 May–Sep scenes ≥ 90 % cover (1 unreadable: EODMS host blocked), 68 dropped by the Youden check
(J < 0.5, checked by eye against MODIS: 2011-07-08, 2011-09-02, 2012-08-12, 2012-09-12 were false floods over dry land).
Kept 26: per-year maxima 1997 253, 1998 180, 1999 146, 2002 68, 2003 178, 2004 106, 2006 344, 2010 263, 2011 581,
2012 595 km² (RADARSAT-1); 2026 440 km² (NISAR, 06-24).

Agreement of open water (incl. permanent), same 80 m grid, where both see. Date (who): 15.11.26 (Noa).

| Pass | NISAR vs RCM (RCM day) | NISAR vs NASA DSWx (DSWx day, compared) | RCM vs DSWx (no NISAR) |
|---|---|---|---|
| 2026-06-24 | – | 81.2 %, IoU 0.61 (06-24, 99 %) | – |
| 2026-07-06 | 88.9 %, IoU 0.58 (07-03) | 79.7 %, IoU 0.57 (07-07, 90 %) | 73.8 %, IoU 0.43 |
| 2026-07-18 | 90.1 %, IoU 0.63 (07-18) | – (clouds) | – |
| **mean** | **89.5 %, IoU 0.60** | **80.5 %, IoU 0.59** | 73.8 %, IoU 0.43 |

Agreement % counts dry land too (most of the box); IoU is the water-only score.

## GERD reservoir, Blue Nile: Sentinel-1 years (replaces the 1998 RADARSAT-1 picture)

Script `python -m unseen.s1history gerd-blue-nile-ethiopia` (15.11.26). Input: Sentinel-1 RTC (Planetary Computer), descending
relative orbit 50, the pass nearest 1 Oct each year, on the NISAR 80 m grid. Water = VV < -13.2 dB and VH < -18.9 dB
(Otsu on 2025-09-29, same for all years). Flood = water beyond the lake NISAR sees on ≥ 90 % of 2026 passes. Box 12,866 km².

| Date | Open water (lake + river) | Flood beyond the 2026 lake |
|---|---|---|
| 2016-09-28 | 31 km² | 5 km² |
| 2017-10-05 | 50 km² | 5 km² |
| 2018-10-12 | 38 km² | 5 km² |
| 2019-09-25 | 51 km² | 6 km² |
| 2020-10-01 | 214 km² | 6 km² |
| 2021-09-26 | 373 km² | 6 km² |
| 2022-10-03 | 725 km² | 12 km² |
| 2023-09-28 | 1,113 km² | 71 km² |
| 2024-10-04 (95 % covered) | 1,398 km² | 370 km² |
| 2025-09-29 | 1,518 km² | 468 km² |

## Explorer list clean-up (15.11.26, Noa)

- Hidden (`"hidden": true` in event.json, kept on disk; `bundle.write_index()` skips them): Tamil Nadu floods,
  Atchafalaya Basin, Okavango Delta.
- Nepal floods: box cut from [84.865, 26.895, 85.865, 27.695] to the flooded plain [85.22, 26.90, 85.44, 27.11]
  (`scripts/crop_bundle.py`, same pixels). 26 Jul 2026: GFM flood 7.4 → 4.6 km² (62 % of it inside), NISAR adds
  1.2 → 0.8 km² (68 %), in 1/18 of the area. Other dates had no maps, so their km² were dropped.

## What is in the official map's "cannot see" area

`python scripts/gfm_blank_landcover.py` → `events/world/gfm_blank.json`. GFM exclusion layer of each site's compared pass
(from its bundle) overlaid on ESA WorldCover 2021 (~80 m overview), pixels weighted by cos(lat). Date (who): 15.11.26 (Noa).

| What | Value |
|---|---|
| GFM "cannot see", 17 sites | 31,662 km²: forest (tree + mangrove) 66% · herbaceous wetland 12.5% · cropland 11% · shrub & grass 7% · built-up 2% · water 1% |
| Clouds in GFM's blank | 0% (GFM is Sentinel-1 radar) |
| Most forest | Likouala 98% · Amazon várzea 95% · Atchafalaya 93% · Congo 90% · Hubei 86% · Tonle Sap 66% |
| Not forest | Sudd 96% wetland · Okavango 66% wetland · Pantanal 62% wetland · Inner Niger 53% shrub & grass + 18% bare/sand · Bang Pakong 32% built-up |
| Mekong, 21–23 Sep 2026, box 4,366 km² | GFM cannot see 1,050 km² (vegetation / city, 0% cloud) · OPERA DSWx-HLS cannot see 3,894 km² (cloud) — from `events/mekong-delta-vietnam/2026-09-flood/event.json` |

### Mekong, both official maps' blanks split (event folder v2)

`python scripts/blank_breakdown.py mekong-delta-vietnam/2026-09-flood` → `events/mekong-delta-vietnam/2026-09-flood/blanks.json`.
Blanks from the folder's `gfm_classes` / `dswx_classes` layers; land cover ESA WorldCover 2021 (~40 m overview). km² below are
the bundle's stored values (both blind: overlay km², except 23 Sep scaled to the stored blank); shares from the overlay (its own pixel areas run ~0.7% higher). Date (who): 15.11.26 (Noa).

| Pass (GFM / DSWx date) | GFM blank km² (cause: vegetation, city, radar shadow; cloud 0%) | DSWx-HLS blank km² (cause: cloud / shadow) | Both blind |
|---|---|---|---|
| 30 Aug (30 Aug / 1 Sep) | 1,060: forest 39% · cropland 37% · built-up 13% | 2,990: cropland 72% · forest 16% | 858 km² (80% of GFM blank) |
| **23 Sep (23 Sep / 21 Sep)** | **1,050: forest 40% · cropland 37% · built-up 13% · water 5%** | **3,894: cropland 74% · forest 14% · water 5%** | **≈ 1,001 km² (95%)** |
| 5 Oct (5 Oct / 5 Oct) | 1,052 | 1,344: cropland 69% · forest 18% | 404 km² (38%) |
| 17 Oct (17 Oct / 16 Oct) | 1,052 | 2,676: cropland 73% · forest 15% | 716 km² (68%) |

Explorer layer `both_blind` (magenta, step "Both blind" on the Mekong site): the same GFM blank ∩ DSWx-HLS cloud per pass,
written by `python scripts/blank_breakdown.py mekong-delta-vietnam/2026-09-flood --layer mekong-delta-vietnam`
into `events/mekong-delta-vietnam/layers/both_blind_<date>.png` (4 passes). 15.11.26 (Noa).


## Over-the-years folders: Tonle Sap, Sylhet (Nepal not possible) — 15.11.26 (Noa)

`python -m unseen.historyfolder <place>`; same method as Mekong / Peace–Athabasca (RADARSAT-1 ≥ 90 % cover, Otsu per
image, Youden J ≥ 0.5 quality check). Each RADARSAT-1 flood map checked by eye against MODIS.

| Place | Images kept | RADARSAT-1 | Most flood, then → now | Notes |
|---|---|---|---|---|
| Tonle Sap, Cambodia | 13 | 9 (1998–2006), 0 dropped | 1,716 km² (2001-08-30) → 4,060 km² (NISAR 2026-10-17) | flood pulse: dry 300–700, wet 1,000–1,700 km² |
| Sylhet haor, Bangladesh | 9 | 4 (1996–2002), 3 dropped (J < 0.5) | 931 km² (2002-07-01) → 920 km² (NISAR 2026-07-24) | monsoon haor edges; no MODIS before 2000, cloud after |
| Nepal (small box) | – | 10 found, all unusable | – | box holds only a thin river: no tile with both permanent water and land, so no threshold |

## Improvement %: pooled over passes (15.11.26, Noa)

% = 100 × Σ NISAR addition ÷ Σ official flood over every pass with a baseline (`bundle.pooled`). Was: the wettest pass only.

| Flood | Passes | Σ official | Σ NISAR adds | Pooled % | Was (one pass) |
|---|---|---|---|---|---|
| Inner Niger Delta | 10 | 569 | 2,083 | **366 %** | 493 % |
| Tonle Sap | 11 | 3,719 | 2,387 | **64 %** | 98 % |
| Mekong (v2) | 5 | 3,146 | 769 | **24 %** | 24 % |
| Peace–Athabasca (v2, DSWx) | 3 | 1,822 | 383 | **21 %** | 0 % |
| Irrawaddy | 11 | 2,543 | 471 | **19 %** | – |
| Sylhet | 11 | 908 | 72 | **8 %** | – |

km² summed over passes (km² × passes, not one area). Each pass's own numbers: `events/<id>/event.json` timeline / passes.

## Data inventory per event (15.11.26, Noa)

Counted from each `event.json` (`passes[]`). Flood folders: flood date ± 30 days, one row per NISAR pass set.
Every NISAR pass has HH, HV, the RGB picture and our water map. **⚠** = only one official flood-map source
(GFM or NASA DSWx, not both). **⛔** = one source on one pass only. *numbers only* = no pictures committed (Explorer card only).

| Place (flood) | NISAR passes | Optical photo (source) | GFM | NASA DSWx | NISAR coherence | NISAR valid | Checks | Pooled % |
|---|---|---|---|---|---|---|---|---|
| Amazon várzea (Jun) **⚠** | 3 | 3 (MODIS) | 0 | 3 | 0 | 100 % | – | 18 % |
| Assam (Sep) **⚠** | 5 | 5 (VIIRS) | 0 | 4 | 4 | 100 % | – | 370 % |
| Congo Cuvette (Oct), *numbers only* | 3 | 2 (HLS) | 3 | 3 | 2 | 100 % | – | – (flood < 5 km²) |
| Dead Sea (Oct) **⚠** | 5 | 5 (VIIRS) | 0 | 5 | 3 | 100 % | DSWx, LANCE | 7 % |
| Hubei, China (Oct) **⚠** | 3 | 3 (VIIRS) | 0 | 2 | 2 | 90 % | DSWx | 14 % |
| Nepal (Jul, small box) | 4 | 4 (VIIRS) | 1 | 4 | 4 | 100 % | – | – (flood < 5 km²) |
| Tamil Nadu (Oct, hidden), *numbers only* **⚠** | 3 | 0 | 0 | 3 | 1 | 93 % | DSWx | 9 % |
| GERD (Nov) **⚠** | 3 | **3 (HLS, added)** | 0 | 3 | 2 | 100 % | – | 7 % |
| Inner Niger (Jul), *numbers only* | 4 | 4 (HLS) | 4 | 4 | 2 | 100 % | – | 664 % |
| Likouala (Oct) **⚠** | 3 | 3 (VIIRS) | 0 | 3 | 0 | 100 % | – | 277 % |
| Mekong (Sep) | 5 | 5 (HLS) | 5 | 4 | 3 | 100 % | – | 24 % |
| Pantanal (Oct) | 4 | 4 (VIIRS) | 1 | 4 | 0 | 100 % | – | – (flood < 5 km²) |
| Peace–Athabasca (Jun) **⚠** | 3 | 3 (HLS) | 0 | 3 | 1 | 100 % | RCM, DSWx | 21 % |
| Sylhet (Jul) **⚠** | 4 | 4 (VIIRS) | 0 | 4 | 0 | 97 % | – | 316 % |
| Sylhet, validation (Oct) | 6 | 6 (VIIRS) | 5 | 5 | 0 | 97 % | GFM, DSWx, LANCE | 25 % |
| Bang Pakong, Thailand (Oct, hidden 15.11) **⛔** | 3 | 3 (VIIRS) | 1 | 0 | 0 | 93 % | – | 17 % (1 pass) |
| Tonle Sap (Oct), *numbers only* | 4 | 3 (HLS) | 4 | 3 | 2 | 100 % | – | 88 % |

Over the years (`history/`): Peace–Athabasca 26 images (22 RADARSAT-1 + 4 NISAR, 1997–2026), Mekong 17 (13 + 4),
GERD 14 (10 Sentinel-1 + 4 NISAR, 2016–2026), Tonle Sap 13 (9 + 4), Assam 9 (6 + 3), Sylhet 9 (4 + 5), Amazon 5 (2 + 3).
Optical there: MODIS 2000–2013, HLS 2026, none before 2000.

Missing photos filled with `scripts/fill_photos.py` (NASA GIBS true colour ± 5 d: HLS Sentinel-2 / Landsat, then VIIRS,
then MODIS; least cloud, ≥ 70 % of the box): GERD 5 Oct and 20 Oct (HLS Sentinel-2) and 31 Oct (HLS Landsat), cloud 0–3 %.
Numbers-only folders (Congo, Tamil Nadu, Inner Niger, Tonle Sap) have no pictures, so no photo was added there.
