# pipeline — flood bundles for the site (Python package `unseen`)

Offline. Turns NISAR radar for a flood site into a bundle in `events/<id>/` (PNG layers + `event.json`, contract in
[docs/08](../docs/08-Plan-data.md) §3). The site only reads the committed bundles; nobody needs to run this to use it.

```bash
pip install -e pipeline              # needs EARTHDATA_TOKEN in .env (see .env.example) or ~/.netrc
unseen auth-check
unseen build                         # all sites in pipeline/sites.json, then events/world + events/index.json
unseen build --only tonle-sap-flood-pulse-2026
unseen site --id my-flood --title "My flood" --bbox lon0,lat0,lon1,lat1 [--kind story] [--passes all|best] [--detector v3|v2]
UNSEEN_EVENTS_DIR=/tmp/ev unseen site ...   # write bundles somewhere else (test without touching events/)
```

Method per NISAR pass (default **v3**, `fused.py`, [docs/07](../docs/07-Plan-algorithm.md) §2b): corrupt passes dropped (scene
median > 3 dB off), then water = logistic score of the per-scene threshold (Martinis et al. 2015), change from the dry
season (first two passes, or `dry_dates` in `sites.json`), HV and 12-day GUNW coherence; water under vegetation from
`detect.py`. `--detector v2` = the old `detect.py` (thresholds calibrated on clear optical days). The gap = NISAR water inside Copernicus GFM's exclusion mask ("cannot see"), both valid,
permanent water removed; area = pixels × 80 m × 80 m.

| Module | Does |
|---|---|
| `flood.py` | stack → water → per-pass gap vs GFM (km², masks) |
| `bundle.py` | masks → `events/<id>/layers/*.png` (EPSG:4326) + `event.json`; `events/index.json` |
| `cli.py` | the `unseen` command; `sites.json` = the 16 sites |
| `nisar.py`, `gcov.py`, `remote.py`, `auth.py` | ASF search, NISAR GCOV windowed reads over HTTP, Earthdata login |
| `fused.py` | **default detector v3**: QA, per-scene threshold, dry-season change, HV, GUNW coherence → water |
| `detect.py`, `flood_nasa.py` | old detector v2 (also gives water under vegetation); NISAR handbook §6.4 classifier (second opinion) |
| `gfm.py`, `optical.py`, `rcm.py` | Copernicus GFM, OPERA DSWx-HLS, Canada's RCM on our grid |
| `eventfolder.py` | one flood in event-folder format v2 (docs/12): `events/<place>/<YYYY-MM>-flood/` + `place.json` (`python -m unseen.eventfolder <place>`) |
| `historyfolder.py` | over the years in event-folder format v2 (docs/12 §10): `events/<place>/history/` (`python -m unseen.historyfolder <place>`) |
| `history.py` | flood history of one place: RADARSAT-1 (1996–2013) + NISAR on one grid, flood per image, vs GFM → Explorer case `site/viewer/sites/<id>/` (`python -m unseen.history`) |
| `landcover.py`, `population.py` | ESA WorldCover, WorldPop on our grid (context) |

Caches go to `data/` (git-ignored).
