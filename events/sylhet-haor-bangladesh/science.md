# Sylhet haor, Bangladesh

**What:** water NISAR (L-band radar) sees inside the official flood map's "cannot see" area (Copernicus GFM exclusion mask).

**Method:** per NISAR pass: open water + water under vegetation from HH/HV (`pipeline/unseen/detect.py`), permanent water
removed; compared with GFM within 2 days; area = 80 m pixels. Shared method: `events/methods.md`.

**Limits:** a NISAR detection inside GFM's blank is a candidate, not proven flood; validation: docs/10-Results.md.
