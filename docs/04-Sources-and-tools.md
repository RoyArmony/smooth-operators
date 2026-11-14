# 04 · Sources and tools

Everything we use: data, tools, services, AI tools and references.
Feeds the **Data & AI Disclosure** and **References** parts of the submission. Credit lines: [03](03-Citation-and-AI.md).

- One line per item: `- **Name** — what we use it for — link (who, DD.MM.YY)`
- Add an item the first time it's used. Don't add duplicates.
- If we drop something, keep the line and add *(dropped)*.
- Data lines also say **how to get it** (login, API, tool), so anyone (or Claude) can fetch it again.

## Official challenge resources

All 14 links from the [Resources tab](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/?tab=resources). Details: [01 · Part C](01-Competition.md#part-c--official-challenge-resources).

- **NASA Earthdata Search** — find and download NASA Earth data (runs on CMR; Harmony can subset to GeoTIFF); Earthdata Login to download — https://search.earthdata.nasa.gov/search (Roy, 13.11.26)
- **ASF Data Search Vertex** — map search for NISAR, Sentinel-1, ALOS; Earthdata Login to download; Python: `asf_search` — https://search.asf.alaska.edu/ (Roy, 13.11.26)
- **NISAR Data User Guide (ASF)** — products, PROVISIONAL vs VALIDATED, access, citation rules — https://nisar-docs.asf.alaska.edu/ (Roy, 13.11.26)
- **Intro to Remote Sensing (Earthdata)** — basics — https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/remote-sensing (Roy, 13.11.26)
- **Intro to SAR (Earthdata)** — frequency, polarization, scattering; Okmok interferogram (2.8 cm per colour cycle) — https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar (Roy, 13.11.26)
- **NASA ARSET Trainings** — incl. 2026 NISAR courses on surface water and surface displacement (method references) — https://appliedsciences.nasa.gov/get-involved/training (Roy, 13.11.26)
- **NISAR ArcGIS StoryMaps** (Peacock, An, Pinto & Lou 2024, Zenodo, doi:10.5281/zenodo.10818833) — floods, wildfires, oil slicks, glacier motion, subsidence — https://nisar.jpl.nasa.gov/applications/arcgis-storymaps/ (Roy, 13.11.26)
- **NISAR Applications White Papers** — 2-page "why it matters" per change type — https://nisar.jpl.nasa.gov/applications/societal-benefit/ (Roy, 13.11.26)
- **UAVSAR Postcards (NASA/JPL)** — airborne L-band false-colour examples and colour keys — https://uavsar.jpl.nasa.gov/education/postcards.html (Roy, 13.11.26)
- **RADARSAT Constellation Mission (RCM) - Data (CSA)** — C-band, 3 satellites; EODMS (user licence), AWS CEOS-ARD, sample folder — https://donnees-data.asc-csa.gc.ca/en/dataset/rcm (Roy, 13.11.26)
- **CSA SAR Python Tutorial** — beginner notebook (GDAL, cartopy) + QGIS guide, RCM wildfire scene (modified MIT) — https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial (Roy, 13.11.26)
- **RADARSAT-1 - Data (CSA)** — 1995–2013 C-band archive, all open (Open Government Licence – Canada) — https://donnees-data.asc-csa.gc.ca/en/dataset/radarsat1 (Roy, 13.11.26)
- **SAOCOM Catalogue (CONAE)** — L-band SAR; free search + thumbnails; download needs account + licence, Argentina only — https://catalogos.conae.gov.ar/catalogo/catalogoSatSaocomInfo.html (Roy, 13.11.26)
- **SAOCOM Catalogue Registration (CONAE)** — how to request archive access — https://www.argentina.gob.ar/noticias/la-informacion-saocom-cada-vez-mas-accesible (Roy, 13.11.26)

## NASA data

- **NASA Earthdata Login** — one account for ASF (NISAR, Sentinel-1, ALOS), LP DAAC (HLS), PO.DAAC (OPERA, SWOT). Use `~/.netrc` or `.env` (`EARTHDATA_TOKEN`, or `EARTHDATA_USERNAME` + `EARTHDATA_PASSWORD`). HTTP 401/403 → approve the archive under Applications → Authorized Apps — https://urs.earthdata.nasa.gov (Shai, 31.10.26)
- **NISAR L2 GCOV (L-band backscatter, HH/HV)** — the core input. Search: `asf_search` with `dataset="NISAR"`, `processingLevel="GCOV"`, `intersectsWith=<bbox>`. Read only the box over HTTP with `h5py` (512×512 chunks) instead of downloading 0.2–8 GB files. Layout: `science/LSAR/GCOV/grids/frequencyA|B/HHHH`, `HVHV` (linear gamma0); freq B = 80 m. Rules: one track + frame + direction + bandwidth mode (`2005` vs `4005`), ≥ 90 % box coverage, no BETA — https://nisar-docs.asf.alaska.edu (Shai, 31.10.26)
- **NISAR L2 GCOV VALIDATED** (`NISAR_L2_GCOV_V1`, acquisitions from 21 Oct 2026) — newer passes, used next to PROVISIONAL (from 17 Jun 2026) — https://nisar-docs.asf.alaska.edu/availability-overview/ (Shai, 09.11.26)
- **NISAR L2 GUNW** — 12-day unwrapped interferograms + coherence (ground motion, damage proxy, flood evidence); `processingLevel="GUNW"` in `asf_search` — https://search.asf.alaska.edu/#/?dataset=NISAR (Shai, 31.10.26)
- **NISAR L3 SME2** (soil moisture, PROVISIONAL) — inspected over the Dead Sea — https://search.asf.alaska.edu/#/?dataset=NISAR (Roy, 31.10.26)
- **NISAR S-band (ISRO, via Bhoonidhi)** — not at ASF; separate free Bhoonidhi account. API: `POST /auth/token` → `POST /data/search` (STAC) → `GET /download`; `.env`: `BHOONIDHI_USER_ID`, `BHOONIDHI_PASSWORD`. Coverage patchy, still being calibrated — https://bhoonidhi.nrsc.gov.in/bhoonidhi-api/ (Roy, 02.11.26)
- **NASA GIBS: NISAR GCOV map tiles** (`NISAR_L2_Geocoded_Polarimetric_Covariance`) — WMTS web-map layer, no login — https://nasa-gibs.github.io/gibs-api-docs/ (Roy, 31.10.26)
- **NASA GIBS: HLS true-colour tiles** (`HLS_L30_Nadir_BRDF_Adjusted_Reflectance`, `HLS_S30_…`) and **Blue Marble** — optical photo and basemap in the browser, no login — https://nasa-gibs.github.io/gibs-api-docs/ (Shai, 02.11.26)
- **NASA CMR** — catalogue search for HLS / OPERA granules: `https://cmr.earthdata.nasa.gov/search/granules.json?short_name=...&bounding_box=...&temporal=...` — https://cmr.earthdata.nasa.gov (Shai, 31.10.26)
- **OPERA DSWx-HLS** (`OPERA_L3_DSWX-HLS_V1`) — optical water maps (Landsat + Sentinel-2), the optical reference; download `_B01_WTR.tif` from PO.DAAC with Earthdata Login — https://www.jpl.nasa.gov/go/opera (Shai, 31.10.26)
- **OPERA DSWx-S1 / DSWx-NI** — water maps from Sentinel-1 (public) and NISAR (test product, not yet public) — https://www.jpl.nasa.gov/go/opera/products (Shai, 14.11.26)
- **HLS, OPERA RTC-S1, DIST-ALERT, DISP-S1** (`HLSL30`, `HLSS30`, `OPERA_L2_RTC-S1_V1`, `OPERA_L3_DIST-ALERT-*_V1`, `OPERA_L3_DISP-S1_V1`) — checked as comparisons; same login — https://cmr.earthdata.nasa.gov (Shai, 31.10.26)
- **SWOT L2 HR LakeSP (version D)** (NASA / CNES, with CSA and UK Space Agency) — lake water level per pass; Hydrocron API returns CSV with no login — https://podaac.jpl.nasa.gov/SWOT · https://podaac.github.io/hydrocron/ (Roy, 10.11.26)
- **ASF HyP3 on-demand InSAR** — Sentinel-1 12-day coherence for the same dates as NISAR; free with Earthdata Login — https://hyp3-docs.asf.alaska.edu (Noa, 14.11.26)
- **NASA POWER daily API** (MERRA-2 rain, temperature, topsoil wetness; no login) — weather context — https://power.larc.nasa.gov/ (Noa, 14.11.26)
- **NASA OMNI Kp / Dst via CDAWeb HAPI** — geomagnetic storm dates for ionosphere checks — https://cdaweb.gsfc.nasa.gov/hapi (Roy, 11.11.26)

## Partner agency data (CSA, JAXA, ESA, CONAE…)

- **RADARSAT-1 open archive (CSA)** — C-band "radar memory" 1995–2013, no login: Natural Resources Canada EODMS STAC search + AWS COGs. Older scenes may need a GCP / height fix to align — https://eodms-sgdot.nrcan-rncan.gc.ca/search · https://registry.opendata.aws/radarsat-1/ (Roy, 11.11.26)
- **RCM CEOS-ARD (CSA, AWS)** — open, analysis-ready C-band compact-pol, Canada every few days. Find scenes via EODMS STAC, or read each scene's `product.xml` straight from the bucket — https://registry.opendata.aws/rcm-ceos-ard/ (Roy, 14.11.26)
- **ALOS PALSAR RTC 12.5 m (JAXA, at ASF)** — L-band 2006–2011 "then" layer, same Earthdata Login; `dataset=ALOS` in Vertex — https://search.asf.alaska.edu/#/?dataset=ALOS (Roy, 14.11.26)
- **ALOS-2 PALSAR-2 ScanSAR + yearly mosaics (JAXA)** — free L-band 2014 →; ASF mirror, JAXA open data; stripmap is commercial — https://www.eorc.jaxa.jp/ALOS/en/dataset/alos_open_and_free_e.htm · https://asf.alaska.edu/notices/alos-2-data-available-from-asf (Roy, 14.11.26)
- **Sentinel-1 (ESA Copernicus)** — densest open C-band since 2014; at ASF (same login), Copernicus Data Space, Microsoft Planetary Computer (RTC, no login) — https://asf.alaska.edu/datasets/ (Roy, 14.11.26)
- **Global Seasonal Sentinel-1 Interferometric Coherence** (Kellndorfer et al. 2022, Sci. Data 9:73) — C-band 12-day coherence 2019–20, AWS, no login — https://registry.opendata.aws/ebd-sentinel-1-global-coherence-backscatter/ (Noa, 14.11.26)
- **ERS-2, Envisat ASAR, Biomass (ESA)** — free with an ESA account; not used yet — https://earth.esa.int/eogateway/ (Roy, 14.11.26)
- **Capella / Umbra Open Data** (CC BY 4.0, AWS) — X-band, only chosen scenes; not used yet — https://registry.opendata.aws/capella_opendata/ · https://registry.opendata.aws/umbra-open-data/ (Roy, 14.11.26)
- **SAR mission access survey** — which SAR satellites since 2000 have usable data; cross-check with the CEOS database — https://database.eohandbook.com (Roy, 14.11.26)

## Other data

- **Copernicus DEM GLO-30** (ESA / EU, AWS open data, no login) — elevation for radar shadow / layover and troposphere correction — https://registry.opendata.aws/copernicus-dem/ (Roy, 31.10.26)
- **ESA WorldCover 2021 v200** (CC BY 4.0, AWS COGs) — land cover: cropland, built-up, forest — https://esa-worldcover.org (Shai, 09.11.26)
- **WorldPop 2025 constrained population, 1 km** (CC BY 4.0) — people in affected zones — https://www.worldpop.org (Shai, 09.11.26)
- **Microsoft Planetary Computer** (STAC, no login; `pystac-client`, `planetary-computer`) — Sentinel-1 RTC, Sentinel-2 L2A, ALOS PALSAR annual mosaics, USDA cropland layer — https://planetarycomputer.microsoft.com/catalog (Noa, 14.11.26)
- **Copernicus EMS Global Flood Monitoring (GFM)** — Sentinel-1 flood extent, open STAC `https://stac.eodc.eu/api/v1` (collection GFM) — https://global-flood.emergency.copernicus.eu (Shai, 14.11.26)
- **GDACS event API** (UN OCHA + EU JRC) — Orange/Red disasters with place and dates — https://www.gdacs.org/gdacsapi/ (Shai, 09.11.26)
- **International Charter Space and Major Disasters** — activations list (website, no public API) — https://disasterscharter.org/activations (Shai, 09.11.26)
- **USGS EDEN** — Everglades daily water depth, ground truth for floods — https://sofia.usgs.gov/eden/ (Shai, 14.11.26)
- **USDA NASS Crop Progress, Crop Sequence Boundaries** — harvest timing and field polygons for crop checks — https://www.nass.usda.gov (Noa, 14.11.26)
- **Open-Meteo Previous Runs API** — archived rain forecasts — https://open-meteo.com/en/docs/previous-runs-api (Noa, 14.11.26)
- **EOX Sentinel-2 cloudless 2023** (CC BY-NC-SA 4.0) — sharp basemap patches — https://s2maps.eu (Shai, 09.11.26)
- **Esri World Imagery, OpenStreetMap** — basemaps — https://www.openstreetmap.org/copyright (Shai, 31.10.26)

## Tools and services

- **Vercel (Hobby, free)** — serverless static hosting of the site, deploys from `main` — https://vercel.com (Noa, 14.11.26)
- **GoDaddy** — custom domain for presenting the site (DNS pointed at Vercel) — https://www.godaddy.com (Noa, 14.11.26)
- **asf_search** (Python, ASF) — NISAR / ALOS / Sentinel-1 search — https://docs.asf.alaska.edu/asf_search/basics/ (Roy, 31.10.26)
- **NASA Worldview** — view NISAR layers in the browser — https://worldview.earthdata.nasa.gov/ (Roy, 31.10.26)
- **Python: h5py, numpy, scipy, rasterio, pyproj, shapely, Pillow, matplotlib, requests** — read HDF5 / GeoTIFF, reproject, process, plot, call STAC APIs — https://www.h5py.org (Roy, 31.10.26)

- **Leaflet** (BSD-2) — web map in the landing film — https://leafletjs.com (Shai, 14.11.26)

## AI tools

- **Claude Code** (Anthropic) — coding, research and docs assistant — https://claude.com/claude-code (Roy, 30.10.26)

## References

- **Challenge statement: Dancing with the SARs** — https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/ (Roy, 30.10.26)
- **NISAR Mission Science Users' Handbook (JPL, 2025)** — https://doi.org/10.48577/jpl.UD4HV3 (Roy, 31.10.26)
- **NASA Earth science data policy + NISAR data use & citation guidance** — licence and credit for NISAR data — https://www.earthdata.nasa.gov/data-and-information-policy · https://nisar-docs.asf.alaska.edu/data-use-citation-guidance/ (Roy, 31.10.26)
- **Rentschler et al. 2022, Nature Comms** — 1.81 billion people exposed to floods (landing film) — https://doi.org/10.1038/s41467-022-30727-4 (Shai, 14.11.26)
- **NISAR mission requirements** — https://science.nasa.gov/mission/nisar/mission-requirements (Shai, 09.11.26)
