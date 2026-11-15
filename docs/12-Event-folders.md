# 12 · Event folders: one place, its floods, its history (contract v2, draft)

**Noa, 15.11.26 10:58:53 says:** proposed format for `events/`. One folder per place; inside it, one folder per recent
flood (with NISAR data) and, if we have it, one `history/` folder (over the years, details later).
v1 ([08 §3](08-Plan-data.md)) stays valid until the pipeline and site move over (§8).

## 1. Folders

```
events/
  index.json                         # every place and its floods, for the site's list (§6)
  schema.json                        # JSON Schema of event.json (v2)
  <place>/                           # e.g. mekong-delta-vietnam
    place.json                       # name, country, bbox, list of its flood folders + history (§6)
    <flood>/                         # e.g. 2026-09-flood: one flood event with NISAR data
      event.json                     # the metadata: results + display hints (§4)
      science.md                     # short method + limits, for the science drawer
      layers/<layer>_<YYYY-MM-DD>.png|jpg  # one picture per layer per date (§3), EPSG:4326, ≤ 2048 px
    history/                         # over the years: RADARSAT-1 + NISAR, one image every month or two (§10)
```

- `<place>`: lower-case words with `-`. `<flood>`: `YYYY-MM-flood` (month of the flood peak); a second flood
  in the same month gets `-2`.
- All layers of one flood share **one grid** (NISAR's, 80 m) and one `bounds`, so they stack exactly on the map.

## 2. The event window and its dates

- **Flood date** `D`: the peak (wettest NISAR pass), or the alert start (GDACS) when there is one.
- **Event window**: `D − 30 days` to `D + 30 days`. Only data inside the window goes in the folder.
- **Time steps = NISAR passes** in the window (every 12 days: about 5 passes). Every other source is matched to
  each pass, nearest in time, and the folder keeps both dates:

| Source | Matched to each NISAR pass | If nothing that close |
|---|---|---|
| Optical photo (HLS true colour) | clearest image within ± 5 days | no photo for that pass |
| GFM (Copernicus, Sentinel-1) | nearest within ± 2 days | baseline missing for that pass |
| NASA OPERA DSWx-HLS (optical) | nearest within ± 3 days, ≥ 30 % of the box | baseline missing for that pass |
| GUNW coherence | mean of the 12-day pairs that include the pass | no coherence layer |

## 3. Layers (one PNG per date unless marked "once")

File name: `layers/<layer>_<YYYY-MM-DD>.<ext>`, date = **the source's own date** (the pass it belongs to is in `event.json`).
Opaque pictures (photo, radar) are **JPEG** (`.jpg`, black = no data); masks and class maps are **PNG** with transparency.
Layers marked `"once": true` have one file for the whole window.

| Group | Layer | What | Picture |
|---|---|---|---|
| optical | `photo` | HLS true colour, clearest near each pass | RGB |
| radar | `nisar_hh` | NISAR GCOV HH | grey, fixed stretch −25…0 dB |
| radar | `nisar_hv` | NISAR GCOV HV | grey, fixed stretch −32…−8 dB |
| radar | `nisar_rgb` | R = HH, G = HV, B = HH/HV | RGB |
| radar | `nisar_coh` | GUNW 12-day coherence (pair ending at the pass) | grey 0…1 |
| radar | `nisar_mask` (once) | where NISAR can't measure: layover, shadow, no data | grey |
| baseline | `gfm_classes` | GFM, segmented (§3a) | class colours |
| baseline | `dswx_classes` | NASA OPERA DSWx, segmented (§3a) | class colours |
| result | `nisar_water` | water NISAR finds (our detector), permanent water removed | blue |
| result | `nisar_adds` | **NISAR addition**: NISAR water inside the baseline's "cannot see" | orange `#ff9a2e` |
| result | `combined` | baseline flood + NISAR addition + still unknown (§3a) | class colours |
| context (once) | `landcover` (`hand` later) | ESA WorldCover; height above nearest drainage (flood plausibility) | class colours / grey |

**Also needed from NISAR (beyond HH, HV, coherence):** a **dry reference** (median of the passes before the
window, for "change from normal"), the **layover/shadow mask** (GCOV has it), and **incidence angle** (in GCOV)
for the methods text. They feed the numbers; only `nisar_mask` needs to be a picture.

### 3a. Segmented maps: one picture, fixed colours

Each `*_classes` and `combined` picture is **one segmented map** of the flood box. Every class has one exact colour,
so the site can show it as is **and** code can count pixels by colour.

| Class | Colour | `gfm_classes` / `dswx_classes` | `combined` |
|---|---|---|---|
| flood | `#2882ff` | baseline says flooded | baseline flood |
| permanent water | `#0a3a8c` | reference / ocean water (not flood) | same |
| dry | transparent | baseline says not flooded | dry in both |
| cannot see: clouds | `#ebebf0` | DSWx-HLS cloud / shadow / snow | – |
| cannot see: vegetation, city, radar shadow | `#8c8c96` | GFM exclusion mask | – |
| NISAR addition | `#ff9a2e` | – | NISAR water in the baseline's blank |
| still unknown | `#3c3c46` | – | blank in baseline and NISAR can't tell (its mask or low confidence) |

Solid colours, not hatching: hatched PNGs are ~3× bigger. The site may draw a hatch on top of the grey.
| no data | transparent + not counted | outside the scene | – |

## 4. `event.json` (metadata, read by the site)

Short example (numbers are made up; keys are the contract):

```json
{
  "version": 2,
  "id": "mekong-delta-vietnam/2026-09-flood",
  "place": "Mekong delta, Vietnam",
  "title": "Mekong delta flood, Sep 2026",
  "flood_date": "2026-09-23",
  "window": {"start": "2026-08-24", "end": "2026-10-23", "days_before": 30, "days_after": 30},
  "bbox": [105.0, 10.4, 105.6, 11.0],
  "area_km2": 4400,
  "baselines": ["gfm", "dswx"],
  "summary": {
    "pass_date": "2026-09-23",
    "baseline": "gfm", "baseline_date": "2026-09-23",
    "baseline_flood_km2": 706,
    "nisar_adds_km2": 170,
    "improvement_pct": 24,
    "cannot_see_km2": 1062, "cannot_see_clouds_km2": 0, "cannot_see_vegetation_km2": 1062,
    "still_unknown_km2": 210,
    "sentence": "NISAR adds 170 km² of flood (+24%) where the official map (GFM) cannot see."
  },
  "passes": [
    {
      "date": "2026-09-23",
      "matched": {"photo": "2026-09-21", "gfm": "2026-09-23", "dswx": "2026-09-24", "coh_pair": ["2026-09-11", "2026-09-23"]},
      "clouds_pct": 64,
      "baselines": {
        "gfm":  {"flood_km2": 706, "cannot_see_km2": 1062, "cannot_see_clouds_km2": 0,   "cannot_see_vegetation_km2": 1062,
                 "nisar_adds_km2": 170, "improvement_pct": 24, "still_unknown_km2": 210},
        "dswx": {"flood_km2": 512, "cannot_see_km2": 2830, "cannot_see_clouds_km2": 2830, "cannot_see_vegetation_km2": 0,
                 "nisar_adds_km2": 980, "improvement_pct": 191, "still_unknown_km2": 120}
      },
      "nisar": {"water_km2": 1854, "valid_pct": 99},
      "layers": ["photo", "nisar_rgb", "nisar_hh", "nisar_hv", "nisar_coh", "gfm_classes", "dswx_classes",
                 "nisar_water", "nisar_adds", "combined"]
    }
  ],
  "layers": {
    "gfm_classes": {"group": "baseline", "label": "Official flood map (GFM)", "sensor": "Sentinel-1 (Copernicus GFM)",
                    "legend": [["#2882ff", "flood"], ["#0a3a8c", "permanent water"], ["#8c8c96", "cannot see here"]],
                    "files": {"2026-09-23": "layers/gfm_classes_2026-09-23.png"},
                    "bounds": [[10.399, 105.0], [11.001, 105.601]], "default": true}
  },
  "method": {"detector": "fused v3", "pixel_m": 80, "permanent_water": "water on ≥ 90 % of passes"},
  "sources": [{"name": "NISAR L2 GCOV", "url": "https://search.asf.alaska.edu", "credit": "NASA/JPL-Caltech, ISRO; ASF DAAC"}]
}
```

### What each number means

All areas are pixels × 80 m × 80 m, counted only where both NISAR and the baseline have data, permanent water removed.

| Key | Meaning |
|---|---|
| `flood_km2` | flood in the baseline map (GFM or NASA DSWx) on the matched date |
| `cannot_see_km2` | area the baseline marks as "can't tell": `_clouds` (optical) + `_vegetation` (forest, city, radar shadow) |
| `nisar_adds_km2` | NISAR water inside `cannot_see` (the NISAR addition) |
| `improvement_pct` | `100 × nisar_adds_km2 / flood_km2` (how much bigger the flood map gets); `null` if `flood_km2 < 5` |
| `still_unknown_km2` | `cannot_see` where NISAR can't tell either (its mask, low confidence) |
| `clouds_pct` | cloud cover of the photo's scene in the box |
| `summary` | the wettest pass, against the main baseline (GFM if present, else DSWx): the numbers the site shows first |

## 5. How the site shows it

- **Headline card**: `summary.sentence` + three numbers: `baseline_flood_km2`, `nisar_adds_km2`, `improvement_pct`.
- **Date slider** = `passes[]`. Each step shows that pass's layers; the matched dates are written under the slider
  ("photo 21 Sep, GFM 23 Sep"), so nobody thinks they are the same day.
- **Layer list** = `layers{}` in group order (optical, radar, baseline, result, context); `default: true` ones on.
- **Legend** = the layer's `legend` pairs ([colour or "hatch", text]).
- **Chart** under the map: per pass, baseline flood (blue) + NISAR addition (orange) + still unknown (grey).
- No number is typed in HTML: everything comes from `event.json`.

## 6. `place.json` and `index.json`

```json
{"id": "mekong-delta-vietnam", "name": "Mekong delta", "country": "Vietnam", "bbox": [105.0, 10.4, 105.6, 11.0],
 "floods": [{"id": "2026-09-flood", "flood_date": "2026-09-23", "improvement_pct": 24, "nisar_adds_km2": 170}],
 "history": null}
```

`events/index.json`: `{"version": 2, "events": [ v1 list, unchanged ], "places": [ {id, folder, name, country, bbox, floods, history} ] }`
(`bundle.write_index()` writes both, so v1 and v2 live side by side).

## 7. Size

5 passes × ~10 layers × ~150 KB ≈ 7.5 MB per flood: too much for the 20 MB budget with many places.
Keep `nisar_hh` / `nisar_hv` at half resolution, and store only `nisar_rgb` if we must cut. Run `scripts/check_bundle.py`.

## 8. Moving from v1, and drawbacks

- v1 bundles are flat (`events/<id>/`). The site (`site/viewer/js/inmap.js` finds bundles by id), `bundle.py`,
  `cli.py` and `scripts/check_bundle.py` need updating together; until then both layouts can live side by side.
- **Drawbacks:** one fixed ±30-day window can cut a long flood (Mekong floods Aug–Dec); colour-coded classes break
  if a PNG is resized with smoothing (use nearest only); "still unknown" depends on our confidence threshold;
  GFM and DSWx disagree on what "cannot see" means, so their improvement % are not comparable to each other.

## 9. Built so far

**Noa, 15.11.26 11:55:13 says:** first folder: `events/mekong-delta-vietnam/2026-09-flood/` (`python -m unseen.eventfolder
mekong-delta-vietnam`). Flood date 23 Sep 2026, window 24 Aug → 23 Oct, 5 passes. GFM on all 5 (read from the v1 bundle:
the GFM server was down); DSWx-HLS on 4; coherence on 3 (no GUNW pairs for 11 and 23 Sep); 4.6 MB. The Explorer card
(Roy) already reads its `summary`. `hand` and "low confidence" for still-unknown are not built yet.

## 10. `history/`: the place over the years

**Noa, 15.11.26 12:24:31 says:** format of the over-the-years folder, first one built: `events/mekong-delta-vietnam/history/`
(`python -m unseen.historyfolder mekong-delta-vietnam`).

- **Images:** every RADARSAT-1 (CSA, 1996–2013) scene covering ≥ 90 % of the box, plus the NISAR passes. Kept: each year's
  wettest image, then others ≥ 30 days from the kept ones (about one every month or two).
- **Per image:** the radar picture, **our flood map from that radar** (RADARSAT-1 or NISAR), an optical photo near the
  same day, and the official flood maps **where they exist**, each with km².

| Layer | What | Dates |
|---|---|---|
| `rs1_radar` | RADARSAT-1 HH picture (160 m picture; analysis at 80 m) | RADARSAT-1 dates |
| `rs1_flood` | flood from RADARSAT-1 (our analysis) | RADARSAT-1 dates |
| `nisar_rgb`, `nisar_water` | NISAR picture, flood from NISAR (our analysis) | NISAR dates |
| `photo_modis` | MODIS Terra/Aqua true colour, least cloudy within ± 3 d (250 m, NASA GIBS) | from 2000 |
| `photo` | HLS true colour, clearest within ± 5 d | 2026 |
| `gfm_classes`, `dswx_classes`, `nisar_adds` | official maps segmented (§3a) + NISAR addition | GFM from 2015, DSWx-HLS from 2023 |

`event.json` (`"kind": "history"`): `images[]` with, per image, `date`, `sensor`, `flood_km2` (our analysis), `optical`
(`date`, `source`, `cloud_pct` = bright cloud only, not haze), `baselines` (as in §4: `flood_km2`, `cannot_see_km2` …,
`nisar_adds_km2`, `improvement_pct`), `baselines_missing`, `layers`; `summary.years[]` = per year `max_flood_km2`, its date
and sensor, `flood_season_seen` (false = dry-season images only); `sampling`, `method`, `sources`.
`place.json` → `"history": {"id": "history", "first", "last", "n_images", "sensors"}`.

**Noa, 15.11.26 12:38:41 says:** second place: `events/gerd-blue-nile-ethiopia/` (GERD reservoir, Blue Nile).
NISAR track 129 frame 7, 11 dual-pol passes (23 Jun → 2 Nov 2026); thresholds HH −13 / HV −18 dB (Otsu on 2 Nov: −12.4 / −16.9).
Flood folder `2026-11-flood`: peak 2 Nov, 3 passes; "flood" = lake beyond its ≥ 90 % core = how far it grows (399 km² by 2 Nov).
DSWx only (GFM server 502), no photos (no Explorer site). History: RADARSAT-1 has **one** scene here (9 Jul 1998,
ScanSAR, 74 % of the box, dam just outside), so new place keys `rs1_min_cover` (0.7 here, default 0.9) and `rs1_flood`
(False: in 1998 the lake was dry valley, the river/land threshold splits terrain shadows, 1,547 km² of false "flood"):
1998 picture only, plus 4 NISAR images. Size 4 MB; `events/` is now 24.5 MB (over the 20 MB check before this, at 21 MB).
