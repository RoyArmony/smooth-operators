"""Restyle the official map's "cannot see" area from grey hatch to the site's violet hatch (docs/11-Design.md).

1. site/story/tonlesap/gfm_excluded_violet.png: violet tint + white 45° lines, from the GFM exclusion mask (film layer).
2. site/story/world/thumbs/*.jpg: the film's site thumbnails, grey hatch pixels recoloured to violet/white in place
   (originals are in git history).

Run from the repo root:  python scripts/violet_blank.py
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "site" / "story"
VIOLET = np.array([70, 52, 120])      # tint, as rgba(70,52,120,.6) on Home
LINE = np.array([236, 238, 248])      # hatch lines


def layer() -> None:
    a = np.asarray(Image.open(STORY / "tonlesap" / "gfm_excluded.png").convert("RGBA"))
    m = a[..., 3] > 0
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    line = ((xx - yy) % 20) < 5                                   # 135° lines; ~6 px apart at the film's zoom
    out = np.zeros(a.shape, np.uint8)
    out[..., :3] = np.where(line[..., None], LINE, VIOLET)
    out[..., 3] = np.where(m, np.where(line, 220, 150), 0)
    Image.fromarray(out).save(STORY / "tonlesap" / "gfm_excluded_violet.png", optimize=True)


def thumbs() -> None:
    for p in sorted((STORY / "world" / "thumbs").glob("*.jpg")):
        a = np.asarray(Image.open(p).convert("RGB")).astype(float)
        mx, mn = a.max(-1), a.min(-1)
        grey = (mx - mn < 28) & (mx > 58)                          # hatch pixels: light-grey stripes on dark grey
        t = np.clip((mx - 58) / (200 - 58), 0, 1)[..., None]
        col = VIOLET * (1 - t) + LINE * t
        out = np.where(grey[..., None], col, a).clip(0, 255).astype(np.uint8)
        Image.fromarray(out).save(p, quality=90)


if __name__ == "__main__":
    layer()
    thumbs()
    print("done")
