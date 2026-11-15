# Sharon storm, Israel

**What:** a flash flood. Rain fell in hours and most streets drained the same day, so we need a radar pass that day.

**Data:** Sentinel-1 (ESA Copernicus, C-band) passed the afternoon of the storm (8 Nov, 15:40 UTC) and the next morning
(9 Nov, 03:43 UTC). NISAR (L-band) passed on 3 Nov (before); its next pass on the same track (15 Nov) is added when ASF
has processed it. Official flood map (Copernicus GFM): its server was down at build time.

**Method:** same-track change, so geometry is identical (3x3 median). New open water = VV darker than -15 dB after,
more than 3 dB darker than 6 days before, not water before. Soaked ground = land more than 3 dB brighter than 6 days
before (wet soil reflects more C-band). Area = pixels x 80 m x 80 m on the NISAR grid.

**Result:** lots of soaked ground, no standing water in open fields at 80 m: the flood was in streets and drained in hours.

**Limits:** C-band cannot see water under trees or between buildings (double bounce in towns), so flooded streets are
mostly missed: this is water in fields and open ground. Wet bare soil can also darken a little; the 3 dB drop and the
-15 dB level keep only strong change. Not checked against ground reports yet.
