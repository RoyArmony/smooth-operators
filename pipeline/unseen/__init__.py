"""Unseen Earth flood pipeline: NISAR L-band water vs the official flood map (Copernicus GFM) -> site bundles.

  config      paths and constants (.env aware)
  auth        NASA Earthdata login (EARTHDATA_TOKEN, user/password, or ~/.netrc)
  remote      read HDF5 over HTTP range requests (no full downloads)
  gcov        NISAR L2 GCOV reader
  nisar       ASF search, consistent-stack selection, windowed stack reads for a bbox
  optical     OPERA DSWx-HLS optical water, regridded to the NISAR grid (threshold calibration, ocean mask)
  detect      open water + water under vegetation from HH/HV
  flood_nasa  second opinion: NISAR handbook §6.4 flood classifier
  gfm         Copernicus GFM flood extent + exclusion mask on our grid
  rcm         Canada's RCM CEOS-ARD scenes (CSA) on our grid, for validation
  landcover   ESA WorldCover on our grid (context)
  flood       stack -> water -> per-pass gap vs GFM (km², masks)
  bundle      masks -> events/<id>/ (PNG layers in EPSG:4326 + event.json), events/index.json
  cli         the `unseen` command
"""
