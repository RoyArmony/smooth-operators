"""Crop a v1 event bundle (events/<id>/) to a smaller box, to focus on where the change is.

    python scripts/crop_bundle.py flood-in-nepal-2026 85.22 26.90 85.44 27.11

Same pixels, no new analysis: every layer PNG (EPSG:4326) is cut to the box and its bounds updated.
km² on dates that have pictures = full-box km² x (share of that layer's pixels inside the box).
Dates without pictures can't be cut, so their stats are dropped (kept as dates only).
The original box is kept in event.json "crop.from_bbox".
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

STAT_OF = {"gfm_flood": "gfm_flood", "gfm_excluded": "gfm_excluded", "nisar_adds": "nisar_adds"}


def main(eid, w, s, e, n):
    root = Path(__file__).resolve().parents[1] / "events" / eid
    E = json.loads((root / "event.json").read_text(encoding="utf-8"))
    share = {}                                     # (layer, date) -> fraction of its pixels inside the box
    for k, lay in E["layers"].items():
        (s0, w0), (n0, e0) = lay["bounds"]
        for d, f in lay["files"].items():
            im = Image.open(root / f).convert("RGBA")
            W, H = im.size
            c0, c1 = round((w - w0) / (e0 - w0) * W), round((e - w0) / (e0 - w0) * W)
            r0, r1 = round((n0 - n) / (n0 - s0) * H), round((n0 - s) / (n0 - s0) * H)
            c0, r0, c1, r1 = max(0, c0), max(0, r0), min(W, c1), min(H, r1)
            a = np.array(im)[..., 3] > 0
            share[(k, d)] = float(a[r0:r1, c0:c1].sum()) / max(1, a.sum())
            im.crop((c0, r0, c1, r1)).save(root / f, optimize=True)
            # bounds of the pixels actually kept
            lay["bounds"] = [[n0 - r1 / H * (n0 - s0), w0 + c0 / W * (e0 - w0)],
                             [n0 - r0 / H * (n0 - s0), w0 + c1 / W * (e0 - w0)]]
    for row in E.get("timeline", []):
        ks = [(k, d) for (k, d) in share if d == row["date"]]
        if not ks:
            row["stats"] = {}
            continue
        st = row.get("stats", {})
        for k, d in ks:
            if STAT_OF.get(k) in st:
                st[STAT_OF[k]] = round(st[STAT_OF[k]] * share[(k, d)], 1)
        for k in list(st):                         # sub-splits of the full box can't be cut: drop them
            if k not in STAT_OF.values():
                del st[k]
    E["crop"] = dict(from_bbox=E["bbox"], to_bbox=[w, s, e, n],
                     how="layer PNGs cut to the box; km² = full-box km² × share of the layer's pixels inside it")
    E["bbox"] = [w, s, e, n]
    h = E.get("headline", {})
    row = next((r for r in E.get("timeline", []) if r["date"] == h.get("date")), None)
    if row and row["stats"]:
        st = row["stats"]
        h["numbers"] = [dict(label="Official map: flood", value=st.get("gfm_flood", 0), unit="km²"),
                        dict(label="NISAR adds, in the blank", value=st.get("nisar_adds", 0), unit="km²")]
        h["sentence"] = (f"On {h['date']}, NISAR found {st.get('nisar_adds', 0):g} km² of water where the official flood "
                         f"map (Copernicus GFM) says it cannot see, in the flooded plain.")
    (root / "event.json").write_text(json.dumps(E, indent=1, ensure_ascii=False), encoding="utf-8")
    print(eid, "→", E["bbox"], {f"{k}@{d}": round(v, 2) for (k, d), v in share.items()}, h.get("numbers"))


if __name__ == "__main__":
    main(sys.argv[1], *map(float, sys.argv[2:6]))
