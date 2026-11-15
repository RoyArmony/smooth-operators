"""Sentinel-1 years for a place's flood history: replaces the RADARSAT-1 image(s) in events/<place>/history/.

    python -m unseen.s1history gerd-blue-nile-ethiopia

Why: at GERD, RADARSAT-1 has a single partial 1998 scene. Sentinel-1 (ESA Copernicus, C-band) passes every 12 days
from 2015, so we take one image per year on one fixed track, near the same day of the year, and watch the reservoir fill.
Source: Sentinel-1 RTC (radiometrically terrain corrected gamma0, 10 m) on Microsoft Planetary Computer (no login).
Everything goes on the NISAR 80 m grid first, like every other source (docs/12). Run after unseen.historyfolder.
"""
import argparse
import datetime as dt
import json

import numpy as np
from scipy.ndimage import median_filter

from . import bundle
from .config import DATA_DIR, EVENTS_DIR
from .eventfolder import C, HEX, PLACES, Writer, classes_rgba, grey
from .flood import load
from .history import CA, otsu

# per place: fixed track (same geometry every year), target day of year, years
S1 = {"gerd-blue-nile-ethiopia": dict(orbit="descending", rel_orbit=50, day="10-01", years=range(2016, 2026),
                                      window_days=30)}
STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def pick(bbox, cfg, year):
    """All RTC items of the pass (same date, same track) nearest the target day within ± window_days."""
    import planetary_computer as pc
    import pystac_client
    cat = pystac_client.Client.open(STAC, modifier=pc.sign_inplace)
    t0 = dt.date.fromisoformat(f"{year}-{cfg['day']}")
    w = dt.timedelta(days=cfg["window_days"])
    items = [i for i in cat.search(collections=["sentinel-1-rtc"], bbox=list(bbox),
                                   datetime=f"{t0 - w}/{t0 + w}").items()
             if i.properties["sat:orbit_state"] == cfg["orbit"] and i.properties["sat:relative_orbit"] == cfg["rel_orbit"]]
    if not items:
        return None, []
    by = {}
    for i in items:
        by.setdefault(i.datetime.date(), []).append(i)
    d = min(by, key=lambda x: abs((x - t0).days))
    return d.isoformat(), by[d]


def on_grid(items, pol, grid, shape):
    """gamma0 (linear power) of one polarisation, mosaicked onto our grid by averaging (COG overviews, ~40 m read)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.warp import reproject, transform_bounds
    from rasterio.windows import from_bounds
    x, y, dx = grid["x"], grid["y"], grid["dx"]
    dst_t, dst_crs = from_origin(x[0] - dx / 2, y[0] + dx / 2, dx, dx), f"EPSG:{grid['epsg']}"
    gb = (x[0] - dx / 2, y[-1] - dx / 2, x[-1] + dx / 2, y[0] + dx / 2)
    out = np.full(shape, np.nan, "float32")
    env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", **(dict(GDAL_CURL_CA_BUNDLE=CA, CURL_CA_BUNDLE=CA) if CA else {}))
    for it in items:
        with rasterio.Env(**env), rasterio.open(it.assets[pol].href) as s:
            win = from_bounds(*transform_bounds(dst_crs, s.crs, *gb), s.transform).round_offsets().round_lengths()
            win = win.intersection(rasterio.windows.Window(0, 0, s.width, s.height))
            fac = 4                                                    # 10 m -> 40 m read, then average to 80 m
            a = s.read(1, window=win, out_shape=(max(1, int(win.height // fac)), max(1, int(win.width // fac))),
                       resampling=Resampling.average).astype("float32")
            a[(a <= 0) | ~np.isfinite(a)] = np.nan
            wt = s.window_transform(win) * s.window_transform(win).scale(win.width / a.shape[1], win.height / a.shape[0])
            part = np.full(shape, np.nan, "float32")
            reproject(a, part, src_transform=wt, src_crs=s.crs, dst_transform=dst_t, dst_crs=dst_crs,
                      resampling=Resampling.average, src_nodata=np.nan, dst_nodata=np.nan)
        out = np.where(np.isfinite(out), out, part)
    return out


def year_db(place, bbox, cfg, year, grid, shape):
    d, items = pick(bbox, cfg, year)
    if not d:
        return None
    cache = DATA_DIR / "s1" / f"{place}_{d}_{shape[0]}x{shape[1]}.npz"
    if cache.exists():
        z = np.load(cache)
        return dict(date=d, vv=z["vv"], vh=z["vh"], scenes=[str(s) for s in z["scenes"]])
    vv, vh = (10 * np.log10(on_grid(items, p, grid, shape)) for p in ("vv", "vh"))
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache, vv=vv, vh=vh, scenes=np.array([i.id for i in items]))
    return dict(date=d, vv=vv, vh=vh, scenes=[i.id for i in items])


def smooth(db):
    return median_filter(np.nan_to_num(db, nan=np.nanmedian(db)), 3) * np.where(np.isfinite(db), 1, np.nan)


def build(place):
    case, cfg = PLACES[place], S1[place]
    bbox = case["bbox"]
    stack, ndates, grid, st = load(bbox, case["stack_key"])
    shape = stack.shape[-2:]
    px = (grid["dx"] / 1000) ** 2
    from .fused import detect_fused, qa                  # NISAR permanent water / valid from detector v3, as historyfolder
    stack, ndates, _ = qa(stack, ndates)
    L = detect_fused(stack, ndates, grid, bbox, track=(st or {}).get("track"), frame=(st or {}).get("frame"))
    perm, valid = L["permanent"], L["valid"]

    years = [r for y in cfg["years"] if (r := year_db(place, bbox, cfg, y, grid, shape))]
    for r in years:
        r["vv"], r["vh"] = smooth(r["vv"]), smooth(r["vh"])
        print(r["date"], f"{np.isfinite(r['vv']).mean():.0%} covered", r["scenes"], flush=True)
    # one threshold pair for all years: Otsu on the latest year (full lake: water and land both present)
    ref = years[-1]
    tvv, tvh = otsu(ref["vv"][np.isfinite(ref["vv"]) & valid]), otsu(ref["vh"][np.isfinite(ref["vh"]) & valid])
    print(f"thresholds VV {tvv:.1f} dB, VH {tvh:.1f} dB (Otsu, {ref['date']})")

    folder = EVENTS_DIR / place / "history"
    ev = json.loads((folder / "event.json").read_text(encoding="utf-8"))
    for f in (folder / "layers").glob("rs1_*"):             # RADARSAT-1 out
        f.unlink()
    for f in (folder / "layers").glob("s1_*"):              # re-runs start clean
        f.unlink()
    ev["layers"] = {k: v for k, v in ev["layers"].items() if not k.startswith(("rs1_", "s1_"))}
    images = [i for i in ev["images"] if i["sensor"] not in ("RADARSAT-1", "Sentinel-1")]

    W = Writer(folder, grid)
    new = []
    for r in years:
        d, vv, vh = r["date"], r["vv"], r["vh"]
        ok = np.isfinite(vv) & np.isfinite(vh) & valid
        water = (vv < tvv) & (vh < tvh) & ok
        flood = water & ~perm
        W.picture("s1_radar", d, grey(vv, -25, 0), dict(group="radar", sensor="Sentinel-1 C-band VV (ESA Copernicus)",
                  label="Sentinel-1 radar (dark = water)", legend=None, default=True), half=True)
        W.rgba("s1_water", d, classes_rgba([(flood, "flood")]), dict(group="result", sensor="Sentinel-1 (our analysis)",
               label="Flood from Sentinel-1 (our analysis)", legend=[[HEX(C["flood"]), "flood"]], default=True))
        I = dict(date=d, sensor="Sentinel-1",
                 radar=dict(band="C, VV + VH, RTC gamma0", orbit=cfg["orbit"], relative_orbit=cfg["rel_orbit"],
                            scenes=r["scenes"], threshold_db=dict(vv=round(tvv, 1), vh=round(tvh, 1))),
                 layers=["s1_radar", "s1_water"], optical=None, baselines={},
                 flood_km2=round(float(flood.sum() * px), 1),
                 open_water_km2=round(float(water.sum() * px), 1),
                 valid_pct=round(100 * float(ok.sum()) / float(valid.sum())),
                 baselines_missing=[])
        new.append(I)
        print(d, "open water", I["open_water_km2"], "km², flood beyond today's lake", I["flood_km2"], "km²", flush=True)

    s1_bounds = {k: v for k, v in W.layers.items()}
    ev["layers"] = {**s1_bounds, **ev["layers"]}
    ev["images"] = sorted(new + images, key=lambda i: i["date"])
    I_ = ev["images"]

    # summary per year
    ys = []
    for y in sorted({i["date"][:4] for i in I_}):
        yi = [i for i in I_ if i["date"][:4] == y]
        top = max(yi, key=lambda i: i["flood_km2"] or 0)
        ys.append(dict(year=int(y), sensor=top["sensor"], max_flood_km2=top["flood_km2"], date=top["date"],
                       n_images=len(yi), flood_season_seen=any(i["date"][5:7] in ("08", "09", "10", "11", "12") for i in yi),
                       **({"open_water_km2": top["open_water_km2"]} if "open_water_km2" in top else {})))
    first, last_s1 = new[0], new[-1]
    nis = max((i for i in I_ if i["sensor"] == "NISAR"), key=lambda i: i["flood_km2"] or 0)
    area = ev["area_km2"]
    ev["title"] = f"{case['name']}, {I_[0]['date'][:4]}–{I_[-1]['date'][:4]}"
    ev["summary"] = dict(
        years=ys,
        sentence=(f"Same {area:,} km² box, early October each year (Sentinel-1): open water {first['open_water_km2']:,.0f} km² "
                  f"in {first['date'][:4]} (river, before the dam), {last_s1['open_water_km2']:,.0f} km² in {last_s1['date'][:4]} "
                  f"(the reservoir). Flood beyond the lake: {nis['flood_km2']:,.0f} km² on {nis['date']} (NISAR)."),
        caveat="Two radars (C-band Sentinel-1 2016–2025, L-band NISAR 2026) and two detectors: compare the pattern, not exact km².")
    ev["sampling"] = dict(rule=f"Sentinel-1: one pass a year, track {cfg['rel_orbit']} {cfg['orbit']}, nearest {cfg['day']} "
                               f"(± {cfg['window_days']} d); NISAR: each year's wettest, then others ≥ 30 days apart",
                          kept=len(I_))
    m = ev["method"]
    m.pop("rs1", None)
    m["s1"] = (f"Sentinel-1 RTC gamma0 VV + VH (Planetary Computer), averaged onto the NISAR 80 m grid, 3×3 median; "
               f"water = VV < {tvv:.1f} dB and VH < {tvh:.1f} dB (Otsu on {ref['date']}, same thresholds every year)")
    m["baselines"] = "GFM (Sentinel-1) exists from 2015, NASA OPERA DSWx-HLS from 2023: only on NISAR dates"
    src = [s for s in ev["sources"] if "RADARSAT-1" not in s["name"] and "Sentinel-1 RTC" not in s["name"]]
    ev["sources"] = [dict(name="Sentinel-1 RTC (Microsoft Planetary Computer)",
                          url="https://planetarycomputer.microsoft.com/dataset/sentinel-1-rtc",
                          credit="Contains modified Copernicus Sentinel data [2016–2025], processed by ESA; "
                                 "RTC by Catalyst / Microsoft Planetary Computer")] + src
    (folder / "event.json").write_text(json.dumps(ev, indent=1, ensure_ascii=False), encoding="utf-8")
    (folder / "science.md").write_text(SCIENCE.format(title=ev["title"], sentence=ev["summary"]["sentence"], n=len(I_),
                                                      n1=len(new), tvv=tvv, tvh=tvh, ref=ref["date"]), encoding="utf-8")
    pf = EVENTS_DIR / place / "place.json"
    pl = json.loads(pf.read_text(encoding="utf-8"))
    pl["history"] = dict(id="history", first=I_[0]["date"], last=I_[-1]["date"], n_images=len(I_),
                         sensors=sorted({i["sensor"] for i in I_}))
    pf.write_text(json.dumps(pl, indent=1, ensure_ascii=False), encoding="utf-8")
    bundle.write_index()
    return ev


SCIENCE = """# {title}: flood history

{sentence}

**Images:** {n}. Sentinel-1 (ESA Copernicus, C-band): {n1}, one a year near 1 October, always the same orbit track,
so the years compare. NISAR (L-band) 2026 passes, each with NASA OPERA DSWx-HLS where it exists.

**Method:** everything on NISAR's 80 m grid. Sentinel-1: terrain-corrected gamma0 (RTC), water = VV < {tvv:.1f} dB
and VH < {tvh:.1f} dB (Otsu on {ref}, the same for every year). NISAR: our detector. Flood = water beyond the lake
NISAR sees on ≥ 90 % of its passes, so "open water" shows the reservoir filling and "flood" shows how far it spreads past it.

**Limits:** C-band and L-band differ (wind-roughened water, shadows in the gorge); one threshold for all Sentinel-1 years:
compare the pattern, not exact km². One image a year cannot catch the yearly peak. Audit: docs/10-Results.md.
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("place", choices=sorted(S1))
    build(ap.parse_args(argv).place)


if __name__ == "__main__":
    main()
