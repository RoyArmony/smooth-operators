"""Story film / Home pictures from the current bundles (no new analysis: layers are copied or resampled).

    python scripts/story_layers.py tonle      # site/story/tonlesap/nisar_added.png + nisar_adds_edge.png (Tonle Sap, 17 Oct)
    python scripts/story_layers.py thumbs     # site/story/world/thumbs/<site>.jpg (GFM flood, "cannot see", NISAR adds)
    python scripts/story_layers.py canada     # site/story/canada/{nisar_water,rcm_water,agree}.png + pad.json (Peace-Athabasca)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
EV, STORY = ROOT / "events", ROOT / "site" / "story"
ORANGE, EDGE = (255, 150, 40, 245), (255, 154, 46, 255)


def mask(path):
    return np.array(Image.open(path).convert("RGBA"))[..., 3] > 0


def resample(m, src, dst, size):
    """Nearest resample of a lat/lon mask from bounds src [[s,w],[n,e]] to dst bounds at size (W, H)."""
    (s0, w0), (n0, e0) = src
    (s1, w1), (n1, e1) = dst
    W, H = size
    lon = w1 + (np.arange(W) + .5) * (e1 - w1) / W
    lat = n1 - (np.arange(H) + .5) * (n1 - s1) / H
    c = np.floor((lon - w0) / (e0 - w0) * m.shape[1]).astype(int)
    r = np.floor((n0 - lat) / (n0 - s0) * m.shape[0]).astype(int)
    ok = (c[None] >= 0) & (c[None] < m.shape[1]) & (r[:, None] >= 0) & (r[:, None] < m.shape[0])
    return m[np.clip(r, 0, m.shape[0] - 1)[:, None], np.clip(c, 0, m.shape[1] - 1)[None]] & ok


def rgba(m, col):
    a = np.zeros(m.shape + (4,), np.uint8); a[m] = col
    return Image.fromarray(a)


def tonle():
    E = json.loads((EV / "tonle-sap-flood-pulse-2026" / "event.json").read_text())
    lay = E["layers"]["nisar_adds"]
    m = mask(EV / "tonle-sap-flood-pulse-2026" / lay["files"]["2026-10-17"])
    edge = ndi.binary_dilation(m, np.ones((3, 3))) & ~ndi.binary_erosion(m, np.ones((3, 3)))
    rgba(edge, EDGE).save(STORY / "tonlesap" / "nisar_adds_edge.png", optimize=True)        # same bounds as the layer
    B = [[12.3005, 103.5949], [13.2994, 104.7009]]                                          # landing.html B
    size = Image.open(STORY / "tonlesap" / "gfm_flood.png").size
    rgba(resample(m, lay["bounds"], B, size), ORANGE).save(STORY / "tonlesap" / "nisar_added.png", optimize=True)
    print("tonle: NISAR adds 17 Oct:", E["timeline"][[t["date"] for t in E["timeline"]].index("2026-10-17")]["stats"]["nisar_adds"], "km²")


THUMBS = {"tonle-sap": "tonle-sap-flood-pulse-2026", "inner-niger-delta-mali": "inner-niger-delta-mali",
          "mekong-delta-vietnam": "mekong-delta-vietnam", "irrawaddy-delta-myanmar": "irrawaddy-delta-myanmar",
          "congo-cuvette-centrale": "congo-cuvette-centrale"}


def thumbs():
    for key, eid in THUMBS.items():
        E = json.loads((EV / eid / "event.json").read_text())
        d = E["headline"]["date"]
        L = {k: mask(EV / eid / E["layers"][k]["files"][d]) for k in ("gfm_excluded", "gfm_flood", "nisar_adds")}
        H, W = L["gfm_flood"].shape
        a = np.zeros((H, W, 3), np.uint8); a[:] = (22, 28, 34)
        yy, xx = np.mgrid[:H, :W]
        ex = L["gfm_excluded"]
        a[ex] = (70, 72, 82); a[ex & ((xx + yy) % 6 < 2)] = (150, 150, 160)
        a[L["gfm_flood"]] = (40, 130, 255)
        a[L["nisar_adds"]] = (255, 150, 40)
        s = min(H, W) // 2                                         # centre crop, half the box: detail at thumbnail size
        im = Image.fromarray(a[(H - s) // 2:(H + s) // 2, (W - s) // 2:(W + s) // 2]).resize((240, 240), Image.NEAREST)
        im.save(STORY / "world" / "thumbs" / f"{key}.jpg", quality=85)
        print("thumb", key, d)


def canada():
    base = EV / "peace-athabasca-delta" / "2026-06-flood"
    E = json.loads((base / "event.json").read_text())
    rd = sorted(E["layers"]["rcm_water"]["files"])
    d = next((x for x in rd if x.startswith("2026-07")), rd[0])    # the July pair (Home: "Jul 2026")
    for k, out in (("nisar_open", "nisar_water"), ("rcm_water", "rcm_water"), ("agreement", "agree")):
        lay = E["layers"][k]
        f = lay["files"].get(d) or lay["files"][min(lay["files"], key=lambda x: abs(int(x.replace("-", "")) - int(d.replace("-", ""))))]
        Image.open(base / f).save(STORY / "canada" / f"{out}.png", optimize=True)
    (s, w), (n, e) = E["layers"]["agreement"]["bounds"]
    json.dump({"corners": [[w, n], [e, s]]}, open(STORY / "canada" / "pad.json", "w"))
    print("canada: RCM day", d)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        dict(tonle=tonle, thumbs=thumbs, canada=canada)[a]()
