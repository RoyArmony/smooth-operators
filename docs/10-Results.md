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

| `events/mekong-delta-history/` bundle | headline: flood 2001-08-30 2,830 km² (RADARSAT-1) · 2026-09-23 1,854 km² (NISAR) · GFM same day 706 km²; layers `rs1_water` (17 dates), `agreement` (11 NISAR dates), `rs1_rgb` (4 key dates, 160 m); 3.1 MB. GFM read back from `events/mekong-delta-vietnam` (EODC STAC down, HTTP 502): same numbers as the direct fetch | 15.11.26 (Noa) |

Caveats: C-band (RADARSAT-1) and L-band (NISAR) see flooded rice differently, and the methods differ (one threshold per
image vs our calibrated detector), so compare the pattern (dry ≈ 100–350 km², wet ≈ 1,500–2,800 km²), not exact km².
1998 and 2007 have dry-season images only.
