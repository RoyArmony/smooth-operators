"""List RADARSAT-1 scenes (1996-2013) over a box, from the open EODMS STAC (no login).

    python scripts/rs1_coverage.py                          # Peace-Athabasca Delta
    python scripts/rs1_coverage.py -112.0 58.3 -110.8 59.0  # west south east north

Prints scenes per year with how much of the box each covers, mode and month, best first.
Images are Cloud-Optimized GeoTIFFs on AWS (radarsat-r1-l1-cog), readable without download.
"""
import sys
from collections import Counter

import requests
from shapely.geometry import box, shape

STAC = "https://eodms-sgdot.nrcan-rncan.gc.ca/search/search"
DEFAULT_BBOX = [-112.0, 58.3, -110.8, 59.0]


def search(bbox, start="1995-01-01", end="2013-12-31"):
    body = {"collections": ["Radarsat-1-L1-COG"], "bbox": bbox, "limit": 100,
            "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z"}
    feats = []
    for _ in range(50):
        j = requests.post(STAC, json=body, timeout=120).json()
        feats += j.get("features", [])
        nxt = [link for link in j.get("links", []) if link.get("rel") == "next"]
        if not nxt or len(j.get("features", [])) < 100:
            break
        body = {**body, **nxt[0].get("body", {})}
    aoi = box(*bbox)
    for f in feats:
        f["cov"] = shape(f["geometry"]).intersection(aoi).area / aoi.area
    return feats


def main():
    bbox = [float(v) for v in sys.argv[1:5]] if len(sys.argv) >= 5 else DEFAULT_BBOX
    feats = search(bbox)
    print(f"bbox {bbox}: {len(feats)} RADARSAT-1 scenes")
    full = [f for f in feats if f["cov"] >= 0.9]
    print(f"  covering >= 90% of the box: {len(full)}")
    years = Counter(f["properties"].get("datetime", "")[:4] for f in feats)
    print("  per year:", dict(sorted(years.items())))
    months = Counter(f["properties"].get("datetime", "")[5:7] for f in full)
    print("  full-cover scenes per month:", dict(sorted(months.items())))
    print("\nbest 15 (coverage, then date):")
    for f in sorted(feats, key=lambda f: (-round(f["cov"], 1), f["properties"].get("datetime", "")))[:15]:
        p = f["properties"]
        mode = p.get("sar:instrument_mode") or p.get("beam_mode") or p.get("mode") or "?"
        print(f"  {p.get('datetime', '')[:10]}  cover {f['cov']:.0%}  mode {mode}  {f['id']}")


if __name__ == "__main__":
    main()
