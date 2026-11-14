# Glossary

All abbreviations and initials used in this repo, in **A–Z order**.

- **Rule:** keep the table in strict alphabetical order (ignore upper/lower case; symbols and digits come before letters, e.g. `L-band` before `L2`).
  When you add an entry, insert it in its place; never append it at the end.
- One line per term: abbreviation · what it stands for · what it means.

| Abbreviation | Stands for | What it means |
|---|---|---|
| **AI** | Artificial Intelligence | Must be disclosed in the submission (see SI). |
| **ALOS** | Advanced Land Observing Satellite | Japanese (JAXA) L-band radar; its PALSAR (2006–11) is our optional L-band "then" layer. |
| **API** | Application Programming Interface | A way for programs to request data, e.g. the ASF search API. |
| **ARD** | Analysis Ready Data | Data already corrected and gridded so you can analyze it directly (NISAR L2 is close to ARD). |
| **ARIA** | Advanced Rapid Imaging and Analysis (JPL) | JPL project that makes damage proxy and flood proxy maps from SAR after disasters. |
| **ARSET** | Applied Remote Sensing Training | NASA's free online training program for satellite data; has 2026 NISAR courses. |
| **ASF** | Alaska Satellite Facility | NASA's SAR data center (a DAAC). NISAR L-band products are downloaded from here. |
| **ASI** | Agenzia Spaziale Italiana | Italian space agency. |
| **AWS** | Amazon Web Services | Cloud provider. NASA Earthdata Cloud, RADARSAT-1, RCM and the Copernicus DEM are hosted there. |
| **CC BY** | Creative Commons Attribution | Open licence: reuse freely with credit. `-NC-SA` adds non-commercial and share-alike. |
| **CDN** | Content Delivery Network | Servers around the world that serve our static site fast (Vercel provides it). |
| **CEOS** | Committee on Earth Observation Satellites | International body of space agencies; sets the ARD standard (CEOS-ARD). |
| **CF** | Climate and Forecast conventions | The netCDF/HDF5 metadata standard that NISAR follows. |
| **CMR** | Common Metadata Repository | NASA's catalog of all Earth science datasets; Earthdata Search runs on it. |
| **CNAME** | Canonical Name (DNS record) | Points `www` of our GoDaddy domain at Vercel. |
| **CNES** | Centre National d'Études Spatiales | French space agency; SWOT partner with NASA. |
| **COG** | Cloud-Optimized GeoTIFF | A GeoTIFF laid out so a server can read just the part it needs over the internet. |
| **CONAE** | Comisión Nacional de Actividades Espaciales | Argentina's space agency; runs the SAOCOM L-band radar satellites. |
| **CORS** | Cross-Origin Resource Sharing | Browser rule that blocks reading other sites' data; why a GDACS feed may need a small proxy function. |
| **CSA** | Canadian Space Agency | Runs RADARSAT / RCM. A Haifa prize is for the best use of CSA data. |
| **DAAC** | Distributed Active Archive Center | One of ~12 NASA data centers, each for a science area (e.g. ASF, PO.DAAC). |
| **DEM** | Digital Elevation Model | A height map of the ground, e.g. Copernicus DEM GLO-30. |
| **DISP** | Displacement (OPERA product) | OPERA ground-motion product from InSAR. |
| **DLR** | Deutsches Zentrum für Luft- und Raumfahrt (German Aerospace Center) | Co-owner of the Copernicus DEM source data. |
| **DNS** | Domain Name System | Maps our GoDaddy domain name to Vercel's servers (A / CNAME records). |
| **DOI** | Digital Object Identifier | A permanent ID for a dataset or paper, e.g. `10.5067/NIL2GCOV-P1`. Used in citations. |
| **DSWx** | Dynamic Surface Water Extent (OPERA) | OPERA's surface-water maps (from HLS, Sentinel-1, NISAR). |
| **EDEN** | Everglades Depth Estimation Network | USGS daily water-level and depth surfaces (400 m) for the Everglades, from ~240 gauges; our ground truth. |
| **EMS** | Emergency Management Service (Copernicus) | EU service that maps disasters from satellite data. |
| **EODC** | Earth Observation Data Centre | Vienna data centre whose open STAC catalogue serves Copernicus GFM flood maps. |
| **EODMS** | Earth Observation Data Management System | Canada's portal for RADARSAT / RCM data. |
| **EPSG** | European Petroleum Survey Group (code) | Catalog numbers for coordinate systems: 4326 = lat/lon, 3857 = Web Mercator, 32636 = UTM 36N. |
| **ESA** | European Space Agency | Runs Sentinel-1 and the Copernicus DEM (with the EU). |
| **GCOV** | Geocoded Polarimetric Covariance | NISAR L2 "brightness" product: terrain-corrected backscatter (HH, HV), 20 m. |
| **GDACS** | Global Disaster Alert and Coordination System | UN + EU disaster alert feed (quakes, floods, volcanoes, fires, cyclones) with a free API. |
| **GDAL** | Geospatial Data Abstraction Library | Open-source tools for reading, converting and reprojecting rasters. |
| **GFM** | Global Flood Monitoring | Copernicus EMS service: automatic Sentinel-1 flood maps worldwide. |
| **GIBS** | Global Imagery Browse Services | NASA's ready-made map tiles (images only); Worldview shows them. |
| **GIS** | Geographic Information System | Mapping software and methods, e.g. QGIS. |
| **GloFAS** | Global Flood Awareness System | Copernicus global flood service; its satellite flood map is GFM. The official map we add NISAR to. |
| **GRD** | Ground Range Detected | A common SAR product type (amplitude only). |
| **GUNW** | Geocoded Unwrapped Interferogram | NISAR L2 ground-motion pair: phase change between two dates + coherence. |
| **HDF5** | Hierarchical Data Format v5 | The file format of NISAR products (`.h5`): a folder tree inside one file. |
| **HH / HV / VV** | Polarizations (send / receive: Horizontal, Vertical) | HH and VV react to surfaces and water; HV to volume (vegetation). |
| **HLS** | Harmonized Landsat Sentinel-2 | NASA's combined optical product (30 m, true color). |
| **HTTPS** | Hypertext Transfer Protocol Secure | Encrypted web; Vercel gives our domain a certificate automatically. |
| **InSAR** | Interferometric SAR | Comparing the phase of two SAR images to measure ground motion. |
| **IoU** | Intersection over Union | Overlap between two maps (0–1): shared area ÷ combined area. A standard mask-accuracy measure. |
| **IP** | Internet Protocol (address) | The numeric server address our domain's A record points to. |
| **ISRO** | Indian Space Research Organisation | NASA's partner in NISAR; built the S-band radar. |
| **JAXA** | Japan Aerospace Exploration Agency | Runs ALOS / ALOS-2 (L-band SAR). |
| **JJ-FAST** | JICA-JAXA Forest Early Warning System in the Tropics | Operational L-band deforestation alerts through clouds. |
| **JPL** | Jet Propulsion Laboratory | NASA center that built NISAR's L-band radar and processes its products. |
| **JRC** | Joint Research Centre (EU) | EU science service; co-runs GDACS. |
| **JS** | JavaScript | The language of our web app (no build step). |
| **JSON** | JavaScript Object Notation | Text format of our event bundles (`event.json`, `index.json`). |
| **L-band / S-band / C-band / X-band** | Radar frequency bands | L ≈ 24 cm (NISAR), S ≈ 9.4 cm (NISAR, ISRO), C ≈ 5.6 cm (Sentinel-1, RCM, RADARSAT-1), X ≈ 3 cm. |
| **L2 / L3** | Processing Level 2 / 3 | L2: geocoded products (GCOV, GUNW). L3: derived geophysical maps (e.g. soil moisture). |
| **LANCE** | Land, Atmosphere Near real-time Capability for Earth observation | NASA near-real-time service; publishes the MODIS/VIIRS global flood products. |
| **LLM** | Large Language Model | An AI model like Claude. |
| **LOS** | Line Of Sight | The direction from the satellite to the ground. InSAR measures motion along it. |
| **MODIS** | Moderate Resolution Imaging Spectroradiometer | NASA optical sensor on Terra/Aqua; many GIBS layers come from it. |
| **MVP** | Minimum Viable Product | The smallest demoable version of our app. |
| **NASA** | National Aeronautics and Space Administration | US space agency; NISAR partner; runs Space Apps. |
| **NHESS** | Natural Hazards and Earth System Sciences | Open-access EGU journal (landslides, floods). |
| **NISAR** | NASA-ISRO Synthetic Aperture Radar | The satellite of our challenge: L-band + S-band radar, launched 2025, repeats every 12 days. |
| **OCHA** | UN Office for the Coordination of Humanitarian Affairs | Co-runs GDACS. |
| **OMNI** | (NASA) OMNI solar-wind and geomagnetic data set | Hourly space-weather indices (Kp, Dst) from NASA SPDF. |
| **OPERA** | Observational Products for End-Users from Remote Sensing Analysis | JPL project making ready-made products (water, disturbance, displacement). |
| **OSCAR** | Observing Systems Capability Analysis and Review tool | WMO's online database of satellites and instruments. |
| **P0 / P1 / P2** | Priority 0 / 1 / 2 | Task priority in `tasks.md`: must / should / nice to have. |
| **PALSAR** | Phased Array type L-band SAR | The L-band radar on JAXA's ALOS (2006–2011, free at ASF). |
| **PNG** | Portable Network Graphics | Image format of our map layers (with transparency). |
| **PO.DAAC** | Physical Oceanography DAAC | NASA DAAC for ocean and surface-water data (OPERA DSWx, SWOT). |
| **QGIS** | Quantum GIS | Free desktop GIS. Opens GeoTIFFs and (≥ 4.2) NISAR `.h5` files. |
| **RCM** | RADARSAT Constellation Mission | Canada's three C-band SAR satellites (CSA). |
| **RGB** | Red, Green, Blue | Color channels; radar composites map polarizations to them. |
| **RGBA** | Red, Green, Blue, Alpha | Image colour channels plus transparency; our PNG map layers use it. |
| **RR / RL** | Right-Right / Right-Left (circular polarisations) | The two RCM compact-pol channels; RL is dark over water, RR−RL high means double bounce. |
| **RTC** | Radiometric Terrain Correction | Normalizing radar brightness for slopes, so values are comparable. Applied in GCOV. |
| **SAOCOM** | Satélite Argentino de Observación con Microondas | Argentina's L-band radar satellites (1A 2018, 1B 2020). |
| **SAR** | Synthetic Aperture Radar | An imaging radar that uses the satellite's motion to build a long virtual antenna: sharp images, day and night, through clouds. |
| **SI** | Super Intelligence | Space Apps' term for AI tools. Use must be disclosed; AI images/videos need a visible watermark ([02](docs/02-Submission-guide.md)). |
| **SLC** | Single Look Complex | A full-resolution SAR image that keeps amplitude and phase. |
| **SME** | Subject Matter Expert | NASA experts who answer questions on Space Apps Connect. |
| **SME2** | Soil Moisture (NISAR L3 product) | Soil moisture of the top ~5 cm, 200 m. |
| **STAC** | SpatioTemporal Asset Catalog | A standard way to search satellite data by area and date (GFM, RCM catalogues). |
| **SWOT** | Surface Water and Ocean Topography | NASA / CNES satellite (with CSA and the UK Space Agency) that measures water levels of lakes, rivers and the sea. |
| **UAVSAR** | Uninhabited Aerial Vehicle Synthetic Aperture Radar | NASA/JPL airborne L-band radar (since 2009); NISAR's test bed. |
| **UI / UX** | User Interface / User Experience | What the user sees / how it feels to use. |
| **USGS** | United States Geological Survey | US science agency; runs the EDEN Everglades water-level network we validate against. |
| **VIIRS** | Visible Infrared Imaging Radiometer Suite | NASA/NOAA optical sensor; daily true-color imagery in GIBS. |
| **WMO** | World Meteorological Organization | UN agency for weather and climate; runs OSCAR. |
