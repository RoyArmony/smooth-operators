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

Not the same test as the Inner Niger held-out track (docs/07 §2b), where v2 scored 0.01 because a corrupt pass broke its baseline.

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
