"""One recent flood of one place, in the event-folder format v2 (docs/12-Event-folders.md).

    python -m unseen.eventfolder mekong-delta-vietnam            # flood date = wettest NISAR pass
    python -m unseen.eventfolder mekong-delta-vietnam --date 2026-09-23

Writes events/<place>/place.json and events/<place>/<YYYY-MM>-flood/ (event.json, science.md, layers/), and adds the
place to events/index.json ("places"). Event window = flood date ± 30 days; time steps = NISAR passes in it.

Per pass: optical photo (clearest ± 5 d), NISAR HH / HV / RGB / GUNW coherence, the two baselines segmented
(Copernicus GFM ± 2 d; NASA OPERA DSWx-HLS ± 3 d), NISAR water, NISAR addition and the combined map.
Areas: pixels × 80 m × 80 m, where NISAR and the baseline both have data, permanent water removed.
"""
import argparse
import datetime as dt
import json

import numpy as np
from PIL import Image

from . import bundle, gfm, optical
from .auth import session as earthdata_session
from .config import EVENTS_DIR, REPO
from .detect import detect
from .flood import load

PLACES = {
    "mekong-delta-vietnam": dict(
        name="Mekong delta", country="Vietnam", bbox=(105.0, 10.4, 105.6, 11.0),
        stack_key="mekong-delta-vietnam-83-7",        # NISAR stack cache (data/stacks), track 83 frame 7 ascending
        viewer_site="mekong-delta-vietnam-83-7",      # its Explorer site: HLS photos on the same grid
        open_hh=-13.0, open_hv=-18.0,                 # detector thresholds calibrated on clear optical days (that site)
        gfm_bundle="mekong-delta-vietnam"),           # v1 bundle: GFM fallback when the GFM server is down
    "gerd-blue-nile-ethiopia": dict(
        name="GERD reservoir, Blue Nile", country="Ethiopia", bbox=(34.9, 10.2, 35.8, 11.35),
        stack_key="gerd-blue-nile-ethiopia-129-7",    # track 129 frame 7 ascending, 11 dual-pol passes Jun-Nov 2026
        open_hh=-13.0, open_hv=-18.0,                 # Otsu on the 2 Nov 2026 pass: HH -12.4, HV -16.9 dB
        rs1_min_cover=0.7,                            # history: the only RADARSAT-1 scene (9 Jul 1998) covers 74 %
        rs1_flood=False,                              # no lake in 1998: the river/land threshold has no river tiles
        rs1_note="No flood map from RADARSAT-1 here: our threshold is set on tiles holding both permanent water and land, "
                 "and in 1998 (before the dam) today's lake was dry valley, so the split lands on terrain shadows. Picture only.",
        history_limits="Only one RADARSAT-1 scene reaches GERD (9 Jul 1998, ScanSAR, 74 % of the box; the dam site is just "
                       "outside it): a before-the-dam picture, no flood km². The reservoir fills every rainy season, so "
                       "'flood' here = water beyond the lake on ≥ 90 % of NISAR passes, i.e. how far the lake grows. "
                       "No GFM (server down at build time). Audit: docs/10-Results.md."),
}
WINDOW_DAYS, PHOTO_DAYS, GFM_DAYS, DSWX_DAYS = 30, 5, 2, 3

# exact class colours (docs/12 §3a): the site shows them as is, code counts pixels by colour
C = dict(flood=(40, 130, 255, 230), permanent=(10, 58, 140, 200), clouds=(235, 235, 240, 200),
         blank=(140, 140, 150, 170), adds=(255, 154, 46, 245), unknown=(60, 60, 70, 200))
# "cannot see" and "still unknown" are solid greys, not hatched: hatch patterns make PNGs ~3x bigger (20 MB budget)
HEX = lambda c: "#%02x%02x%02x" % c[:3]
D = dt.date.fromisoformat


# ---------- pictures ----------
def classes_rgba(layers):
    """layers: ordered [(mask, key)], later wins; key in C."""
    a = np.zeros(layers[0][0].shape + (4,), np.uint8)
    for m, k in layers:
        a[m] = C[k]
    return a


def grey(a, lo, hi):
    """float array -> uint8 1..255 (0 = no data)."""
    g = np.clip((a - lo) / (hi - lo) * 254 + 1, 1, 255)
    return np.where(np.isfinite(a), g, 0).astype(np.uint8)


class Writer:
    """Writes layers/<layer>_<date>.<png|jpg> in EPSG:4326 and records them in event.json's "layers"."""
    def __init__(self, folder, grid):
        self.dir, self.grid, self.layers = folder / "layers", grid, {}
        self.dir.mkdir(parents=True, exist_ok=True)

    def _add(self, lid, date, img, bounds, ext, meta):
        name = f"{lid}_{date}.{ext}"
        if ext == "jpg":
            img.convert("RGB").save(self.dir / name, quality=72, optimize=True)
        else:
            img.save(self.dir / name, optimize=True)
        lay = self.layers.setdefault(lid, dict(meta, files={}, bounds=bounds))
        lay["files"][date] = f"layers/{name}"

    def rgba(self, lid, date, a, meta, half=False):
        a = a[::2, ::2] if half else a
        g = self.grid if not half else dict(self.grid, x=self.grid["x"][::2], y=self.grid["y"][::2], dx=self.grid["dx"] * 2)
        chans = [bundle.to_wgs84(np.ascontiguousarray(a[..., i]), g) for i in range(4)]
        self._add(lid, date, Image.fromarray(np.dstack([c[0] for c in chans]), "RGBA"), chans[0][1], "png", meta)

    def picture(self, lid, date, rgb_or_grey, meta, half=False):
        """Opaque picture (photo, radar): JPEG. uint8 (H,W) grey or (H,W,3) RGB, 0 = no data (black)."""
        a = rgb_or_grey[::2, ::2] if half else rgb_or_grey
        g = self.grid if not half else dict(self.grid, x=self.grid["x"][::2], y=self.grid["y"][::2], dx=self.grid["dx"] * 2)
        if a.ndim == 2:
            w, b = bundle.to_wgs84(a, g)
            img = Image.fromarray(w, "L")
        else:
            ch = [bundle.to_wgs84(np.ascontiguousarray(a[..., i]), g) for i in range(3)]
            img, b = Image.fromarray(np.dstack([c[0] for c in ch]), "RGB"), ch[0][1]
        self._add(lid, date, img, b, "jpg", meta)


# ---------- baselines on our grid ----------
def gfm_on_grid(case, bbox, date, grid, shape):
    try:
        G = gfm.on_grid(bbox, date, grid, shape, days=GFM_DAYS)
        if G:
            return G
    except Exception as e:  # noqa: BLE001
        print(f"[warn] GFM {date}: {e!r}"[:110])
    from .history import gfm_from_bundle
    return gfm_from_bundle(case.get("gfm_bundle"), date, grid, shape)


def dswx_classes(files, date, grid, shape):
    """Nearest DSWx-HLS day within ± DSWX_DAYS that covers >= 30 % of the box: WTR classes on our grid (nearest)."""
    import rasterio
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    days = sorted({f["date"] for f in files if abs((D(f["date"]) - D(date)).days) <= DSWX_DAYS},
                  key=lambda d: abs((D(d) - D(date)).days))
    for d in days:
        out = np.full(shape, 255, np.uint8)
        for f in (f for f in files if f["date"] == d):
            tmp = np.full(shape, 255, np.uint8)
            with rasterio.open(f["path"]) as s:
                reproject(rasterio.band(s, 1), tmp, dst_transform=from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx),
                          dst_crs=f"EPSG:{grid['epsg']}", resampling=Resampling.nearest, src_nodata=255, dst_nodata=255)
            ok = (tmp != 255) & (out == 255)
            out[ok] = tmp[ok]
        if (out != 255).mean() >= 0.3:
            return d, out
    return None, None


def photo_for(case, date):
    """HLS photo of the Explorer site within ± PHOTO_DAYS with the most clear land: cloud-free fraction (DSWx-HLS)
    × part of the box the swath covers."""
    site = REPO / "site" / "viewer" / "sites" / (case.get("viewer_site") or "-")
    if not (site / "site.json").exists():               # place without an Explorer site: no photos yet
        return None, None, None
    S = json.loads((site / "site.json").read_text())
    clear = {o["date"]: o["clear"] for o in S.get("timeline", {}).get("optical", [])}
    c = []
    for d, f in S.get("photos", {}).items():
        if abs((D(d) - D(date)).days) <= PHOTO_DAYS:
            im = np.array(Image.open(site / f).convert("RGB"))
            cover = float((im.max(-1) > 8).mean())                 # part of the box the swath covers (black = none)
            c.append((clear.get(d, 0) * cover, -abs((D(d) - D(date)).days), d, im, clear.get(d, 0)))
    if not c:
        return None, None, None
    _, _, d, im, cl = max(c, key=lambda x: x[:2])
    return d, im, cl


# ---------- main ----------
def build(place, flood_date=None):
    case = PLACES[place]
    bbox = case["bbox"]
    stack, dates, grid, st = load(bbox, case["stack_key"])
    shape = stack.shape[-2:]
    px = (grid["dx"] / 1000) ** 2
    L = detect(stack, pixel_m=grid["dx"], open_hh=case["open_hh"], open_hv=case["open_hv"])
    perm, valid = L["permanent"], L["valid"]
    wet = [(L["water"][t] | L["canopy"][t]) & ~perm & valid for t in range(len(dates))]
    fd = flood_date or dates[int(np.argmax([w.sum() for w in wet]))]
    w0, w1 = D(fd) - dt.timedelta(days=WINDOW_DAYS), D(fd) + dt.timedelta(days=WINDOW_DAYS)
    idx = [t for t, d in enumerate(dates) if w0 <= D(d) <= w1]
    fid = f"{fd[:7]}-flood"
    folder = EVENTS_DIR / place / fid
    W = Writer(folder, grid)
    print(f"{place}/{fid}: flood date {fd}, window {w0} → {w1}, passes {[dates[t] for t in idx]}")

    # inputs for the whole window
    try:
        og = optical.search(bbox, (w0 - dt.timedelta(days=DSWX_DAYS)).isoformat(), (w1 + dt.timedelta(days=DSWX_DAYS)).isoformat())
        dfiles = optical.download(og, earthdata_session()) if og else []
    except Exception as e:  # noqa: BLE001
        print(f"[warn] DSWx-HLS: {e!r}"[:120]); dfiles = []
    track, frame = (st or {}).get("track"), (st or {}).get("frame")
    vs = REPO / "site/viewer/sites" / (case.get("viewer_site") or "-") / "site.json"
    if track is None and vs.exists():
        stk = json.loads(vs.read_text()).get("stack", {})
        track, frame = stk.get("track"), stk.get("frame")
    try:
        from .fused import coherence
        coh = coherence(bbox, grid, track, frame, [dates[t] for t in idx])
    except Exception as e:  # noqa: BLE001
        print(f"[warn] coherence: {e!r}"[:120]); coh = [None] * len(idx)

    hh = 10 * np.log10(np.where(stack[:, 0] > 0, stack[:, 0], np.nan))
    hv = 10 * np.log10(np.where(stack[:, 1] > 0, stack[:, 1], np.nan))
    nmask = ~valid
    W.rgba("nisar_mask", dates[idx[0]], classes_rgba([(nmask, "blank")]),
           dict(group="radar", sensor="NISAR L-band", label="NISAR can't measure (layover, shadow, no data)",
                legend=[[HEX(C["blank"]), "NISAR can't measure"]], default=False, once=True))
    try:
        from .landcover import on_grid as lc_on_grid
        lc = lc_on_grid(grid, bbox, key=case["stack_key"])
    except Exception as e:  # noqa: BLE001
        print(f"[warn] land cover: {e!r}"[:120]); lc = None
    if lc is not None:
        pal = {10: (0, 100, 0), 20: (255, 187, 34), 30: (255, 255, 76), 40: (240, 150, 255), 50: (250, 0, 0),
               60: (180, 180, 180), 80: (0, 100, 200), 90: (0, 150, 160), 95: (0, 207, 117)}
        a = np.zeros(shape + (4,), np.uint8)
        for k, c in pal.items():
            a[lc == k] = (*c, 170)
        W.rgba("landcover", dates[idx[0]], a, dict(group="context", sensor="ESA WorldCover 2021", label="Land cover",
               legend=[[HEX(pal[k]), n] for k, n in ((10, "forest"), (40, "cropland"), (50, "built-up"), (80, "water"),
                                                    (90, "wetland"))], default=False, once=True))

    passes = []
    for j, t in enumerate(idx):
        d, w = dates[t], wet[t]
        P = dict(date=d, matched={}, baselines={}, layers=[])
        # optical photo
        pd_, ph, clear = photo_for(case, d)
        if ph is not None:
            W.picture("photo", pd_, ph, dict(group="optical", sensor="HLS (Landsat / Sentinel-2) via NASA GIBS",
                                             label="Optical photo (true colour)", legend=None, default=False))
            P["matched"]["photo"], P["clouds_pct"] = pd_, round(100 * (1 - clear))
            P["layers"].append("photo")
        # NISAR radar pictures
        rgb = np.dstack([grey(hh[t], -25, 0), grey(hv[t], -32, -8), grey(hh[t] - hv[t], 0, 15)])
        rgb[~valid] = 0
        W.picture("nisar_rgb", d, rgb, dict(group="radar", sensor="NISAR L-band GCOV",
                  label="NISAR radar (R = HH, G = HV, B = HH/HV)", legend=None, default=True))
        W.picture("nisar_hh", d, grey(hh[t], -25, 0), dict(group="radar", sensor="NISAR L-band GCOV",
                  label="NISAR HH (−25…0 dB)", legend=None, default=False), half=True)
        W.picture("nisar_hv", d, grey(hv[t], -32, -8), dict(group="radar", sensor="NISAR L-band GCOV",
                  label="NISAR HV (−32…−8 dB)", legend=None, default=False), half=True)
        P["layers"] += ["nisar_rgb", "nisar_hh", "nisar_hv"]
        if coh[j] is not None:
            W.picture("nisar_coh", d, grey(coh[j], 0, 1), dict(group="radar", sensor="NISAR L-band GUNW",
                      label="NISAR coherence (12-day pairs, 0…1)", legend=None, default=False), half=True)
            P["layers"].append("nisar_coh")
            P["matched"]["coh"] = "12-day GUNW pairs that include this pass"
        # baselines
        base = {}
        G = gfm_on_grid(case, bbox, d, grid, shape)
        if G:
            seen = G["seen"] & valid
            base["gfm"] = dict(date=G["date"], seen=seen, flood=G["flood"] & ~perm & seen,
                               clouds=np.zeros(shape, bool), veg=G["excluded"] & ~perm & seen & ~G["flood"])
        dd, cls = dswx_classes(dfiles, d, grid, shape) if dfiles else (None, None)
        if cls is not None:
            seen = (cls != 255) & valid
            ocean = cls == 254
            base["dswx"] = dict(date=dd, seen=seen & ~ocean, flood=np.isin(cls, (1, 2)) & ~perm & seen & ~ocean,
                                clouds=np.isin(cls, (252, 253)) & ~perm & seen, veg=np.zeros(shape, bool))
        for k, B in base.items():
            lid = f"{k}_classes"
            blank = B["clouds"] | B["veg"]
            W.rgba(lid, B["date"], classes_rgba([(perm & B["seen"], "permanent"), (B["clouds"], "clouds"),
                                                 (B["veg"], "blank"), (B["flood"], "flood")]),
                   dict(group="baseline", sensor="Sentinel-1 (Copernicus GFM)" if k == "gfm" else "OPERA DSWx-HLS (NASA)",
                        label="Official flood map (GFM)" if k == "gfm" else "NASA flood map (OPERA DSWx-HLS)",
                        legend=[[HEX(C["flood"]), "flood"], [HEX(C["permanent"]), "permanent water"]]
                        + ([[HEX(C["blank"]), "cannot see here (vegetation, city, radar shadow)"]] if k == "gfm"
                           else [[HEX(C["clouds"]), "cannot see here (clouds)"]]),
                        default=k == "gfm"))
            P["matched"][k] = B["date"]
            P["layers"].append(lid)
            adds = w & blank
            unknown = blank & nmask
            fl = float(B["flood"].sum() * px)
            P["baselines"][k] = dict(
                flood_km2=round(fl, 1), cannot_see_km2=round(float(blank.sum() * px), 1),
                cannot_see_clouds_km2=round(float(B["clouds"].sum() * px), 1),
                cannot_see_vegetation_km2=round(float(B["veg"].sum() * px), 1),
                nisar_adds_km2=round(float(adds.sum() * px), 1),
                improvement_pct=round(100 * float(adds.sum() * px) / fl) if fl >= 5 else None,
                still_unknown_km2=round(float(unknown.sum() * px), 1))
            B["adds"], B["unknown"] = adds, unknown
        # our result
        W.rgba("nisar_water", d, classes_rgba([(w, "flood")]), dict(group="result", sensor="NISAR L-band",
               label="NISAR flood (our detector)", legend=[[HEX(C["flood"]), "flood seen by NISAR"]], default=False))
        P["layers"].append("nisar_water")
        P["nisar"] = dict(water_km2=round(float(w.sum() * px), 1), valid_pct=round(100 * float(valid.mean())))
        main = "gfm" if "gfm" in base else next(iter(base), None)
        if main:
            B = base[main]
            W.rgba("nisar_adds", d, classes_rgba([(B["adds"], "adds")]), dict(group="result", sensor="NISAR L-band",
                   label="NISAR addition: water in the blank", legend=[[HEX(C["adds"]), "NISAR addition: water in the blank"]],
                   default=True))
            W.rgba("combined", d, classes_rgba([(perm & B["seen"], "permanent"), (B["flood"], "flood"),
                                               (B["adds"], "adds"), (B["unknown"], "unknown")]),
                   dict(group="result", sensor="Baseline + NISAR", label=f"Combined flood map ({main.upper()} + NISAR)",
                        legend=[[HEX(C["flood"]), "flood in the official map"], [HEX(C["adds"]), "NISAR addition"],
                                [HEX(C["unknown"]), "still unknown"], [HEX(C["permanent"]), "permanent water"]], default=False))
            P["layers"] += ["nisar_adds", "combined"]
            P["main_baseline"] = main
        passes.append(P)
        print(d, {k: (v["flood_km2"], v["nisar_adds_km2"], v["improvement_pct"]) for k, v in P["baselines"].items()},
              "photo", P["matched"].get("photo"), "coh", coh[j] is not None, flush=True)

    # summary: the wettest pass, against the main baseline (GFM if present, else DSWx)
    withb = [p for p in passes if p["baselines"]]
    sp = next(p for p in withb if p["date"] == fd) if any(p["date"] == fd for p in withb) else \
        max(withb, key=lambda p: p["nisar"]["water_km2"])
    mb = "gfm" if "gfm" in sp["baselines"] else next(iter(sp["baselines"]))
    s = sp["baselines"][mb]
    nice = dict(gfm="the official flood map (Copernicus GFM)", dswx="NASA's flood map (OPERA DSWx-HLS)")[mb]
    summary = dict(pass_date=sp["date"], baseline=mb, baseline_date=sp["matched"][mb],
                   baseline_flood_km2=s["flood_km2"], nisar_adds_km2=s["nisar_adds_km2"],
                   improvement_pct=s["improvement_pct"], cannot_see_km2=s["cannot_see_km2"],
                   cannot_see_clouds_km2=s["cannot_see_clouds_km2"],
                   cannot_see_vegetation_km2=s["cannot_see_vegetation_km2"], still_unknown_km2=s["still_unknown_km2"],
                   nisar_water_km2=sp["nisar"]["water_km2"],
                   sentence=f"On {sp['date']}, NISAR adds {s['nisar_adds_km2']:,.0f} km² of flood "
                            f"(+{s['improvement_pct']}%) where {nice} cannot see.")
    ev = dict(
        version=2, id=f"{place}/{fid}", place=f"{case['name']}, {case['country']}",
        title=f"{case['name']} flood, {D(fd).strftime('%b %Y')}", flood_date=fd,
        window=dict(start=w0.isoformat(), end=w1.isoformat(), days_before=WINDOW_DAYS, days_after=WINDOW_DAYS),
        bbox=list(bbox), area_km2=round(float(valid.sum() * px)), baselines=sorted({k for p in passes for k in p["baselines"]}),
        summary=summary, passes=passes, layers=W.layers,
        method=dict(detector="detect.py v2 (open water + water under vegetation, HH/HV), thresholds calibrated on clear "
                             f"optical days: HH {case['open_hh']} / HV {case['open_hv']} dB",
                    pixel_m=grid["dx"], permanent_water="dark on ≥ 90 % of NISAR passes",
                    matching=dict(photo_days=PHOTO_DAYS, gfm_days=GFM_DAYS, dswx_days=DSWX_DAYS),
                    nisar=dict(track=track, frame=frame, product="L2 GCOV (HH, HV) + L2 GUNW coherence"),
                    improvement="100 × NISAR addition / baseline flood (null if baseline flood < 5 km²)",
                    still_unknown="baseline 'cannot see' where NISAR can't measure either (layover, shadow, no data)"),
        sources=[
            dict(name="NISAR L2 GCOV + GUNW", url="https://search.asf.alaska.edu", credit="NASA/JPL-Caltech, ISRO; data via ASF DAAC"),
            dict(name="Copernicus EMS Global Flood Monitoring", url="https://global-flood.emergency.copernicus.eu",
                 credit="© European Union, Copernicus Emergency Management Service"),
            dict(name="OPERA DSWx-HLS", url="https://www.jpl.nasa.gov/go/opera", credit="NASA/JPL OPERA; data via PO.DAAC"),
            dict(name="HLS true colour via NASA GIBS", url="https://earthdata.nasa.gov/gibs",
                 credit="NASA EOSDIS GIBS; HLS (NASA / USGS Landsat, ESA Copernicus Sentinel-2)"),
            dict(name="ESA WorldCover 2021", url="https://esa-worldcover.org", credit="© ESA WorldCover project 2021, CC BY 4.0")],
    )
    (folder / "event.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False))
    (folder / "science.md").write_text(SCIENCE.format(**summary, title=ev["title"], start=w0, end=w1, n=len(passes)))
    pl = dict(version=2, id=place, name=case["name"], country=case["country"], bbox=list(bbox),
              floods=[dict(id=fid, flood_date=fd, title=ev["title"], baseline=mb,
                           improvement_pct=summary["improvement_pct"], nisar_adds_km2=summary["nisar_adds_km2"],
                           baseline_flood_km2=summary["baseline_flood_km2"])],
              history=None)
    pf = EVENTS_DIR / place / "place.json"
    if pf.exists():                                       # keep other floods / history already listed
        old = json.loads(pf.read_text())
        pl["floods"] = sorted([f for f in old.get("floods", []) if f["id"] != fid] + pl["floods"], key=lambda f: f["flood_date"])
        pl["history"] = old.get("history")
    pf.write_text(json.dumps(pl, indent=1, ensure_ascii=False))
    bundle.write_index()
    return ev


SCIENCE = """# {title}

{sentence}

**Window:** {start} → {end} (flood date ± 30 days), {n} NISAR passes, every 12 days.

**Baselines:** Copernicus GFM (Sentinel-1; "cannot see" = its exclusion mask: dense vegetation, cities, radar shadow)
and NASA OPERA DSWx-HLS (optical; "cannot see" = clouds). Matched to each pass: GFM ± 2 d, DSWx ± 3 d, photo ± 5 d.

**Method:** NISAR L-band HH + HV (GCOV): open water + water under vegetation, permanent water removed
(`pipeline/unseen/detect.py`). NISAR addition = NISAR water inside the baseline's "cannot see". Improvement % =
NISAR addition / baseline flood. Area = pixels × 80 m × 80 m.

**Limits:** a NISAR addition is a candidate, not proven flood; paddies are flooded on purpose in season; numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("place", choices=sorted(PLACES))
    ap.add_argument("--date", help="flood date YYYY-MM-DD (default: wettest NISAR pass)")
    a = ap.parse_args(argv)
    build(a.place, a.date)


if __name__ == "__main__":
    main()
