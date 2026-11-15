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

DETECTOR = None                                           # --detector: overrides every place (default v3)

PLACES = {
    "mekong-delta-vietnam": dict(
        name="Mekong delta", country="Vietnam", bbox=(105.0, 10.4, 105.6, 11.0),
        stack_key="mekong-delta-vietnam-83-7",        # NISAR stack cache (data/stacks), track 83 frame 7 ascending
        viewer_site="mekong-delta-vietnam-83-7",      # its Explorer site: HLS photos on the same grid
        open_hh=-13.0, open_hv=-18.0,                 # detector thresholds calibrated on clear optical days (that site)
        gfm_bundle="mekong-delta-vietnam"),           # v1 bundle: GFM fallback when the GFM server is down
    "tonle-sap-flood-pulse-2026": dict(
        name="Tonle Sap", country="Cambodia", bbox=(103.6, 12.3, 104.7, 13.3),
        stack_key="tonle-sap-flood-pulse-2026-83-8",  # track 83 frame 8 ascending
        viewer_site="tonle-sap-flood-pulse-2026-83-8",
        open_hh=-14.0, open_hv=-19.0,                 # that site's calibration on clear optical days
        gfm_bundle="tonle-sap-flood-pulse-2026"),
    "inner-niger-delta-mali": dict(
        name="Inner Niger Delta", country="Mali", bbox=(-4.6, 14.6, -4.0, 15.2),
        stack_key="inner-niger-delta-mali-145-9",     # track 145 frame 9 ascending
        viewer_site="inner-niger-delta-mali-145-9",
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults: that site's calibration was not used (too few clear days)
        gfm_bundle="inner-niger-delta-mali"),
    "congo-cuvette-centrale": dict(
        name="Congo basin (Cuvette Centrale)", country="Rep. of Congo", bbox=(17.3, 0.2, 17.9, 0.8),
        stack_key="congo-cuvette-centrale-101-2",     # track 101 frame 2 ascending
        viewer_site="congo-cuvette-centrale-101-2",
        open_hh=-13.5, open_hv=-18.5,                 # that site's calibration on clear optical days
        gfm_bundle="congo-cuvette-centrale"),
    "amazon-varzea-mamiraua": dict(
        name="Amazon várzea (Mamirauá)", country="Brazil", bbox=(-65.2, -3.3, -64.6, -2.7),
        stack_key="amazon-varzea-mamiraua",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-11.0, open_hv=-16.0,                 # v1 bundle's calibration on clear optical days
        gfm_bundle="amazon-varzea-mamiraua"),
    "assam-brahmaputra": dict(
        name="Brahmaputra, Assam", country="India", bbox=(92.2, 26.3, 92.8, 26.9),
        stack_key="assam-brahmaputra",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-13.0, open_hv=-18.0,                 # v1 bundle's calibration on clear optical days
        gfm_bundle="assam-brahmaputra"),
    "atchafalaya-basin": dict(
        name="Atchafalaya Basin", country="USA", bbox=(-91.6, 30.0, -91.2, 30.5),
        stack_key="atchafalaya-basin",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults (no calibration in the v1 bundle)
        gfm_bundle="atchafalaya-basin"),
    "flood-in-china-2026": dict(
        name="Hubei floods", country="China", bbox=(110.472, 30.428, 111.472, 31.228),
        stack_key="flood-in-china-2026",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-11.0, open_hv=-16.0,                 # v1 bundle's calibration on clear optical days
        gfm_bundle="flood-in-china-2026"),
    "flood-in-nepal-2026": dict(
        name="Nepal floods", country="Nepal", bbox=(85.22, 26.9, 85.44, 27.11),     # 15.11: cut to the flooded plain (was 84.865, 26.895, 85.865, 27.695)
        stack_key="flood-in-nepal-2026-plain",              # new key: the old box's cached stack must not be reused
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults (no calibration in the v1 bundle)
        flood_months=range(6, 11),                    # history: monsoon flood season Jun–Oct
        gfm_bundle="flood-in-nepal-2026"),
    "flood-india-2026-08": dict(
        name="Tamil Nadu floods", country="India", bbox=(78.11, 10.932, 79.11, 11.732),
        stack_key="flood-india-2026-08",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults (no calibration in the v1 bundle)
        gfm_bundle="flood-india-2026-08"),
    "irrawaddy-delta-myanmar": dict(
        name="Irrawaddy delta", country="Myanmar", bbox=(95.0, 16.3, 95.6, 16.9),
        stack_key="irrawaddy-delta-myanmar",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-11.0, open_hv=-16.0,                 # v1 bundle's calibration on clear optical days
        gfm_bundle="irrawaddy-delta-myanmar"),
    "likouala-flood-congo-2026": dict(
        name="Likouala floods", country="Rep. of Congo", bbox=(17.6, 1.3, 18.2, 1.9),
        stack_key="likouala-flood-congo-2026",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-11.0, open_hv=-16.0,                 # v1 bundle's calibration on clear optical days
        gfm_bundle="likouala-flood-congo-2026"),
    "okavango-delta": dict(
        name="Okavango Delta", country="Botswana", bbox=(22.6, -19.6, 23.2, -19.0),
        stack_key="okavango-delta",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults (no calibration in the v1 bundle)
        gfm_bundle="okavango-delta"),
    "pantanal-brazil": dict(
        name="Pantanal", country="Brazil", bbox=(-57.4, -18.8, -56.8, -18.2),
        stack_key="pantanal-brazil",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults (no calibration in the v1 bundle)
        gfm_bundle="pantanal-brazil"),
    "sudd-wetland-south-sudan": dict(
        name="Sudd wetland", country="South Sudan", bbox=(30.3, 7.0, 30.9, 7.6),
        stack_key="sudd-wetland-south-sudan",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-17.0, open_hv=-24.0,                 # detect.py defaults (no calibration in the v1 bundle)
        gfm_bundle="sudd-wetland-south-sudan"),
    "sylhet-haor-bangladesh": dict(
        name="Sylhet haor", country="Bangladesh", bbox=(91.1, 24.4, 91.7, 25.0),
        stack_key="sylhet-haor-bangladesh",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-12.0, open_hv=-21.0,                 # v1 bundle's calibration on clear optical days
        flood_months=range(5, 11),                    # history: flash floods (May) + monsoon (Jun–Oct)
        gfm_bundle="sylhet-haor-bangladesh"),
    "thailand-floods-bang-pakong-2026": dict(
        name="Bang Pakong floods", country="Thailand", bbox=(100.7, 13.41, 101.3, 13.89),
        stack_key="thailand-floods-bang-pakong-2026",                    # NISAR stack: best one covering the box (searched on first run)
        open_hh=-11.0, open_hv=-18.0,                 # v1 bundle's calibration on clear optical days
        gfm_bundle="thailand-floods-bang-pakong-2026"),
    "peace-athabasca-delta": dict(
        name="Peace-Athabasca Delta", country="Canada", bbox=(-111.8, 58.3, -111.0, 58.9),
        stack_key="peace-athabasca-delta-143-59",     # track 143 frame 59 descending
        viewer_site="peace-athabasca-delta-143-59",
        open_hh=-12.0, open_hv=-18.0,                 # that site's calibration on 6 clear optical days (F1 0.80)
        validation="rcm",                             # independent check: Canada's RCM radar (CSA) near each pass
        flood_limits="shallow delta lakes roughened by wind are not dark on ≥ 90 % of passes, so part of them counts as "
                     "flood here (in NISAR and in the baseline alike);",
        flood_months=range(5, 9),                     # flood season: spring ice-jam + summer high water (May–Aug)
        dry_dates=["2026-09-04", "2026-09-16"],       # v3 dry reference: first passes after the flood season (the default,
                                                      # the first two passes, falls in June-July high water here)
        rs1_months=range(5, 10),                      # history: May–Sep only (ice, snow, freeze-up fool a dark-water threshold)
        history_limits="C-band misses water under willow and sedge that L-band sees; one threshold per image vs a "
                       "calibrated detector: compare the pattern, not exact km². RADARSAT-1 May–Sep only (ice and freeze-up "
                       "from Oct). MODIS is 250 m. Audit: docs/10-Results.md."),
    "dead-sea-israel": dict(
        name="Dead Sea (validation)", country="Israel", bbox=(35.37, 30.97, 35.52, 31.30),
        stack_key="dead-sea-israel",                  # NISAR stack: best one covering the box (track 151 descending)
        open_hh=-17.0, open_hv=-24.0,                 # handbook / detect defaults: no optical calibration here
        detector="v3",                                # fused v3 (was doc33, flood_nasa.final(), until 15.11.26)
        kind="validation",                            # not a flood story: a clear-sky check against the official maps
        validation=["lance", "gfm"],                  # + DSWx (always when present): NISAR water vs each map where it can see
        flood_limits="validation site, not a flood: desert valley floor (open water, salt ponds, bare shore), no "
                     "vegetation, almost always cloud-free;"),
    "sylhet-haor-validation": dict(
        name="Sylhet haor (validation)", country="Bangladesh", bbox=(91.1, 24.4, 91.7, 25.0),
        stack_key="sylhet-haor-validation",           # NISAR track 69 frame 14 (same stack as the Sylhet flood site)
        open_hh=-12.0, open_hv=-21.0,                 # that site's calibration on clear optical days
        detector="doc33", no_map=(50, 60),            # flood_nasa.final(); handbook mask without cropland: the haor is flooded farmland
        kind="validation",                            # a check: GFM "cannot see" ~3 % of the box, NASA LANCE cloud-free
        validation=["gfm", "lance"],                  # + DSWx when it downloads
        flood_limits="validation site: seasonal haor wetland, mostly flooded farmland, little tree cover; GFM covers about "
                     "half the box (its Sentinel-1 scene), so scores are where GFM sees;"),
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
WINDOW_DAYS, PHOTO_DAYS, GFM_DAYS, DSWX_DAYS, RCM_DAYS = 30, 5, 2, 3, 3

# exact class colours (docs/12 §3a): the site shows them as is, code counts pixels by colour
C = dict(flood=(40, 130, 255, 230), permanent=(10, 58, 140, 200), clouds=(235, 235, 240, 200),
         blank=(140, 140, 150, 170), adds=(255, 154, 46, 245), unknown=(60, 60, 70, 200),
         rcm=(58, 160, 255, 230), both=(46, 204, 113, 235), nisar_only=(40, 130, 255, 235), rcm_only=(255, 215, 0, 235))
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
    S = json.loads((site / "site.json").read_text(encoding="utf-8"))
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


def compare(a, b, ok):
    """Two water masks where both see: agreement % (all pixels), IoU and F1 (water), km² of each."""
    a, b = a & ok, b & ok
    tp, fp, fn = float((a & b).sum()), float((a & ~b).sum()), float((~a & b).sum())
    return dict(compared_pct=round(100 * float(ok.mean())), agreement_pct=round(100 * float((a == b)[ok].mean()), 1),
                iou=round(tp / (tp + fp + fn), 2) if tp + fp + fn else None,
                f1=round(2 * tp / (2 * tp + fp + fn), 2) if tp + fp + fn else None,
                precision=round(tp / (tp + fp), 2) if tp + fp else None, recall=round(tp / (tp + fn), 2) if tp + fn else None)


# ---------- independent check: RCM (Canada's C-band radar) ----------
def rcm_check(feats, date, grid, shape, perm, valid, nisar_open):
    """RCM day within ± RCM_DAYS of the pass that covers most of the box (ties: closest; ≥ 30 % needed): open water
    from its RL band (one Otsu threshold per image, tiles with both water and land, as for RADARSAT-1), compared with
    NISAR open water (incl. permanent water) where both see. C-band can't see water under trees, so NISAR's
    water-under-vegetation is left out of the comparison."""
    from scipy.ndimage import median_filter
    from . import rcm
    from .history import split_threshold
    day = lambda f: f["properties"]["datetime"][:10]
    best = None
    for d in sorted({day(f) for f in feats if abs((D(day(f)) - D(date)).days) <= RCM_DAYS}, key=lambda d: abs((D(d) - D(date)).days)):
        b = rcm.on_grid([f for f in feats if day(f) == d], grid, shape, bands=("rl",))["rl"]
        cover = float((np.isfinite(b) & valid).mean())
        if cover >= 0.3 and (best is None or cover > best[0] + 0.05):
            best = (cover, d, b)
    if best is None:
        return None
    _, rd, b = best
    db = 10 * np.log10(np.where(b > 0, b, np.nan))
    ok = np.isfinite(db) & valid
    db = median_filter(np.nan_to_num(db, nan=np.nanmedian(db)), 3) * np.where(np.isfinite(db), 1, np.nan)
    thr, ntiles = split_threshold(db, perm)
    rw, nw = (db < thr) & ok, nisar_open & ok
    both, n_only, r_only = rw & nw, nw & ~rw, rw & ~nw
    u = float((rw | nw).sum())
    tp, fp, fn = float(both.sum()), float(n_only.sum()), float(r_only.sum())
    return dict(date=rd, db=db, ok=ok, water=rw, both=both, n_only=n_only, r_only=r_only, stats=dict(
        threshold_db=round(float(thr), 1), split_tiles=ntiles, compared_pct=round(100 * float(ok.mean())),
        agreement_pct=round(100 * float((rw == nw)[ok].mean()), 1), iou=round(tp / u, 2) if u else None,
        f1=round(2 * tp / (2 * tp + fp + fn), 2) if tp + fp + fn else None))


# ---------- main ----------
REF = dict(lance=("NASA LANCE (VIIRS / MODIS), 2-day composite", "NASA's LANCE flood map"),
           gfm=("Sentinel-1 (Copernicus GFM)", "Copernicus GFM"))


def viirs_photo(W, bbox, date):
    """VIIRS true colour of the pass day (NASA GIBS, ~375 m) for places without an Explorer site. Returns its date."""
    import shutil
    import tempfile
    from . import lance
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False).name
    try:
        lay = lance.truecolor(bbox, date, tmp, width=512)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] VIIRS photo {date}: {e!r}"[:110]); return None
    name = f"photo_{date}.jpg"
    shutil.move(tmp, W.dir / name)
    lp = W.layers.setdefault("photo", dict(group="optical", sensor=f"{lay.split('_')[0]} true colour via NASA GIBS",
                                           label="Optical photo (true colour, same day)", legend=None, default=False,
                                           files={}, bounds=[[bbox[1], bbox[0]], [bbox[3], bbox[2]]]))
    lp["files"][date] = f"layers/{name}"
    return date


def build(place, flood_date=None):
    case = PLACES[place]
    bbox = case["bbox"]
    stack, dates, grid, st = load(bbox, case["stack_key"])
    shape = stack.shape[-2:]
    px = (grid["dx"] / 1000) ** 2
    det = DETECTOR or case.get("detector") or "v3"
    track, frame = (st or {}).get("track"), (st or {}).get("frame")
    vs = REPO / "site/viewer/sites" / (case.get("viewer_site") or "-") / "site.json"
    if track is None and vs.exists():
        stk = json.loads(vs.read_text(encoding="utf-8")).get("stack", {})
        track, frame = stk.get("track"), stk.get("frame")
    qa_dropped = []
    if det == "v3":                                       # fused v3 (fused.py, docs/07 §2b): the site's detector
        from .fused import detect_fused, qa
        stack, dates, qa_dropped = qa(stack, dates)
        L = detect_fused(stack, dates, grid, bbox, track=track, frame=frame, dry_dates=case.get("dry_dates"))
    else:
        L = detect(stack, pixel_m=grid["dx"], open_hh=case["open_hh"], open_hv=case["open_hv"])
    perm, valid = L["permanent"], L["valid"]
    wet = [(L["water"][t] | L["canopy"][t]) & ~perm & valid for t in range(len(dates))]
    vals = case.get("validation") or []
    vals = [vals] if isinstance(vals, str) else list(vals)
    nopen_all = None                                      # doc33: NISAR water incl. permanent, for the checks
    if det == "doc33":                                   # NISAR handbook §6.4 + confidence + handbook mask (flood_nasa.final)
        from . import dem
        from .detect import _db
        from .flood_nasa import final
        from .landcover import on_grid as lc_on_grid
        try:
            lc0 = lc_on_grid(grid, bbox, key=case["stack_key"])
        except Exception as e:  # noqa: BLE001
            print(f"[warn] land cover: {e!r}"[:120]); lc0 = None
        try:
            z0 = dem.on_grid(grid, bbox, key=case["stack_key"])
        except Exception as e:  # noqa: BLE001
            print(f"[warn] DEM: {e!r}"[:120]); z0 = None
        F = final(stack, dates, lc0, z0, grid["dx"], case["open_hh"], **(dict(no_map=case["no_map"]) if "no_map" in case else {}))
        _, _, valid = _db(stack)
        perm = F["permanent"]
        nopen_all = [F["inundated"][t] & valid for t in range(len(dates))]
        wet = [nopen_all[t] & ~perm for t in range(len(dates))]
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
    try:
        from .fused import coherence
        coh = coherence(bbox, grid, track, frame, [dates[t] for t in idx])
    except Exception as e:  # noqa: BLE001
        print(f"[warn] coherence: {e!r}"[:120]); coh = [None] * len(idx)

    rfeats = []
    if "rcm" in vals:
        try:
            from . import rcm
            rfeats = rcm.search(bbox, (w0 - dt.timedelta(days=RCM_DAYS)).isoformat(), (w1 + dt.timedelta(days=RCM_DAYS)).isoformat())
        except Exception as e:  # noqa: BLE001
            print(f"[warn] RCM: {e!r}"[:120])

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
        if ph is None and case.get("kind") == "validation":    # no Explorer site: VIIRS true colour of the day
            vt = viirs_photo(W, bbox, d)
            if vt:
                P["matched"]["photo"] = vt
                P["layers"].append("photo")
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
                               clouds=np.zeros(shape, bool), veg=G["excluded"] & ~perm & seen & ~G["flood"],
                               water=G["water"] if G.get("has_water") else None, clear=seen & ~G["excluded"])
        dd, cls = dswx_classes(dfiles, d, grid, shape) if dfiles else (None, None)
        if cls is not None:
            seen = (cls != 255) & valid
            ocean = cls == 254
            base["dswx"] = dict(date=dd, seen=seen & ~ocean, flood=np.isin(cls, (1, 2)) & ~perm & seen & ~ocean,
                                clouds=np.isin(cls, (252, 253)) & ~perm & seen, veg=np.zeros(shape, bool),
                                water=np.isin(cls, (1, 2)) & seen & ~ocean,                      # incl. permanent water
                                clear=seen & ~ocean & ~np.isin(cls, (252, 253)))                 # DSWx sees: no cloud
        nopen = L["water"][t] & valid                      # NISAR open water incl. permanent (what C-band / optical also see)
        if nopen_all is not None:
            nopen = nopen_all[t]
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
        # independent check (RCM): open water, same grid, near the same day
        R = None
        if rfeats:
            try:
                R = rcm_check(rfeats, d, grid, shape, perm, valid, nopen)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] RCM {d}: {e!r}"[:120])
        if R:
            W.rgba("rcm_water", R["date"], classes_rgba([(R["water"], "rcm")]), dict(group="validation",
                   sensor="RCM C-band compact-pol (CSA)", label="Water seen by Canada's RCM radar (our analysis)",
                   legend=[[HEX(C["rcm"]), "open water (RCM)"]], default=False))
            W.rgba("agreement", d, classes_rgba([(R["both"], "both"), (R["n_only"], "nisar_only"), (R["r_only"], "rcm_only")]),
                   dict(group="validation", sensor="NISAR + RCM", label="NISAR vs RCM: open water",
                        legend=[[HEX(C["both"]), "both see water"], [HEX(C["nisar_only"]), "NISAR only"],
                                [HEX(C["rcm_only"]), "RCM only"]], default=False))
            P["matched"]["rcm"] = R["date"]
            P["validation"] = dict(rcm=dict(R["stats"], nisar_open_km2=round(float((R["both"] | R["n_only"]).sum() * px), 1),
                                            rcm_water_km2=round(float(R["water"].sum() * px), 1)))
            W.picture("rcm_radar", R["date"], grey(R["db"], -25, -5), dict(group="validation", sensor="RCM C-band compact-pol (CSA)",
                      label="RCM radar (RL, −25…−5 dB; dark = water)", legend=None, default=False), half=True)
            P["layers"] += ["rcm_water", "agreement", "rcm_radar"]
        # NISAR open water (the mask every check uses) + NASA DSWx water, for the swipe and the agreement numbers
        lw = None
        if "lance" in vals:                                # NASA LANCE (VIIRS / MODIS) flood map, 2-day composite
            try:
                from . import lance
                lw = lance.composite(bbox, d, grid, shape)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] LANCE {d}: {e!r}"[:120])
        gw = base["gfm"] if "gfm" in vals and "gfm" in base and base["gfm"].get("water") is not None else None
        if R or "dswx" in base or lw is not None or gw is not None:
            W.rgba("nisar_open", d, classes_rgba([(nopen, "nisar_only")]), dict(group="validation", sensor="NISAR L-band",
                   label="NISAR open water (incl. permanent)", legend=[[HEX(C["nisar_only"]), "open water (NISAR)"]], default=False))
            P["layers"].append("nisar_open")
        if "dswx" in base:
            B = base["dswx"]
            W.rgba("dswx_water", B["date"], classes_rgba([(B["clouds"], "clouds"), (B["water"], "rcm")]), dict(group="validation",
                   sensor="OPERA DSWx-HLS (NASA)", label="Water in NASA's map (DSWx, incl. permanent)",
                   legend=[[HEX(C["rcm"]), "open water (NASA DSWx)"], [HEX(C["clouds"]), "clouds"]], default=False))
            P["layers"].append("dswx_water")
            ok = B["clear"] & valid
            if ok.mean() >= 0.3:
                P.setdefault("validation", {})["dswx"] = dict(compare(nopen, B["water"], ok), date=B["date"])
                if case.get("kind") == "validation":       # agreement map: green both, blue NISAR only, yellow NASA only
                    W.rgba("agreement_dswx", d, classes_rgba([(nopen & B["water"] & ok, "both"), (nopen & ~B["water"] & ok, "nisar_only"),
                                                              (~nopen & B["water"] & ok, "rcm_only")]),
                           dict(group="validation", sensor="NISAR + OPERA DSWx-HLS", label="NISAR vs NASA DSWx: water",
                                legend=[[HEX(C["both"]), "both see water"], [HEX(C["nisar_only"]), "NISAR only"],
                                        [HEX(C["rcm_only"]), "NASA only"]], default=False))
                    P["layers"].append("agreement_dswx")
                if R:
                    P["validation"]["rcm_vs_dswx"] = compare(R["water"], B["water"], ok & R["ok"])
        for k, X in (("lance", lw), ("gfm", gw)):
            if X is None:
                continue
            ok = (X["seen"] if k == "lance" else X["clear"]) & valid
            W.rgba(f"{k}_water", X["date"], classes_rgba([(X["water"] & ok, "rcm")]), dict(group="validation",
                   sensor=REF[k][0], label=f"Water in {REF[k][1]} (incl. permanent, where it can see)",
                   legend=[[HEX(C["rcm"]), f"water ({REF[k][1]})"]], default=False))
            P["layers"].append(f"{k}_water")
            P["matched"][k] = X["date"]
            if ok.mean() >= 0.3:
                P.setdefault("validation", {})[k] = dict(compare(nopen, X["water"], ok), date=X["date"])
                if case.get("kind") == "validation":       # agreement map: green both, blue NISAR only, yellow map only
                    W.rgba(f"agreement_{k}", d, classes_rgba([(nopen & X["water"] & ok, "both"), (nopen & ~X["water"] & ok, "nisar_only"),
                                                              (~nopen & X["water"] & ok, "rcm_only")]),
                           dict(group="validation", sensor=f"NISAR + {REF[k][1]}", label=f"NISAR vs {REF[k][1]}: water",
                                legend=[[HEX(C["both"]), "both see water"], [HEX(C["nisar_only"]), "NISAR only"],
                                        [HEX(C["rcm_only"]), f"{REF[k][1]} only"]], default=False))
                    P["layers"].append(f"agreement_{k}")
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
    if case.get("kind") == "validation":                  # a check: summarise the clearest pass, not the "flood" date
        rk = next((k for k in ("gfm", "dswx", "lance") if any(k in p.get("validation", {}) for p in withb)), None)
        vv = [p for p in withb if rk in p.get("validation", {})]
        if vv:
            sp = max(vv, key=lambda p: (p["validation"][rk]["compared_pct"], p["date"]))
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
    validation = {}
    NAMES = dict(rcm="Canada's RCM radar (CSA, C-band)", dswx="NASA's flood map (OPERA DSWx-HLS, optical)",
                 rcm_vs_dswx="RCM vs NASA DSWx (no NISAR: how well two other sensors agree)",
                 lance="NASA's LANCE flood map (VIIRS / MODIS, optical, 250 m)", gfm="Copernicus GFM (Sentinel-1, observed water)")
    for k in ("rcm", "dswx", "rcm_vs_dswx", "lance", "gfm"):
        vp = [p for p in passes if k in p.get("validation", {})]
        if not vp:
            continue
        V = [p["validation"][k] for p in vp]
        mean = lambda q: round(sum(v[q] for v in V if v[q] is not None) / max(1, sum(v[q] is not None for v in V)), 2)
        ag = round(sum(v["agreement_pct"] for v in V) / len(V), 1)
        validation[k] = dict(source=NAMES[k], n_dates=len(vp), dates=[p["date"] for p in vp],
                             agreement_pct=ag, iou=mean("iou"), f1=mean("f1"),
                             **({q: mean(q) for q in ("precision", "recall") if any(v.get(q) is not None for v in V)}))
        if k == "rcm":
            validation[k].update(sensor="RCM C-band compact-pol (CSA), CEOS-ARD", match_days=RCM_DAYS,
                                 compared="open water incl. permanent (C-band can't see water under trees)",
                                 dates=[[p["date"], p["matched"]["rcm"]] for p in vp])
        if k == "dswx":
            validation[k].update(compared="open water incl. permanent, where DSWx has no cloud")
        if k in ("lance", "gfm"):
            validation[k].update(compared="water incl. permanent, where the map can see (LANCE: no cloud / terrain mask; "
                                          "GFM: outside its exclusion mask)", dates=[[p["date"], p["matched"][k]] for p in vp])
        who = dict(rcm="Canada's RCM radar", dswx="NASA's DSWx map", rcm_vs_dswx="RCM and NASA's DSWx",
                   lance="NASA's LANCE flood map", gfm="Copernicus GFM")[k]
        validation[k]["sentence"] = (f"{who} {'agree' if k == 'rcm_vs_dswx' else 'and NISAR agree'} on {ag:.0f}% of pixels "
                                     f"(open water IoU {mean('iou')}, {len(vp)} pass{'es' if len(vp) > 1 else ''}).")
    if validation:
        summary["validation"] = dict(source=next(k for k in ("rcm", "gfm", "dswx", "lance") if k in validation) if
                                     any(k in validation for k in ("rcm", "gfm", "dswx", "lance")) else None,
                                     **{k: dict(agreement_pct=v["agreement_pct"], iou=v["iou"], n_dates=v["n_dates"])
                                        for k, v in validation.items()})
        summary["validation"]["agreement_pct"] = validation[summary["validation"]["source"]]["agreement_pct"]
        summary["validation"]["iou"] = validation[summary["validation"]["source"]]["iou"]
        summary["validation"]["n_dates"] = validation[summary["validation"]["source"]]["n_dates"]
    if validation and case.get("kind") == "validation":      # a check, not a flood story: lead with the agreement
        summary["sentence"] = ("Where the official maps can see: " if "no_map" in case else "Clear sky, no vegetation: ") + " ".join(
            validation[k]["sentence"] for k in ("gfm", "dswx", "lance") if k in validation)
    validation = validation or None
    ev = dict(
        version=2, id=f"{place}/{fid}", place=f"{case['name']}, {case['country']}",
        **(dict(kind=case["kind"]) if case.get("kind") else {}),
        title=(f"{case['name']}, {D(fd).strftime('%b %Y')}" if case.get("kind") == "validation"
               else f"{case['name']} flood, {D(fd).strftime('%b %Y')}"), flood_date=fd,
        window=dict(start=w0.isoformat(), end=w1.isoformat(), days_before=WINDOW_DAYS, days_after=WINDOW_DAYS),
        bbox=list(bbox), area_km2=round(float(valid.sum() * px)), baselines=sorted({k for p in passes for k in p["baselines"]}),
        summary=summary, passes=passes, layers=W.layers, **(dict(validation=validation) if validation else {}),
        method=dict(detector=("fused v3 (fused.py: per-scene threshold, change from the dry season, HV, GUNW coherence; "
                              "water under vegetation from detect.py)") if det == "v3" else ("flood_nasa.final(): NISAR handbook §6.4 classes + transitions, confidence >= 0.8, handbook mask "
                              + ("(no city, bare land, slope > 5°; cropland kept here: the haor is flooded farmland)" if "no_map" in case
                                 else "(no cropland, city, bare land, slope > 5°)")
                              + f"; open-water HH threshold {case['open_hh']} dB")
                             if det == "doc33" else
                             "detect.py v2 (open water + water under vegetation, HH/HV), thresholds calibrated on clear "
                             f"optical days: HH {case['open_hh']} / HV {case['open_hv']} dB",
                    detector_info=L.get("info"), qa_dropped=qa_dropped,
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
            dict(name="ESA WorldCover 2021", url="https://esa-worldcover.org", credit="© ESA WorldCover project 2021, CC BY 4.0")]
        + ([dict(name="NASA LANCE NRT Global Flood Product (VIIRS VCDWD, MODIS MCDWD) + VIIRS true colour, via NASA GIBS",
                 url="https://www.earthdata.nasa.gov/data/tools/flood", credit="NASA LANCE / ESDIS; NASA EOSDIS GIBS")]
           if validation and "lance" in validation else [])
        + ([dict(name="Copernicus DEM GLO-30 (slope for the handbook mask)", url="https://registry.opendata.aws/copernicus-dem/",
                 credit="© DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the "
                        "European Union and ESA")] if det == "doc33" else [])
        + ([dict(name="RADARSAT Constellation Mission (RCM) CEOS-ARD", url="https://registry.opendata.aws/rcm-ceos-ard/",
                 credit="RCM data © Government of Canada (Canadian Space Agency); RCM Public User Licence")]
           if validation and "rcm" in validation else []),
    )
    (folder / "event.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
    (folder / "science.md").write_text(SCIENCE.format(**summary, title=ev["title"], start=w0, end=w1, n=len(passes),
                                                      limits=case.get("flood_limits", "paddies are flooded on purpose in season;"))
                                       + (VALIDATION.format(**validation["rcm"]) if validation and "rcm" in validation else "")
                                       + (VALID_DSWX.format(d=validation["dswx"]["sentence"], r=validation.get("rcm_vs_dswx", {}).get("sentence", ""))
                                          if validation and "dswx" in validation else "")
                                       + (VALID_MAPS.format(lines="\n".join(f"- {validation[k]['sentence']}" for k in ("lance", "gfm")
                                                                            if k in validation))
                                          if validation and any(k in validation for k in ("lance", "gfm")) else ""), encoding="utf-8")
    pl = dict(version=2, id=place, name=case["name"], country=case["country"], bbox=list(bbox),
              floods=[dict(id=fid, flood_date=fd, title=ev["title"], baseline=mb, **(dict(kind=case["kind"]) if case.get("kind") else {}),
                           improvement_pct=summary["improvement_pct"], nisar_adds_km2=summary["nisar_adds_km2"],
                           baseline_flood_km2=summary["baseline_flood_km2"],
                           **(dict(validation=summary["validation"]) if validation else {}))],
              history=None)
    pf = EVENTS_DIR / place / "place.json"
    if pf.exists():                                       # keep other floods / history already listed
        old = json.loads(pf.read_text(encoding="utf-8"))
        pl["floods"] = sorted([f for f in old.get("floods", []) if f["id"] != fid] + pl["floods"], key=lambda f: f["flood_date"])
        pl["history"] = old.get("history")
    pl["validation"] = sorted({k for f in pl["floods"] for k in ("rcm", "dswx", "lance", "gfm") if k in (f.get("validation") or {})})
    pf.write_text(json.dumps(pl, indent=1, ensure_ascii=False), encoding="utf-8")
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

**Limits:** a NISAR addition is a candidate, not proven flood; {limits} numbers are
from one detector with thresholds fitted on clear days. Audit: docs/10-Results.md.
"""


VALIDATION = """
**Independent check (RCM):** {sentence} RCM (Canadian Space Agency, C-band, compact-pol) is a different radar,
band and orbit. Its water = one Otsu threshold per image on the RL band (tiles with both water and land), on our 80 m
grid; compared with NISAR open water only, where both see. Layers `rcm_water`, `rcm_radar`, `nisar_open`, `agreement`.
"""
VALID_DSWX = """
**Check against NASA's map (DSWx-HLS):** {d} {r} Same open-water masks, only where DSWx has no cloud.
Layer `dswx_water`.
"""


VALID_MAPS = """
**Check against the other official maps:** NISAR water (incl. permanent) vs each map's water (flood + normal water),
only where that map can see (LANCE: no cloud or terrain mask; GFM: outside its exclusion mask) and NISAR is valid.
Layers `lance_water`, `gfm_water`, `nisar_open`.

{lines}
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("place", choices=sorted(PLACES))
    ap.add_argument("--date", help="flood date YYYY-MM-DD (default: wettest NISAR pass)")
    ap.add_argument("--detector", choices=["v3", "v2", "doc33"], help="default: v3 (fused.py), or the place's own")
    a = ap.parse_args(argv)
    global DETECTOR
    DETECTOR = a.detector
    build(a.place, a.date)


if __name__ == "__main__":
    main()
