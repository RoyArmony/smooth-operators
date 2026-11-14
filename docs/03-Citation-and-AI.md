# 03 · Citation and AI disclosure

How we credit data, tools and papers, and how we disclose AI use. Feeds the **Data & AI Disclosure** and **References**
parts of the submission ([01](01-Competition.md#what-to-submit), [02](02-Submission-guide.md)).

## Rules
- **Credit everything we use:** data, code, libraries, APIs, map tiles, images, papers, AI tools. Even open source.
- **Where it goes:**
  - [`04-Sources-and-tools.md`](04-Sources-and-tools.md): one line when we first use something.
  - [`ACKNOWLEDGMENTS.md`](../ACKNOWLEDGMENTS.md): the credit / licence line, in the same commit.
  - Bundled third-party code: keep its licence file next to it (e.g. `web/vendor/<lib>/LICENSE`).
- **Use the provider's own wording** when it gives one (NISAR, Copernicus, ESA, CSA, JAXA). Copy it word for word.
- **Derived ≠ official.** Our maps and numbers are our processing, not official NASA products, and not endorsed by NASA or ISRO. Say so.
- **No NASA logos, flags or mission insignia** in our own or AI-made graphics.
- **Map credits on screen:** keep the attribution of every tile layer visible on the map.

## Credit lines for likely sources
Copy the line that matches what we actually use. Remove what we don't.

### NASA and partner data
| Source | Credit / terms |
|---|---|
| **NISAR** (any product, ASF DAAC) | "NISAR data: NASA/JPL-Caltech and ISRO, distributed by ASF DAAC." Open (NASA data policy). Follow the [NISAR data use & citation guidance](https://nisar-docs.asf.alaska.edu/data-use-citation-guidance/). |
| NISAR dataset DOIs (PROVISIONAL) | GCOV **10.5067/NIL2GCOV-P1** · GUNW **10.5067/NIL2GUNW-P1** · SME2 **10.5067/NIL3SME2-P1** (read from each file's `identification/productDoi`; VALIDATED products have their own) |
| **OPERA** (DSWx-HLS, DSWx-S1, RTC-S1, DIST, DISP), NASA JPL, PO.DAAC / ASF | NASA open data; cite product + DOI from its landing page |
| **HLS** (Landsat 8/9 + Sentinel-2), LP DAAC / NASA GIBS | NASA open data; Sentinel-2 part: Copernicus |
| **NASA GIBS** tiles, **Blue Marble** | NASA open data (Blue Marble: NASA Earth Observatory, public domain) |
| **SWOT** (NASA / CNES, with CSA and UK Space Agency), PO.DAAC / Hydrocron | NASA open data; cite the SWOT product (PO.DAAC) |
| **NASA OMNI** (SPDF, GSFC) via CDAWeb | NASA open data |
| **RADARSAT-1** (CSA), EODMS / AWS | Open Government Licence – Canada; "RADARSAT-1 data © Canadian Space Agency" |
| **RCM** (CSA / NRCan), EODMS / AWS CEOS-ARD | RCM public user licence (CSA); use the credit line in the licence |
| **ALOS PALSAR RTC** (JAXA/METI; RTC by ASF DAAC) | "ALOS PALSAR © JAXA/METI [year], accessed through ASF DAAC; includes material © JAXA/METI [year]" |
| **SAOCOM** (CONAE) | Per the CONAE licence signed at registration |

### Other data
| Source | Credit / terms |
|---|---|
| **Copernicus DEM GLO-30** (ESA / EU) | "© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA" |
| **ESA WorldCover 2021 v200** | CC BY 4.0; "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium" |
| **WorldPop** (Univ. of Southampton) | CC BY 4.0; credit WorldPop |
| **Copernicus EMS Global Flood Monitoring** | "© European Union, Copernicus Emergency Management Service"; free and open |
| **GDACS** (UN OCHA + EU JRC) | © GDACS, credit required |
| **International Charter Space and Major Disasters** | © the Charter; public website |

### Map imagery
| Source | Terms |
|---|---|
| **Esri World Imagery** (Esri, Maxar, Earthstar Geographics) | Esri terms of use; attribution shown on the map |
| **OpenStreetMap** | © OpenStreetMap contributors, ODbL |
| **Sentinel-2 cloudless by EOX** | CC BY-NC-SA 4.0: non-commercial, credit EOX, share-alike; "Contains modified Copernicus Sentinel data [year]" |

### Common software licences
| Package | Licence |
|---|---|
| asf_search | BSD |
| numpy, scipy, h5py, rasterio, shapely, scikit-learn, uvicorn | BSD-3-Clause |
| pyproj, FastAPI, pyshp, globe.gl, three.js, Mermaid | MIT |
| Leaflet | BSD-2-Clause |
| Pillow | MIT-CMU |
| requests, Playwright | Apache-2.0 |
| matplotlib | PSF-based |
| Google Fonts (e.g. Inter) | SIL Open Font License 1.1 |

## Citation formats

**Data (NISAR example):**
> NASA/JPL-Caltech & ISRO (2026). NISAR L2 Geocoded Polarimetric Covariance (GCOV), PROVISIONAL [doi:10.5067/NIL2GCOV-P1].
> Track [T], frame [F]. Distributed by ASF DAAC. Accessed [date].

**Paper:** Authors (year). Title. *Journal* volume, pages. DOI.

**Web page / tool:** Owner. *Title*. URL (accessed [date]).

**Our project** (README):
```bibtex
@misc{smoothoperators2026,
  title  = {[Project name]},
  author = {Smooth Operators (Roy Armony, Shai Yehezkel, Noa Shoham)},
  year   = {2026},
  note   = {NASA Space Apps Challenge 2026, Haifa},
  url    = {[repo URL]}
}
```

**Our data products** (if we publish any): "Derived from NASA data. Processing: Smooth Operators, NASA Space Apps 2026, CC BY 4.0.
Not an official NASA product." Keep the original source credit next to it.

## Key references (knowledge base)
Official and scientific sources worth citing for **Validity** and **Impact**. Cite only what we actually rely on.

**NISAR mission and data**
- NISAR Data User Guide (ASF) — https://nisar-docs.asf.alaska.edu
- NISAR Science Users' Handbook (JPL, 2025) — https://doi.org/10.48577/jpl.UD4HV3
- NISAR mission overview and requirements (NASA) — https://science.nasa.gov/mission/nisar/mission-overview/ · https://science.nasa.gov/mission/nisar/mission-requirements
- eoPortal: NISAR — https://www.eoportal.org/satellite-missions/nisar
- WMO OSCAR/Space: NISAR SAR-L — https://space.oscar.wmo.int/instruments/view/sar_l_nisar
- CF conventions (metadata standard NISAR follows) — https://cfconventions.org/
- NASA Earth science data policy — https://www.earthdata.nasa.gov/data-and-information-policy
- NASA data use and citation guidance — https://www.earthdata.nasa.gov/about/esdis/esco/standards-practices/data-use-citation-guidance

**Training and outreach (official challenge resources, see [01 · Part C](01-Competition.md#part-c--official-challenge-resources))**
- NASA ARSET 2026 NISAR trainings (surface water; surface displacement)
- Peacock, A., An, K., Pinto, N., & Lou, Y. (2024). *NISAR ArcGIS Storymaps.* Zenodo. https://doi.org/10.5281/zenodo.10818833
- NISAR Applications White Papers — https://nisar.jpl.nasa.gov/applications/societal-benefit/
- UAVSAR Postcards — https://uavsar.jpl.nasa.gov/education/postcards.html
- NASA Earthdata, "What is SAR" — https://www.earthdata.nasa.gov/learn/earth-observation-data-basics/sar

**Floods and water**
- Hübinger et al. 2026, L-band InSAR for flooded vegetation in tropical wetlands, *Remote Sens. Environ.* 332:115086 — https://doi.org/10.1016/j.rse.2025.115086
- Alsdorf et al. 2000, InSAR water levels on the Amazon flood plain, *Nature* 404:174; Wdowinski et al. 2004/2008
- Kolluru et al. 2026, limits of optical flood mapping by land cover, arXiv 2606.07780 — https://arxiv.org/abs/2606.07780
- Tellman et al. 2021, Global Flood Database, *Nature* 596:80
- Yao et al. 2023, decline in global lake water storage, *Science* 380:743

**Ground motion, damage, hazards**
- Yun et al. 2015, ARIA damage proxy maps from InSAR coherence, *Seismol. Res. Lett.* 86(6)
- Burrows et al. 2020, coherence methods for rapid landslide detection, *NHESS* 20:3197 — https://nhess.copernicus.org/articles/20/3197/2020/
- Jacquemart & Tiampo 2021, coherence time series before landslides, *NHESS* 21:629
- Sandwell & Price 1998, interferogram stacking, *JGR* 103:30183
- Lu & Dzurisin 2010, Okmok InSAR deflation, *JGR* 115, B00B03
- Nof et al. 2013, sinkhole precursors along the Dead Sea revealed by InSAR, *Geology* 41(9)
- COMET Volcanic and Magmatic Deformation Portal — https://comet.nerc.ac.uk/comet-volcano-portal/

**Vegetation, fire, soil, snow**
- Tanase et al. 2010, burn severity and SAR backscatter, *IEEE TGRS* 48(8); An, Jones & Lou 2023, *Earth Space Sci.* doi:10.1029/2023ea002943
- JICA-JAXA JJ-FAST, L-band deforestation alerts — https://www.eorc.jaxa.jp/jjfast/
- Hethcoat et al. 2021 (*RSE* 259:112411), 2022 (*Remote Sens.* 14:179), selective logging with SAR
- Deng et al. 2023 (*Remote Sens.* 15:4538); Zhang et al. 2024 (*Remote Sens.* 16:1591), L- vs C-band coherence over vegetation
- De Zan & Gomba 2018 (*RSE* 217:562); Molan & Lu 2020 (*Remote Sens.* 12:1511), closure phase and soil moisture
- Tarricone et al. 2023, L-band InSAR snow water equivalent, *The Cryosphere* 17:1997

**Dual-Use (space + Earth)**
- International Mars Ice Mapper concept (NASA, CSA, ASI, JAXA): L-band polarimetric SAR to find buried ice

## Data access tools (for reference)
- NASA Earthdata Login — https://urs.earthdata.nasa.gov · CMR — https://cmr.earthdata.nasa.gov
- ASF Vertex — https://search.asf.alaska.edu · `asf_search` — https://docs.asf.alaska.edu/asf_search/basics/
- NASA Worldview — https://worldview.earthdata.nasa.gov/ · GIBS — https://nasa-gibs.github.io/gibs-api-docs/
- PO.DAAC Hydrocron (SWOT time series) — https://podaac.github.io/hydrocron/
- OPERA products — https://www.jpl.nasa.gov/go/opera/products
- ISRO Bhoonidhi (NISAR S-band) — https://bhoonidhi.nrsc.gov.in
- CSA open data — https://donnees-data.asc-csa.gc.ca · EODMS — https://www.eodms-sgdot.nrcan-rncan.gc.ca/
- AWS open data: RADARSAT-1, RCM CEOS-ARD, Copernicus DEM — https://registry.opendata.aws/
- JAXA ALOS open data — https://www.eorc.jaxa.jp/ALOS/en/dataset/alos_open_and_free_e.htm
- GDACS API — https://www.gdacs.org/gdacsapi/ · Disasters Charter activations — https://disasterscharter.org/activations
- Copernicus EMS GFM — https://global-flood.emergency.copernicus.eu

## AI disclosure

The site calls AI tools "SI" (Super Intelligence). **Allowed as a tool, not to come up with the idea.** Be clear and honest:
judges don't see the SI form field, but they do see the marks in the project and judge originality and intent from them.

| What | How we disclose |
|---|---|
| **Code** made with AI | README "AI use" section + commit trailer `Co-Authored-By: Claude …` (added by Claude Code) |
| **Data / text** made with AI | Say so in the text and in metadata (README, file header, doc note) |
| **Images and videos** made by AI | **Visible watermark**, e.g. "AI-generated" or "Made with AI" in a corner |
| **Audio** made by AI | Say so in the text and the metadata |
| **NASA branding** | AI output must not use or change NASA logos, flags or mission identifiers |

**Every AI tool we use goes in [04](04-Sources-and-tools.md#ai-tools)** (name, maker, what for). Include AI used outside the repo
(chat for wording, image generators, slide tools).

**Template: SI form field**
> We used Claude Code (Anthropic) as a coding and research assistant: writing and reviewing code, reading data documentation,
> and drafting text. The team chose the idea, the study areas and the method, checked the results against [sources], and
> reviewed all AI-assisted code. [Other tools: …]. AI-made images in the demo carry a visible watermark.

**Template: README "AI use"**
> Parts of this code and documentation were written with help from Claude Code (Anthropic). Commits it helped with carry a
> `Co-Authored-By: Claude` trailer. The idea, the analysis choices and the validation are the team's. AI-made images are watermarked.
