"""Flood history of one place, in the event-folder format v2 (docs/12): events/<place>/history/.

    python -m unseen.historyfolder mekong-delta-vietnam

Long series from RADARSAT-1 (CSA, 1996-2013) where it has the place, plus NISAR (2026), one image about every
month or two (each year's wettest image always kept). Per image: the radar picture, our flood map from that radar,
an optical photo near the same day (MODIS Terra/Aqua from 2000, HLS for 2026), and the official flood maps where
they exist (Copernicus GFM from 2015, NASA OPERA DSWx-HLS from 2023), with km² for each in history/event.json.
All analysis runs on the NISAR 80 m grid (frequency B, native), before any picture is made.
"""
import argparse
import datetime as dt
import io
import json

import numpy as np
import requests
from PIL import Image
from scipy.ndimage import median_filter

from . import bundle, optical
from .auth import session as earthdata_session
from .config import EVENTS_DIR, REPO
from .detect import detect
from .eventfolder import C, HEX, PLACES, Writer, classes_rgba, dswx_classes, gfm_on_grid, grey, photo_for
from .flood import load
from .history import align, rs1_on_grid, rs1_scenes, shift, split_threshold

MIN_GAP_DAYS = 30          # "every month or two": keep an image only if >= 30 days from the ones kept
MODIS_DAYS = 3             # optical photo for old dates: least cloudy MODIS day within +-3 days
GIBS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
D = dt.date.fromisoformat


def thin(rows):
    """rows: [(date, flood_km2, ...)] -> subset: each year's wettest, then others >= MIN_GAP_DAYS from all kept."""
    keep = {max((r for r in rows if r[0][:4] == y), key=lambda r: r[1])[0] for y in {r[0][:4] for r in rows}}
    for r in sorted(rows):
        if r[0] not in keep and all(abs((D(r[0]) - D(k)).days) >= MIN_GAP_DAYS for k in keep):
            keep.add(r[0])
    return sorted(keep)


def modis_photo(bbox, date, size=300):
    """Least cloudy MODIS true-colour day (Terra from 2000-02-24, Aqua from 2002-07-04) within +-MODIS_DAYS.
    Cloud = bright white pixels (all bands > 180). Returns (date, satellite, RGB array, cloud fraction) or None."""
    if D(date) < dt.date(2000, 2, 24):
        return None
    best = None
    for k in range(-MODIS_DAYS, MODIS_DAYS + 1):
        d = (D(date) + dt.timedelta(days=k)).isoformat()
        for sat in ("Terra", "Aqua"):
            if sat == "Aqua" and D(d) < dt.date(2002, 7, 4):
                continue
            p = dict(SERVICE="WMS", REQUEST="GetMap", VERSION="1.3.0", LAYERS=f"MODIS_{sat}_CorrectedReflectance_TrueColor",
                     CRS="EPSG:4326", BBOX=f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}", WIDTH=size, HEIGHT=size,
                     FORMAT="image/jpeg", TIME=d)
            try:
                r = requests.get(GIBS, params=p, timeout=60)
                im = np.array(Image.open(io.BytesIO(r.content)).convert("RGB"))
            except Exception:  # noqa: BLE001
                continue
            if (im.max(-1) < 10).mean() > 0.3:          # outside the swath
                continue
            cloud = float((im.min(-1) > 180).mean())
            key = (cloud, abs(k))
            if best is None or key < best[0]:
                best = (key, d, sat, im, cloud)
    return None if best is None else best[1:]


def build(place):
    case = PLACES[place]
    bbox = case["bbox"]
    stack, ndates, grid, _ = load(bbox, case["stack_key"])
    shape = stack.shape[-2:]
    px = (grid["dx"] / 1000) ** 2
    L = detect(stack, pixel_m=grid["dx"], open_hh=case["open_hh"], open_hv=case["open_hv"])
    perm, valid = L["permanent"], L["valid"]
    ref = np.nanmedian(L["hh"], 0)
    folder = EVENTS_DIR / place / "history"
    W = Writer(folder, grid)

    # 1. every candidate image: RADARSAT-1 scenes + NISAR passes, flood km² from our analysis
    cand = {}
    for f in rs1_scenes(bbox):
        d = f["properties"]["datetime"][:10]
        db = rs1_on_grid(f, grid, shape)
        if np.isfinite(db).mean() < 0.8:
            continue
        dy, dx = align(ref, db)
        db = shift(db, dy, dx)
        db = median_filter(np.nan_to_num(db, nan=np.nanmedian(db)), 3) * np.where(np.isfinite(db), 1, np.nan)
        thr, ntiles = split_threshold(db, perm)
        ok = np.isfinite(db) & valid
        flood = (db < thr) & ~perm & ok
        cand[d] = dict(sensor="RADARSAT-1", db=db, flood=flood, ok=ok, info=dict(
            beam=f["properties"]["beam_mnemonic"], orbit=f["properties"]["sat:orbit_state"],
            scene=f["assets"]["cog"]["href"].rsplit("/", 1)[-1], threshold_db=round(thr, 1), split_tiles=ntiles,
            shift_px=[dy, dx]))
    hh = 10 * np.log10(np.where(stack[:, 0] > 0, stack[:, 0], np.nan))
    hv = 10 * np.log10(np.where(stack[:, 1] > 0, stack[:, 1], np.nan))
    for t, d in enumerate(ndates):
        w = (L["water"][t] | L["canopy"][t]) & ~perm & valid
        cand[d] = dict(sensor="NISAR", t=t, flood=w, ok=valid, info=dict(band="L, frequency B (80 m)"))
    keep = thin([(d, float(c["flood"].sum() * px)) for d, c in cand.items()])
    print(f"{len(cand)} images → keep {len(keep)}: {keep}")

    # 2. official maps where they exist (GFM from 2015, DSWx-HLS from 2023)
    nk = [d for d in keep if cand[d]["sensor"] == "NISAR"]
    dfiles = []
    if nk:
        try:
            og = optical.search(bbox, (D(nk[0]) - dt.timedelta(days=3)).isoformat(), (D(nk[-1]) + dt.timedelta(days=3)).isoformat())
            dfiles = optical.download(og, earthdata_session()) if og else []
        except Exception as e:  # noqa: BLE001
            print(f"[warn] DSWx-HLS: {e!r}"[:120])

    images = []
    for d in keep:
        c = cand[d]
        I = dict(date=d, sensor=c["sensor"], radar=c["info"], layers=[], optical=None, baselines={})
        # radar picture + our flood map
        if c["sensor"] == "RADARSAT-1":
            db = c["db"]
            lo, hi = np.nanpercentile(db, 2), np.nanpercentile(db, 98)
            W.picture("rs1_radar", d, grey(db, lo, hi), dict(group="radar", sensor="RADARSAT-1 C-band HH (CSA)",
                      label="RADARSAT-1 radar (dark = water)", legend=None, default=True), half=True)   # picture 160 m
            W.rgba("rs1_flood", d, classes_rgba([(c["flood"], "flood")]), dict(group="result", sensor="RADARSAT-1 (our analysis)",
                   label="Flood from RADARSAT-1 (our analysis)", legend=[[HEX(C["flood"]), "flood"]], default=True))
            I["layers"] += ["rs1_radar", "rs1_flood"]
        else:
            t = c["t"]
            rgb = np.dstack([grey(hh[t], -25, 0), grey(hv[t], -32, -8), grey(hh[t] - hv[t], 0, 15)])
            rgb[~valid] = 0
            W.picture("nisar_rgb", d, rgb, dict(group="radar", sensor="NISAR L-band GCOV",
                      label="NISAR radar (R = HH, G = HV, B = HH/HV)", legend=None, default=True), half=True)
            W.rgba("nisar_water", d, classes_rgba([(c["flood"], "flood")]), dict(group="result", sensor="NISAR (our analysis)",
                   label="Flood from NISAR (our analysis)", legend=[[HEX(C["flood"]), "flood"]], default=True))
            I["layers"] += ["nisar_rgb", "nisar_water"]
        I["flood_km2"] = round(float(c["flood"].sum() * px), 1)
        I["valid_pct"] = round(100 * float(c["ok"].mean()))
        # optical photo
        if c["sensor"] == "NISAR":
            pd_, ph, clear = photo_for(case, d)
            if ph is not None:
                W.picture("photo", pd_, ph, dict(group="optical", sensor="HLS (Landsat / Sentinel-2) via NASA GIBS",
                          label="Optical photo (HLS, 30 m)", legend=None, default=False), half=True)
                # 2026 pictures at half size here: full size in the flood folder (events/<place>/<YYYY-MM>-flood/)
                I["optical"] = dict(date=pd_, source="HLS", cloud_pct=round(100 * (1 - clear)))
                I["layers"].append("photo")
        else:
            m = modis_photo(bbox, d)
            if m:
                md, sat, im, cloud = m
                W._add("photo_modis", md, Image.fromarray(im), [[bbox[1], bbox[0]], [bbox[3], bbox[2]]], "jpg",
                       dict(group="optical", sensor="MODIS Terra / Aqua via NASA GIBS", label="Optical photo (MODIS, 250 m)",
                            legend=None, default=False))
                I["optical"] = dict(date=md, source=f"MODIS {sat}", cloud_pct=round(100 * cloud))
                I["layers"].append("photo_modis")
        # official flood maps (only on dates they exist)
        if c["sensor"] == "NISAR":
            base = {}
            G = gfm_on_grid(case, bbox, d, grid, shape)
            if G:
                seen = G["seen"] & valid
                base["gfm"] = dict(date=G["date"], seen=seen, flood=G["flood"] & ~perm & seen,
                                   clouds=np.zeros(shape, bool), veg=G["excluded"] & ~perm & seen & ~G["flood"])
            dd, cls = dswx_classes(dfiles, d, grid, shape) if dfiles else (None, None)
            if cls is not None:
                seen = (cls != 255) & valid & (cls != 254)
                base["dswx"] = dict(date=dd, seen=seen, flood=np.isin(cls, (1, 2)) & ~perm & seen,
                                    clouds=np.isin(cls, (252, 253)) & ~perm & seen, veg=np.zeros(shape, bool))
            for k, B in base.items():
                blank = B["clouds"] | B["veg"]
                W.rgba(f"{k}_classes", B["date"], classes_rgba([(perm & B["seen"], "permanent"), (B["clouds"], "clouds"),
                                                                 (B["veg"], "blank"), (B["flood"], "flood")]),
                       dict(group="baseline", sensor="Sentinel-1 (Copernicus GFM)" if k == "gfm" else "OPERA DSWx-HLS (NASA)",
                            label="Official flood map (GFM)" if k == "gfm" else "NASA flood map (OPERA DSWx-HLS)",
                            legend=[[HEX(C["flood"]), "flood"], [HEX(C["permanent"]), "permanent water"],
                                    [HEX(C["blank"] if k == "gfm" else C["clouds"]), "cannot see here"]],
                            default=k == "gfm"))
                adds = c["flood"] & blank
                fl = float(B["flood"].sum() * px)
                I["baselines"][k] = dict(
                    date=B["date"], flood_km2=round(fl, 1), cannot_see_km2=round(float(blank.sum() * px), 1),
                    cannot_see_clouds_km2=round(float(B["clouds"].sum() * px), 1),
                    cannot_see_vegetation_km2=round(float(B["veg"].sum() * px), 1),
                    nisar_adds_km2=round(float(adds.sum() * px), 1),
                    improvement_pct=round(100 * float(adds.sum() * px) / fl) if fl >= 5 else None)
                I["layers"].append(f"{k}_classes")
                if k == "gfm":
                    W.rgba("nisar_adds", d, classes_rgba([(adds, "adds")]), dict(group="result", sensor="NISAR L-band",
                           label="NISAR addition: water in the blank", legend=[[HEX(C["adds"]), "NISAR addition"]], default=True))
                    I["layers"].append("nisar_adds")
        I["baselines_missing"] = [k for k, y in (("gfm", 2015), ("dswx", 2023)) if k not in I["baselines"]
                                  and (int(d[:4]) < y or c["sensor"] == "NISAR")]
        images.append(I)
        print(d, I["sensor"], I["flood_km2"], "km²", {k: v["flood_km2"] for k, v in I["baselines"].items()},
              I["optical"] and (I["optical"]["date"], I["optical"]["source"], I["optical"]["cloud_pct"]), flush=True)

    # 3. summary per year
    years = []
    for y in sorted({i["date"][:4] for i in images}):
        yi = [i for i in images if i["date"][:4] == y]
        top = max(yi, key=lambda i: i["flood_km2"])
        years.append(dict(year=int(y), sensor=top["sensor"], max_flood_km2=top["flood_km2"], date=top["date"],
                          n_images=len(yi), flood_season_seen=any(i["date"][5:7] in ("08", "09", "10", "11", "12") for i in yi)))
    wet = [y for y in years if y["flood_season_seen"]]
    old, new = max((y for y in wet if y["sensor"] == "RADARSAT-1"), key=lambda y: y["max_flood_km2"]), \
        max((y for y in wet if y["sensor"] == "NISAR"), key=lambda y: y["max_flood_km2"])
    ev = dict(
        version=2, id=f"{place}/history", kind="history", place=f"{case['name']}, {case['country']}",
        title=f"{case['name']}, {images[0]['date'][:4]}–{images[-1]['date'][:4]}", bbox=list(bbox),
        area_km2=round(float(valid.sum() * px)),
        sampling=dict(min_gap_days=MIN_GAP_DAYS, rule="each year's wettest image, then others ≥ 30 days from the kept ones",
                      candidates=len(cand), kept=len(images)),
        summary=dict(years=years,
                     sentence=f"Same {round(float(valid.sum() * px)):,} km² of delta: flood {old['max_flood_km2']:,.0f} km² on "
                              f"{old['date']} (RADARSAT-1), {new['max_flood_km2']:,.0f} km² on {new['date']} (NISAR).",
                     caveat="Two radars (C-band 1998–2007, L-band 2026) and two methods: compare the pattern, not exact km²."),
        images=images, layers=W.layers,
        method=dict(grid="NISAR GCOV frequency B, 80 m (native); every source resampled onto it before analysis",
                    rs1="RADARSAT-1 HH warped with its GCPs, aligned to NISAR by edges, one threshold per image "
                        "(Otsu on tiles with both river and land)",
                    nisar=f"detect.py v2, thresholds HH {case['open_hh']} / HV {case['open_hv']} dB (calibrated on clear optical days)",
                    flood="water beyond permanent water (dark on ≥ 90 % of NISAR passes); area = pixels × 80 m × 80 m",
                    optical=f"MODIS (250 m) least cloudy day within ± {MODIS_DAYS} d for 2000–2013; HLS (30 m) clearest within ± 5 d for 2026; none before 2000",
                    baselines="GFM (Sentinel-1) exists from 2015, NASA OPERA DSWx-HLS from 2023: only on NISAR dates"),
        sources=[
            dict(name="RADARSAT-1 L1 (EODMS / AWS)", url="https://registry.opendata.aws/radarsat-1/",
                 credit="RADARSAT-1 data © Canadian Space Agency; Open Government Licence – Canada"),
            dict(name="NISAR L2 GCOV", url="https://search.asf.alaska.edu", credit="NASA/JPL-Caltech, ISRO; data via ASF DAAC"),
            dict(name="MODIS Terra / Aqua Corrected Reflectance via NASA GIBS", url="https://earthdata.nasa.gov/gibs",
                 credit="NASA EOSDIS GIBS / LANCE"),
            dict(name="HLS true colour via NASA GIBS", url="https://earthdata.nasa.gov/gibs",
                 credit="NASA EOSDIS GIBS; HLS (NASA / USGS Landsat, ESA Copernicus Sentinel-2)"),
            dict(name="Copernicus EMS Global Flood Monitoring", url="https://global-flood.emergency.copernicus.eu",
                 credit="© European Union, Copernicus Emergency Management Service"),
            dict(name="OPERA DSWx-HLS", url="https://www.jpl.nasa.gov/go/opera", credit="NASA/JPL OPERA; data via PO.DAAC")],
    )
    (folder / "event.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False))
    (folder / "science.md").write_text(SCIENCE.format(title=ev["title"], sentence=ev["summary"]["sentence"], n=len(images)))
    pf = EVENTS_DIR / place / "place.json"
    pl = json.loads(pf.read_text()) if pf.exists() else dict(version=2, id=place, name=case["name"], country=case["country"],
                                                            bbox=list(bbox), floods=[])
    pl["history"] = dict(id="history", first=images[0]["date"], last=images[-1]["date"], n_images=len(images),
                         sensors=sorted({i["sensor"] for i in images}))
    pf.write_text(json.dumps(pl, indent=1, ensure_ascii=False))
    bundle.write_index()
    return ev


SCIENCE = """# {title}: flood history

{sentence}

**Images:** {n}, about one every month or two (each year's wettest kept). RADARSAT-1 (CSA, C-band) 1998–2007,
NISAR (L-band) 2026. Each with our flood map, a photo near the same day (MODIS from 2000, HLS in 2026), and the
official flood maps where they exist (GFM from 2015, NASA DSWx-HLS from 2023: 2026 only).

**Method:** everything on NISAR's 80 m grid. RADARSAT-1: GCP warp, edge alignment, one threshold per image.
NISAR: our detector. Flood = water beyond permanent water.

**Limits:** C-band misses some water under rice that L-band sees; one threshold per image vs a calibrated detector:
compare the pattern (dry vs flood, then vs now), not exact km². Paddies are flooded on purpose; dikes keep some fields
dry. MODIS is 250 m and often cloudy in the wet season. Audit: docs/10-Results.md.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("place", choices=sorted(PLACES))
    build(ap.parse_args(argv).place)


if __name__ == "__main__":
    main()
