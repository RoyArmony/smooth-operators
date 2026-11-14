# Acknowledgments and third-party notices

Our code is MIT ([LICENSE](LICENSE)). Everything below belongs to others and keeps its own terms.
How to write each line: [docs/03](docs/03-Citation-and-AI.md). Working list: [docs/04](docs/04-Sources-and-tools.md).

Our maps and numbers are derived products, not official NASA products, and not endorsed by NASA or ISRO.

## Data

| Source | Used for | Credit / terms |
|---|---|---|
| **NISAR L2 GCOV, L2 GUNW, L3 SME2** (NASA/JPL-Caltech & ISRO, ASF DAAC) | L-band backscatter, ground motion + coherence, soil moisture | "NISAR data: NASA/JPL-Caltech and ISRO, distributed by ASF DAAC." Open (NASA data policy). DOIs (PROVISIONAL): GCOV 10.5067/NIL2GCOV-P1 · GUNW 10.5067/NIL2GUNW-P1 · SME2 10.5067/NIL3SME2-P1; VALIDATED products have their own. [Citation guidance](https://nisar-docs.asf.alaska.edu/data-use-citation-guidance/) |
| **NISAR S-band** (ISRO, Bhoonidhi) | S-band backscatter | Per ISRO Bhoonidhi terms of use; credit "NISAR S-band data: ISRO" |
| **OPERA** DSWx-HLS, DSWx-S1, RTC-S1, DIST, DISP (NASA JPL, PO.DAAC / ASF) | Optical and radar water maps, comparisons | NASA open data; cite product + DOI from its landing page |
| **HLS** Landsat 8/9 + Sentinel-2 (LP DAAC / NASA GIBS) | Optical reference image | NASA open data; Sentinel-2 part: "Contains modified Copernicus Sentinel data [year]" |
| **NASA GIBS** tiles, **Blue Marble** | Web-map layers, globe basemap | NASA open data; Blue Marble: NASA Earth Observatory, public domain |
| **SWOT** LakeSP (NASA / CNES, with CSA and UK Space Agency; PO.DAAC / Hydrocron) | Lake water level | NASA open data; cite the SWOT product (PO.DAAC) |
| **NASA POWER** (NASA Langley, MERRA-2) | Daily rain and temperature | NASA open data; "Data obtained from the NASA Langley Research Center POWER Project" |
| **NASA OMNI** Kp / Dst (SPDF, GSFC, via CDAWeb) | Geomagnetic storm dates | NASA open data |
| **ASF HyP3** (ASF DAAC) | On-demand Sentinel-1 InSAR coherence | Free; credit ASF DAAC HyP3 + "Contains modified Copernicus Sentinel data [year]" |
| **RADARSAT-1** (CSA; EODMS / AWS) | C-band 1995–2013 "then" layer | Open Government Licence – Canada; "RADARSAT-1 data © Canadian Space Agency" |
| **RCM CEOS-ARD** (CSA / Natural Resources Canada; EODMS / AWS) | C-band compact-pol comparison | RCM public user licence (CSA); use the credit line in the licence |
| **ALOS PALSAR RTC** (JAXA/METI; RTC by ASF DAAC) | L-band 2006–2011 "then" layer | "ALOS PALSAR © JAXA/METI [year], accessed through ASF DAAC; includes material © JAXA/METI [year]" |
| **ALOS-2 PALSAR-2 ScanSAR / mosaics** (JAXA) | L-band 2014 → | JAXA open-and-free terms; "© JAXA" |
| **Sentinel-1, Sentinel-2** (ESA Copernicus; ASF, Planetary Computer) | C-band radar, optical checks | Free and open; "Contains modified Copernicus Sentinel data [year]" |
| **Global Seasonal Sentinel-1 Coherence** (Kellndorfer et al. 2022, AWS) | C-band coherence reference | CC BY 4.0; cite Kellndorfer et al. 2022, *Sci. Data* 9:73 |
| **Copernicus DEM GLO-30** (ESA / EU, AWS) | Elevation, shadow/layover, troposphere | "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA" |
| **ESA WorldCover 2021 v200** | Land cover | CC BY 4.0; "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium" |
| **WorldPop 2025** (Univ. of Southampton) | Population | CC BY 4.0; credit WorldPop |
| **Copernicus EMS Global Flood Monitoring** | Sentinel-1 flood extent | "© European Union, Copernicus Emergency Management Service"; free and open |
| **GDACS** (UN OCHA + EU JRC) | Disaster events | © GDACS, credit required |
| **International Charter Space and Major Disasters** | Disaster activations | © the Charter; public website |
| **USGS EDEN** | Everglades water depth (ground truth) | US Government public domain; credit USGS |
| **USDA NASS** Crop Progress, Crop Sequence Boundaries, Cropland Data Layer | Crop and harvest checks | US Government public domain; credit USDA NASS |
| **Open-Meteo** | Archived rain forecasts | CC BY 4.0; "Weather data by Open-Meteo.com" |
| **Microsoft Planetary Computer** | STAC access to Sentinel, ALOS mosaics, USDA layers | Service; each dataset keeps its own licence (above) |

- Video in the landing film: "Sangke - Prek Toal, Cambodge" by Pierre André Leclercq, Wikimedia Commons, **CC BY-SA 4.0** (8 s cut, re-encoded; the cut is shared under the same licence) — https://commons.wikimedia.org/wiki/File:Sangke-prek-toal-cambodge-.webm

## Map imagery

| Source | Terms |
|---|---|
| **Esri World Imagery** (Esri, Maxar, Earthstar Geographics) | Esri terms of use; attribution shown on the map |
| **OpenStreetMap** | © OpenStreetMap contributors, ODbL |
| **Sentinel-2 cloudless by EOX** | CC BY-NC-SA 4.0: non-commercial, credit EOX, share-alike; "Contains modified Copernicus Sentinel data [year]" |

## Software

| Package | Licence |
|---|---|
| asf_search | BSD |
| Leaflet 1.9 (bundled in `site/vendor/leaflet/`, licence file next to it) | BSD-2-Clause |
| numpy, scipy, h5py, rasterio, shapely | BSD-3-Clause |
| pyproj | MIT |
| Pillow | MIT-CMU |
| matplotlib | PSF-based |
| requests | Apache-2.0 |

## Research we built on

- NISAR Data User Guide (ASF) — https://nisar-docs.asf.alaska.edu
- Rentschler, J., Salhab, M., Jafino, B. A. (2022). Flood exposure and poverty in 188 countries. *Nature Communications* 13, 3527 (1.81 billion people exposed to 1-in-100-year floods; landing film) — https://doi.org/10.1038/s41467-022-30727-4
- NISAR Mission Science Users' Handbook (JPL, 2025) — https://doi.org/10.48577/jpl.UD4HV3
- Peacock, A., An, K., Pinto, N., & Lou, Y. (2024). *NISAR ArcGIS Storymaps.* Zenodo. https://doi.org/10.5281/zenodo.10818833
- NISAR Applications White Papers (NASA/JPL) — https://nisar.jpl.nasa.gov/applications/societal-benefit/
- NASA ARSET 2026 NISAR trainings (surface water; surface displacement) — https://appliedsciences.nasa.gov/get-involved/training
- CSA SAR Python Tutorial (modified MIT) — https://github.com/asc-csa/Synthetic_Aperture_Radar_Tutorial

## AI tools

- **Claude Code** (Anthropic): coding, research and docs assistant. See [docs/03 · AI disclosure](docs/03-Citation-and-AI.md#ai-disclosure).
