"""Flood history of one place: CSA RADARSAT-1 (1996-2013) and NISAR (2026) on one grid, flood marked on every image.

    python -m unseen.history                 # Mekong delta (default case below)
    python -m unseen.history --no-gfm        # skip the Copernicus GFM comparison

Writes an Explorer case to site/viewer/sites/<id>/ (site.json + one radar image and one flood overlay per date).

Method
  * Grid: the NISAR GCOV stack over the box (UTM, 80 m). NISAR base images are reused from the 2026 site of the same box.
  * RADARSAT-1 (C-band HH, L1 GeoTIFF on AWS, open): read at reduced resolution, warped with its GCPs onto the grid,
    then shifted onto NISAR by gradient cross-correlation (RADARSAT-1 GCPs carry a flat-Earth offset).
  * RADARSAT-1 water: one threshold per image, Otsu on "split" tiles that hold both river and land
    (tiles with 15-85 % NISAR permanent water: bimodal by construction; tile idea from Martinis et al. 2015).
  * NISAR water: our detector (detect.py) with the thresholds calibrated on clear optical days for this box.
  * Flood = water minus permanent water (dark on >= 90 % of NISAR passes): rivers and canals don't count.
  * NISAR dates also get Copernicus GFM (Sentinel-1) within +-3 days: both / only NISAR / only GFM.
"""
import argparse
import datetime as dt
import json
import os

import numpy as np
import requests
from PIL import Image
from scipy.ndimage import median_filter, sobel

from . import bundle, gfm
from .config import DATA_DIR, REPO
from .detect import detect
from .flood import load

STAC = "https://eodms-sgdot.nrcan-rncan.gc.ca/search/search"
VIEWER = REPO / "site" / "viewer" / "sites"
CA = os.environ.get("CURL_CA_BUNDLE") or os.environ.get("REQUESTS_CA_BUNDLE") or ""   # proxy CA, if any

CASE = dict(
    id="mekong-delta-history-1998-2026",
    title="Mekong delta, 1998–2026",
    bbox=(105.0, 10.4, 105.6, 11.0),
    nisar_site="mekong-delta-vietnam-83-7",      # 2026 site of the same box: its NISAR images and calibration
    gfm_bundle="mekong-delta-vietnam",           # its events/ bundle: GFM fallback when the GFM STAC is down
    open_hh=-13.0, open_hv=-18.0,                # calibrated on clear optical days (that site's calibration)
    kind="flood history (RADARSAT-1 + NISAR)",
)
COL = dict(flood=(40, 130, 255, 230), both=(40, 130, 255, 230), nisar_only=(255, 150, 40, 240), gfm_only=(230, 60, 200, 230))


# ---------- RADARSAT-1 ----------
def rs1_scenes(bbox, min_cover=0.9):
    """Best RADARSAT-1 scene per date covering >= min_cover of the box (open EODMS STAC, no login)."""
    from shapely.geometry import box, shape
    body = {"collections": ["Radarsat-1-L1-COG"], "bbox": list(bbox), "limit": 100}
    feats = []
    for _ in range(20):
        j = requests.post(STAC, json=body, timeout=120).json()
        feats += j.get("features", [])
        nxt = [x for x in j.get("links", []) if x.get("rel") == "next"]
        if not nxt or len(j.get("features", [])) < 100:
            break
        body = {**body, **nxt[0].get("body", {})}
    aoi, best = box(*bbox), {}
    for f in feats:
        f["cov"] = shape(f["geometry"]).intersection(aoi).area / aoi.area
        d = f["properties"]["datetime"][:10]
        if f["cov"] >= min_cover and (d not in best or (f["cov"], -f["properties"]["resolution"]) >
                                      (best[d]["cov"], -best[d]["properties"]["resolution"])):
            best[d] = f
    return [best[d] for d in sorted(best)]


def rs1_on_grid(f, grid, shape):
    """RADARSAT-1 scene -> dB on our grid (GCP warp, average). DN is amplitude: dB = 20 log10(DN)."""
    import rasterio
    from rasterio.control import GroundControlPoint as G
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject
    cache = DATA_DIR / "rs1" / f"{f['id']}_{shape[0]}x{shape[1]}.npy"
    if cache.exists():
        return np.load(cache)
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    fac = max(1, int(dx / 2 / (f["properties"].get("resolution") or 25)))       # ~2 source px per grid px
    env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", **(dict(GDAL_CURL_CA_BUNDLE=CA, CURL_CA_BUNDLE=CA) if CA else {}))
    with rasterio.Env(**env), \
            rasterio.open("/vsicurl/" + f["assets"]["cog"]["href"]) as s:
        a = s.read(1, out_shape=(s.height // fac, s.width // fac), resampling=Resampling.average).astype("float32")
        sy, sx = s.height / a.shape[0], s.width / a.shape[1]
        gcps = [G(row=g.row / sy, col=g.col / sx, x=g.x, y=g.y, z=g.z) for g in s.gcps[0]]
        gcrs, dtype = s.gcps[1], s.dtypes[0]
    a[a == 0] = np.nan
    out = np.full(shape, np.nan, "float32")
    reproject(a ** 2 if dtype == "uint8" else a, out, gcps=gcps, src_crs=gcrs,
              dst_transform=from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx), dst_crs=f"EPSG:{grid['epsg']}",
              resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
    db = 10 * np.log10(np.where(out > 0, out, np.nan)).astype("float32")
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, db)
    return db


def align(ref, mov, maxs=60):
    """Integer (dy, dx) that best lines up the edges of mov with ref (gradient cross-correlation, FFT)."""
    def edges(a):
        a = np.nan_to_num(a - np.nanmedian(a))
        g = np.hypot(sobel(a, 0), sobel(a, 1))
        return (g - g.mean()) / (g.std() + 1e-9)
    A, B = edges(ref), edges(mov)
    c = np.real(np.fft.ifft2(np.fft.fft2(A) * np.conj(np.fft.fft2(B))))
    c = np.fft.fftshift(c)
    cy, cx = np.array(c.shape) // 2
    w = c[cy - maxs:cy + maxs + 1, cx - maxs:cx + maxs + 1]
    dy, dx = np.unravel_index(np.argmax(w), w.shape)
    return int(dy - maxs), int(dx - maxs)


def shift(a, dy, dx):
    out = np.full_like(a, np.nan)
    H, W = a.shape
    out[max(dy, 0):H + min(dy, 0), max(dx, 0):W + min(dx, 0)] = a[max(-dy, 0):H + min(-dy, 0), max(-dx, 0):W + min(-dx, 0)]
    return out


def otsu(v):
    h, e = np.histogram(v, 256)
    c = (e[:-1] + e[1:]) / 2
    w = np.cumsum(h)
    m = np.cumsum(h * c)
    b = (m[-1] * w / w[-1] - m) ** 2 / (w * (w[-1] - w) + 1e-9)
    return float(c[np.nanargmax(b)])


def split_threshold(db, permanent, tile=32):
    """Otsu threshold from tiles holding both permanent water and land (15-85 %): always bimodal, wet or dry season."""
    H, W = db.shape
    pick = np.zeros_like(permanent)
    n = 0
    for i in range(0, H - tile + 1, tile):
        for j in range(0, W - tile + 1, tile):
            p = permanent[i:i + tile, j:j + tile].mean()
            if 0.15 <= p <= 0.85 and np.isfinite(db[i:i + tile, j:j + tile]).mean() > 0.9:
                pick[i:i + tile, j:j + tile] = True
                n += 1
    v = db[pick & np.isfinite(db)]
    return otsu(v), n


def gfm_from_bundle(eid, date, grid, shape):
    """GFM flood + exclusion mask for one NISAR date, read back from a committed events/<eid> bundle (PNG, EPSG:4326)
    onto our grid. Used when the GFM STAC is unreachable; same data our pipeline fetched (gfm.on_grid, +-2 d)."""
    import rasterio
    from rasterio.transform import from_bounds, from_origin
    from rasterio.warp import Resampling, reproject
    if not eid:
        return None
    root = REPO / "events" / eid
    E = json.loads((root / "event.json").read_text())
    row = next((r for r in E["timeline"] if r["date"] == date and "gfm_flood" in r["layers"]), None)
    if row is None:
        return None
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    out = {}
    for k in ("gfm_flood", "gfm_excluded"):
        lay = E["layers"][k]
        a = np.array(Image.open(root / lay["files"][date]).convert("RGBA"))[..., 3]
        (s_, w_), (n_, e_) = lay["bounds"]
        m = np.zeros(shape, np.uint8)
        reproject((a > 0).astype(np.uint8), m, src_transform=from_bounds(w_, s_, e_, n_, a.shape[1], a.shape[0]),
                  src_crs="EPSG:4326", dst_transform=from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx),
                  dst_crs=f"EPSG:{grid['epsg']}", resampling=Resampling.nearest)
        out[k] = m.astype(bool)
    print(f"  GFM {date}: from events/{eid} (GFM {row.get('gfm_date')})")
    return dict(date=row.get("gfm_date", date), flood=out["gfm_flood"], excluded=out["gfm_excluded"],
                seen=np.ones(shape, bool), n=0)


# ---------- outputs ----------
def gray_jpg(db, path):
    v = db[np.isfinite(db)]
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    g = np.clip((np.nan_to_num(db, nan=lo) - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
    Image.fromarray(g).convert("RGB").save(path, quality=80, optimize=True)


def overlay_png(classes, path):
    H, W = next(iter(classes.values())).shape
    a = np.zeros((H, W, 4), np.uint8)
    for k, m in classes.items():
        a[m] = COL[k]
    Image.fromarray(a).save(path, optimize=True)


def build(case=CASE, use_gfm=True):
    sid, bbox = case["id"], case["bbox"]
    out = VIEWER / sid
    out.mkdir(parents=True, exist_ok=True)
    src = json.loads((VIEWER / case["nisar_site"] / "site.json").read_text())

    stack, ndates, grid, _ = load(bbox, case["nisar_site"])
    L = detect(stack, pixel_m=grid["dx"], open_hh=case["open_hh"], open_hv=case["open_hv"])
    perm, valid, shape = L["permanent"], L["valid"], L["valid"].shape
    px = (grid["dx"] / 1000) ** 2
    ref = np.nanmedian(L["hh"], 0)                          # NISAR HH median: reference for alignment
    assert list(src["size"]) == [shape[1], shape[0]], "NISAR grid differs from the 2026 site"

    frames, summary, assets, log, masks = [], [], {}, [], {}
    for f in rs1_scenes(bbox):
        p, d = f["properties"], f["properties"]["datetime"][:10]
        db = rs1_on_grid(f, grid, shape)
        if np.isfinite(db).mean() < 0.8:
            continue
        dy, dx = align(ref, db)
        db = shift(db, dy, dx)
        db = median_filter(np.nan_to_num(db, nan=np.nanmedian(db)), 3) * np.where(np.isfinite(db), 1, np.nan)
        thr, ntiles = split_threshold(db, perm)
        ok = np.isfinite(db) & valid
        flood = (db < thr) & ~perm & ok
        gray_jpg(db, out / f"radar_{d}.jpg")
        overlay_png({"flood": flood}, out / f"flood_{d}.png")
        frames.append(dict(date=d, sensor="RADARSAT-1", nisar=f"radar_{d}.jpg", hidden=f"flood_{d}.png",
                           beam=p["beam_mnemonic"], orbit=p["sat:orbit_state"], scene=f["assets"]["cog"]["href"].rsplit("/", 1)[-1]))
        summary.append(dict(date=d, new_water=round(float(flood.sum() * px), 1), hidden_new=0, valid=round(float(ok.mean()), 3)))
        log.append(dict(date=d, beam=p["beam_mnemonic"], threshold_db=round(thr, 1), tiles=ntiles, shift_px=[dy, dx]))
        masks[d] = dict(rs1_water=flood, rs1_db=db)
        print(d, p["beam_mnemonic"], f"thr {thr:.1f} dB ({ntiles} tiles)", f"shift {dy},{dx}", f"flood {summary[-1]['new_water']} km²", flush=True)

    for t, d in enumerate(ndates):
        wet = (L["water"][t] | L["canopy"][t]) & ~perm & valid
        G = None
        if use_gfm:
            try:
                G = gfm.on_grid(bbox, d, grid, shape, days=3)
            except Exception as e:  # noqa: BLE001
                print(f"[warn] GFM {d}: {e!r}"[:120])
            if G is None:                                   # GFM server down: same GFM, from our 2026 bundle
                G = gfm_from_bundle(case.get("gfm_bundle"), d, grid, shape)
        s = dict(date=d, new_water=round(float(wet.sum() * px), 1), hidden_new=0, valid=round(float(valid.mean()), 3))
        if G:
            seen = G["seen"] & valid
            gf = G["flood"] & ~perm & seen
            cls = dict(both=wet & gf, nisar_only=wet & ~gf, gfm_only=gf & ~wet)
            s.update(gfm_date=G["date"], gfm_km2=round(float(gf.sum() * px), 1),
                     both_km2=round(float((wet & gf).sum() * px), 1),
                     nisar_only_km2=round(float((wet & ~gf & seen).sum() * px), 1),
                     gfm_only_km2=round(float((gf & ~wet).sum() * px), 1),
                     nisar_only_in_gfm_blank_km2=round(float((wet & G["excluded"] & seen).sum() * px), 1))
            s["hidden_new"] = s["nisar_only_km2"]
            masks[d] = dict(nisar_water=wet, gfm_flood=gf, gfm_excluded=G["excluded"] & seen, gfm_date=G["date"])
        else:
            cls = dict(flood=wet)
            masks[d] = dict(nisar_water=wet)
        overlay_png(cls, out / f"flood_{d}.png")
        name = f"nisar_{d}.jpg"
        assets[name] = f"sites/{case['nisar_site']}/{name}"
        frames.append(dict(date=d, sensor="NISAR", nisar=name, hidden=f"flood_{d}.png", gfm=bool(G)))
        summary.append(s)
        print(d, "NISAR", f"flood {s['new_water']} km²", f"GFM {s.get('gfm_km2', '–')} km² ({s.get('gfm_date', 'none')})", flush=True)

    years = {}
    for fr, s in zip(frames, summary):
        y = fr["date"][:4]
        if y not in years or s["new_water"] > years[y]["km2"]:
            years[y] = dict(km2=s["new_water"], date=fr["date"], sensor=fr["sensor"])
    g = [s for s in summary if "gfm_km2" in s]
    season = lambda d: d[5:7] in ("08", "09", "10", "11", "12")       # flood season here: Aug-Dec
    seasonal = {y: any(season(f["date"]) for f in frames if f["date"][:4] == y) for y in years}
    headline = [dict(key=f"peak_{y}", label=f"Most flood seen, {y}", value=round(v["km2"]), unit="km²",
                     note=f"{v['date']} · {v['sensor']}" + ("" if seasonal[y] else " · dry-season images only"),
                     strong=y in ("2001", "2026")) for y, v in sorted(years.items())]
    if g:
        pk = max(g, key=lambda s: s["new_water"])
        headline.append(dict(key="vs_gfm", label="NISAR vs GFM (official map), NISAR peak", value=f"{pk['new_water']:.0f} / {pk['gfm_km2']:.0f}",
                             unit="km²", note=f"{pk['date']} vs GFM {pk['gfm_date']} · both {pk['both_km2']:.0f}, only NISAR {pk['nisar_only_km2']:.0f}, only GFM {pk['gfm_only_km2']:.0f}"))
    site = dict(
        id=sid, title=case["title"], bbox=list(bbox), event_date=None, kind=case["kind"], hazard="FL", history=True,
        pixel_m=grid["dx"], size=src["size"], corners=src["corners"], frames=frames, summary=summary, assets=assets,
        photos=src.get("photos", {}), stack=src.get("stack"),
        created=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        report=dict(
            hazard="flood", headline=headline, layers=[],
            pass_label="Flood on this image",
            pass_legend=[["#2882ff", "flood: NISAR and GFM"], ["#ff9628", "only NISAR (GFM missed it)"],
                         ["#e63cc8", "only GFM"]],
            notes=["Flood = water beyond permanent water (dark on ≥ 90 % of NISAR passes): rivers and canals excluded.",
                   "RADARSAT-1 (CSA, C-band HH, 1998–2007): one threshold per image from tiles with both river and land "
                   "(split-based Otsu), after warping onto the NISAR grid and aligning by edges.",
                   f"NISAR (L-band HH+HV, 2026): our detector, thresholds HH {case['open_hh']} / HV {case['open_hv']} dB "
                   "calibrated on clear optical days.",
                   "GFM = Copernicus Global Flood Monitoring (Sentinel-1), nearest day ± 3 d. Only from 2015, so not on RADARSAT-1 dates.",
                   "C-band misses some water under rice and trees that L-band sees: older years are a lower bound.",
                   "Rice paddies are flooded on purpose in season: not all water here is disaster."]),
        rs1_log=log,
    )
    (out / "site.json").write_text(json.dumps(site, indent=1, ensure_ascii=False))
    write_event(case, site, masks, grid)
    return site


# ---------- events/ bundle (contract v1, docs/08 §3) ----------
EVENT_ID = "mekong-delta-history"     # = Explorer id minus its "-1998-2026" suffix (inmap.js finds bundles that way)
RS1_PICTURES = ("2001-08-30", "2005-10-27", "2006-03-13", "2006-10-22")   # then/now swipe: dry vs each flood year


def write_event(case, site, masks, grid):
    """events/<EVENT_ID>/: rs1_water (RADARSAT-1 dates), agreement vs GFM (NISAR dates; nisar_water if no GFM),
    rs1_rgb pictures for a few key dates (kept few: events/ must stay < 20 MB)."""
    ev = bundle.new_event(EVENT_ID, case["title"], "story", case["bbox"], "Mekong delta, Vietnam")
    for fr, sm in zip(site["frames"], site["summary"]):
        d, m, st, lay = fr["date"], masks[fr["date"]], dict(flood_km2=sm["new_water"]), []
        if fr["sensor"] == "RADARSAT-1":
            bundle.add_mask_layer(ev, "rs1_water", d, m["rs1_water"], grid, "RADARSAT-1 C-band (CSA)",
                                  label="Flood (RADARSAT-1)", default=True)
            lay.append("rs1_water")
            if d in RS1_PICTURES:
                db = m["rs1_db"]
                lo, hi = np.nanpercentile(db, 2), np.nanpercentile(db, 98)
                g = np.clip((np.nan_to_num(db, nan=lo) - lo) / (hi - lo) * 254 + 1, 1, 255).astype(np.uint8)
                g, b = bundle.to_wgs84(g[::2, ::2], dict(grid, x=grid["x"][::2], y=grid["y"][::2], dx=grid["dx"] * 2))   # 160 m: size
                rgba = np.dstack([g, g, g, np.where(g > 0, 255, 0).astype(np.uint8)])
                bundle.add_image_layer(ev, "rs1_rgb", d, Image.fromarray(rgba, "RGBA"), b, "radar",
                                       "RADARSAT-1 C-band (CSA)", label="RADARSAT-1 radar (dark = water)")
                lay.append("rs1_rgb")
        else:
            if "gfm_flood" not in m:                       # no GFM that week: NISAR flood alone
                bundle.add_mask_layer(ev, "nisar_water", d, m["nisar_water"], grid, "NISAR L-band",
                                      label="Flood (NISAR)", default=True)
                lay.append("nisar_water")
            else:                                          # agreement already holds NISAR's flood (blue + orange)
                w, gf = m["nisar_water"], m["gfm_flood"]
                cls = np.zeros(w.shape, np.uint8)
                cls[w & gf], cls[w & ~gf], cls[gf & ~w] = 1, 2, 3
                c, b = bundle.to_wgs84(cls, grid)
                rgba = np.zeros(c.shape + (4,), np.uint8)
                for k, key in ((1, "both"), (2, "nisar_only"), (3, "gfm_only")):
                    rgba[c == k] = COL[key]
                bundle.add_image_layer(ev, "agreement", d, Image.fromarray(rgba, "RGBA"), b, "validation",
                                       "NISAR L-band vs Sentinel-1 (Copernicus GFM)",
                                       label="NISAR vs official map (GFM)", default=True)
                ev["layers"]["agreement"]["legend"] = "#2882ff both · #ff9628 only NISAR · #e63cc8 only GFM"
                lay.append("agreement")                   # GFM "cannot see": in events/mekong-delta-vietnam
                st.update({k: sm[k] for k in ("gfm_date", "gfm_km2", "both_km2", "nisar_only_km2", "gfm_only_km2",
                                              "nisar_only_in_gfm_blank_km2")})
        ev["timeline"].append(dict(date=d, sensor=fr["sensor"], stats=st, layers=lay))
    rs1 = [r for r in ev["timeline"] if r["sensor"] == "RADARSAT-1"]
    old = max(rs1, key=lambda r: r["stats"]["flood_km2"])
    new = max((r for r in ev["timeline"] if "gfm_km2" in r["stats"]), key=lambda r: r["stats"]["flood_km2"])
    o, n = old["stats"], new["stats"]
    ev["headline"] = dict(
        date=new["date"],
        sentence=f"Same delta, 25 years apart: RADARSAT-1 saw {o['flood_km2']:,.0f} km² flooded on {old['date']}; "
                 f"NISAR saw {n['flood_km2']:,.0f} km² on {new['date']}, the official map (GFM) {n['gfm_km2']:,.0f} km².",
        numbers=[dict(label=f"Flood {old['date'][:4]} (RADARSAT-1)", value=o["flood_km2"], unit="km²"),
                 dict(label=f"Flood {new['date'][:4]} (NISAR)", value=n["flood_km2"], unit="km²"),
                 dict(label="Official map, same day (GFM)", value=n["gfm_km2"], unit="km²")],
        badge=dict(text="RADARSAT-1 (CSA) + NISAR · different radars: compare the pattern", ref="method"))
    ev["method"] = dict(module="pipeline/unseen/history.py", notes=site["report"]["notes"], rs1=site["rs1_log"],
                        flood="water beyond permanent water (dark on >= 90 % of NISAR passes); area = pixels x 80 m x 80 m")
    ev["sources"] = [
        dict(name="RADARSAT-1 L1 (EODMS / AWS)", url="https://registry.opendata.aws/radarsat-1/",
             credit="RADARSAT-1 data © Canadian Space Agency; Open Government Licence – Canada"),
        dict(name="NISAR L2 GCOV", url="https://search.asf.alaska.edu", credit="NASA/JPL-Caltech, ISRO; data via ASF DAAC"),
        dict(name="Copernicus EMS Global Flood Monitoring", url="https://global-flood.emergency.copernicus.eu",
             credit="© European Union, Copernicus Emergency Management Service")]
    d = bundle.write_event(ev)
    (d.parent / "science.md").write_text(SCIENCE.format(**ev["headline"]))
    bundle.write_index()
    return d


SCIENCE = """# Mekong delta, 1998–2026: flood history

**What:** the same 66 × 66 km of the Mekong delta (Dong Thap / An Giang), flooded every year Aug–Dec.
{sentence}

**Data:** RADARSAT-1 (CSA, C-band HH; 1998, 2001, 2005, 2006 Mar–Dec, 2007) and NISAR (L-band HH+HV, Jun–Oct 2026),
on one 80 m grid. On NISAR dates, Copernicus GFM (Sentinel-1) the same day ± 3 d.

**Method** (`pipeline/unseen/history.py`): RADARSAT-1 warped with its GCPs and aligned to NISAR by edges; one water
threshold per image (Otsu on tiles holding both river and land). NISAR: our detector, thresholds calibrated on clear
optical days. Flood = water beyond permanent water. `agreement`: both / only NISAR / only GFM.

**Limits:** two radars (C vs L band) and two methods: compare the pattern (dry ≈ 100–350 km², flood ≈ 1,500–2,800 km²),
not exact km². Paddies are flooded on purpose; dikes keep some fields dry. Numbers: docs/10-Results.md.
"""


def card(site):
    """Entry for site/viewer/sites/index.json (the Explorer list)."""
    fr, sm = site["frames"], site["summary"]
    pk = max(range(len(sm)), key=lambda i: sm[i]["new_water"])
    return dict(id=site["id"], title=site["title"], bbox=site["bbox"], created=site["created"], n_dates=len(fr),
                kind=site["kind"], hazard="FL", event_date=None, history=True,
                n_rs1=sum(f["sensor"] == "RADARSAT-1" for f in fr), n_nisar=sum(f["sensor"] == "NISAR" for f in fr),
                headline=["Years compared", len({f["date"][:4] for f in fr}), f"({fr[0]['date'][:4]}–{fr[-1]['date'][:4]})"],
                first=fr[0]["date"], last=fr[-1]["date"], stack=site.get("stack"),
                peak_water_km2=round(sm[pk]["new_water"]), max_hidden_by_clouds=0, veg_change_km2=0,
                passes=[dict(date=f["date"], kind=f["sensor"], water_km2=s["new_water"]) for f, s in zip(fr, sm)])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-gfm", action="store_true")
    a = ap.parse_args(argv)
    site = build(use_gfm=not a.no_gfm)
    idx_f = VIEWER / "index.json"
    idx = [s for s in json.loads(idx_f.read_text()) if s["id"] != site["id"]] + [card(site)]
    idx_f.write_text(json.dumps(idx))
    print(f"wrote {VIEWER / site['id']} and index.json")


if __name__ == "__main__":
    main()
