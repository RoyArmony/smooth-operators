"""`unseen` command: build site bundles for the web viewer (events/).

  unseen auth-check
  unseen site  --id tonle-sap --title "Tonle Sap, Cambodia" --bbox 103.6,12.3,104.7,13.3 [--kind story] [--passes all|best]
  unseen build [--only ID]           every site in pipeline/sites.json (stories: all passes; others: wettest pass)
  unseen world                      world event from the site bundles (sum over sites, wettest pass each)
  unseen index                      rebuild events/index.json
"""
import argparse, json

from . import bundle, flood, landcover


def site(eid, title, bbox, kind="site", passes="all", place=None, use_optical=True, refresh=False, detector="v3", dry_dates=None, fill=False):
    from .fused import qa
    stack, dates, grid, st = flood.load(bbox, eid, refresh=refresh)
    stack, dates, dropped = qa(stack, dates)                 # corrupt passes out (both detectors)
    if dropped:
        print(f"[qa] {eid}: dropped corrupt passes {dropped}")
    L, cal = flood.water(stack, dates, grid, bbox, use_optical=use_optical, detector=detector, st=st, dry_dates=dry_dates, fill=fill, key=eid)
    try:
        lc = landcover.on_grid(grid, bbox, key=eid)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] land cover skipped: {e}"); lc = None
    rows = list(flood.gap(L, dates, grid, bbox, lc=lc))
    if not rows:
        raise RuntimeError("no NISAR pass has a Copernicus GFM map within 2 days")
    best = max(rows, key=lambda r: r["km2"]["nisar_adds"])
    ev = bundle.new_event(eid, title, kind, bbox, place)
    for r in rows:
        keep = passes == "all" or r is best
        d = r["nisar_date"]
        ent = dict(date=d, gfm_date=r["gfm_date"], stats=r["km2"], layers=[])
        if keep:
            for lid, m, sensor, lab, dflt in (
                    ("gfm_flood", r["gfm_flood"], "Sentinel-1 (Copernicus GFM)", "Official flood map (GFM)", True),
                    ("gfm_excluded", r["gfm_excluded"], "Sentinel-1 (Copernicus GFM)", "Official map: \"cannot see\"", True),
                    ("nisar_water", r["wet"] if kind == "story" else None, "NISAR L-band", "NISAR water", False),
                    ("nisar_adds", r["adds"], "NISAR L-band", "NISAR addition: water in the blank", True)):
                if m is None:          # world-tour sites: only the three layers the map needs (size budget)
                    continue
                bundle.add_mask_layer(ev, lid, d, m, grid, sensor, lab, dflt)
                ent["layers"].append(lid)
        ev["timeline"].append(ent)
    k = best["km2"]
    pct = round(100 * k["nisar_adds"] / k["gfm_flood"]) if k["gfm_flood"] >= 5 else None
    ev["headline"] = dict(
        date=best["nisar_date"],
        sentence=f"On {best['nisar_date']}, NISAR found {k['nisar_adds']:,.0f} km² of water where the official flood map "
                 f"(Copernicus GFM, {best['gfm_date']}) says it cannot see.",
        numbers=[dict(label="Official map: flood", value=k["gfm_flood"], unit="km²"),
                 dict(label="NISAR adds, in the blank", value=k["nisar_adds"], unit="km²"),
]
                + ([dict(label="more than the official map", value=pct, unit="%")] if pct is not None else
                   [dict(label="of it in forest (ESA WorldCover)", value=k["nisar_adds_forest"], unit="km²")] if "nisar_adds_forest" in k else []),
        badge=dict(text="Wettest NISAR pass", ref="timeline"))
    ev["method"] = dict(detector=("fused v3 (fused.py: per-scene threshold, change from dry season, HV, GUNW coherence; "
                                  "water under vegetation from detect.py)") if detector == "v3"
                        else "detect.py v2 (open water + water under vegetation, HH/HV)",
                        detector_info=L.get("info"), qa_dropped=dropped,
                        smart_fill=dict(on=True, added_km2=L.get("filled_km2")) if fill else None,
                        calibration=cal if cal and cal.get("used") else None, pixel_m=grid["dx"],
                        gap="NISAR water inside GFM exclusion mask, both valid, permanent water removed",
                        stack=None if st is None else dict(track=st["track"], frame=st["frame"], direction=st["direction"]))
    ev["sources"] = [
        dict(name="NISAR L2 GCOV", url="https://search.asf.alaska.edu", credit="NASA/JPL-Caltech, ISRO; data via ASF DAAC"),
        dict(name="NISAR L2 GUNW (coherence)", url="https://search.asf.alaska.edu", credit="NASA/JPL-Caltech, ISRO; data via ASF DAAC"),
        dict(name="Copernicus EMS Global Flood Monitoring", url="https://global-flood.emergency.copernicus.eu",
             credit="© European Union, Copernicus Emergency Management Service"),
        dict(name="OPERA DSWx-HLS", url="https://www.jpl.nasa.gov/go/opera", credit="NASA/JPL OPERA; data via PO.DAAC")]
    bundle.write_event(ev)
    return ev


SITES = __import__("pathlib").Path(__file__).resolve().parents[1] / "sites.json"


def world():
    """events/world/event.json: one entry per site (wettest pass), plus totals. Numbers only; the site's own
    bundle holds its layers."""
    from .config import EVENTS_DIR
    sites = json.loads(SITES.read_text())
    rows, tot_add, tot_gfm = [], 0.0, 0.0
    for s in sites["sites"]:
        f = EVENTS_DIR / s["id"] / "event.json"
        if not f.exists():
            continue
        e = json.loads(f.read_text())
        best = next((t for t in e["timeline"] if t["date"] == e["headline"]["date"]), None)
        if best is None:
            rows.append(dict(id=s["id"], title=s["title"], bbox=s["bbox"], compared=False)); continue
        k = best["stats"]
        tot_add += k["nisar_adds"]; tot_gfm += k["gfm_flood"]
        rows.append(dict(id=s["id"], title=s["title"], bbox=s["bbox"], compared=True, date=best["date"],
                         gfm_date=best["gfm_date"], gfm_flood_km2=k["gfm_flood"], nisar_adds_km2=k["nisar_adds"],
                         pct=round(100 * k["nisar_adds"] / k["gfm_flood"]) if k["gfm_flood"] >= 5 else None))
    ev = bundle.new_event("world", "16 flood sites", "world", [-180, -60, 180, 75], "World")
    ev["sites"] = rows
    pct = round(100 * tot_add / tot_gfm) if tot_gfm else None
    ev["headline"] = dict(
        date=max(r["date"] for r in rows if r.get("compared")),
        sentence=f"Across {len(rows)} flood sites we chose, on each site's wettest NISAR pass, NISAR found "
                 f"{tot_add:,.0f} km² of water inside the official flood maps' blanks: {pct}% more than the "
                 f"{tot_gfm:,.0f} km² they showed. A sample, not a global total.",
        numbers=[dict(label="NISAR adds, in the blanks", value=round(tot_add, 1), unit="km²"),
                 dict(label="Official maps: flood", value=round(tot_gfm, 1), unit="km²"),
                 dict(label="more", value=pct, unit="%")],
        badge=dict(text="Wettest pass per site · sample", ref="sites"))
    ev["sources"] = [dict(name="Site bundles", url="events/", credit="see each site's event.json")]
    bundle.write_event(ev)
    return ev


def main(argv=None):
    ap = argparse.ArgumentParser(prog="unseen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("auth-check")
    s = sub.add_parser("site")
    s.add_argument("--id", required=True); s.add_argument("--title", required=True)
    s.add_argument("--bbox", required=True, help="lon0,lat0,lon1,lat1")
    s.add_argument("--kind", default="site", choices=["story", "site", "live"])
    s.add_argument("--passes", default="all", choices=["all", "best"])
    s.add_argument("--place"); s.add_argument("--no-optical", action="store_true")
    s.add_argument("--detector", default="v3", choices=["v3", "v2"], help="v3 = fused (default), v2 = old detect.py")
    s.add_argument("--fill", action="store_true", help="smart fill with GLO-30 HAND (v3 only, experimental)")
    b = sub.add_parser("build"); b.add_argument("--only"); b.add_argument("--refresh", action="store_true", help="search for new NISAR passes")
    b.add_argument("--detector", default="v3", choices=["v3", "v2"])
    b.add_argument("--fill", action="store_true", help="smart fill with GLO-30 HAND (experimental)")
    sub.add_parser("world")
    sub.add_parser("index")
    a = ap.parse_args(argv)
    if a.cmd == "auth-check":
        from .auth import session
        r = session().get("https://urs.earthdata.nasa.gov/profile", allow_redirects=False, timeout=30)
        print("Earthdata login:", "ok" if r.status_code in (200, 302) else f"HTTP {r.status_code}")
    elif a.cmd == "site":
        ev = site(a.id, a.title, [float(v) for v in a.bbox.split(",")], a.kind, a.passes, a.place, not a.no_optical,
                  detector=a.detector, fill=a.fill)
        print(json.dumps(ev["headline"], indent=1, ensure_ascii=False))
        bundle.write_index()
    elif a.cmd == "build":
        for s in json.loads(SITES.read_text())["sites"]:
            if a.only and s["id"] != a.only:
                continue
            try:
                ev = site(s["id"], s["title"], s["bbox"], s["kind"], "all" if s["kind"] == "story" else "best",
                          refresh=a.refresh, detector=a.detector, dry_dates=s.get("dry_dates"), fill=a.fill)
                print(s["id"], ev["headline"]["numbers"][:2], flush=True)
            except Exception as e:  # noqa: BLE001
                print(s["id"], "FAILED", repr(e)[:200], flush=True)
        world(); bundle.write_index()
    elif a.cmd == "world":
        print(world()["headline"]["sentence"]); bundle.write_index()
    elif a.cmd == "index":
        print(len(bundle.write_index()), "events")


if __name__ == "__main__":
    main()
