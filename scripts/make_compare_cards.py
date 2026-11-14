"""Before/after image pairs for the Home page card: official flood map vs + NISAR.

For each site writes site/story/compare/<key>_map.jpg (official map: GFM flood + "cannot see" hatch)
and <key>_nisar.jpg (same + NISAR water in the blank, orange).

- Tonle Sap: built from the full-size story layers in site/story/tonlesap/ (photo + GFM + mask + NISAR adds).
- Other sites: only the small finished thumbnails exist (site/story/world/thumbs/, made by Shai's pipeline).
  The orange NISAR pixels are found by hue and painted over with the grey hatch to get the "official" image.
  Replace with full-size layers when they are available.

Run from the repo root:  python scripts/make_compare_cards.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "site" / "story"
OUT = STORY / "compare"
THUMB_SITES = ["inner-niger-delta-mali", "mekong-delta-vietnam", "irrawaddy-delta-myanmar", "congo-cuvette-centrale"]


def save(im: Image.Image, name: str) -> None:
    im.convert("RGB").save(OUT / name, quality=88, optimize=True)


def tonle_sap() -> None:
    d = STORY / "tonlesap"
    base = Image.open(d / "photo_2026-10-19.jpg").convert("RGB")
    size = base.size
    base = ImageEnhance.Color(ImageEnhance.Brightness(base).enhance(0.55)).enhance(0.8).convert("RGBA")
    lay = {k: Image.open(d / f"{k}.png").convert("RGBA").resize(size, Image.LANCZOS) for k in ["gfm_excluded", "gfm_flood", "nisar_added"]}
    off = Image.alpha_composite(Image.alpha_composite(base, lay["gfm_excluded"]), lay["gfm_flood"])
    save(off, "tonle-sap_map.jpg")
    save(Image.alpha_composite(off, lay["nisar_added"]), "tonle-sap_nisar.jpg")


def from_thumb(key: str) -> None:
    im = Image.open(STORY / "world" / "thumbs" / f"{key}.jpg").convert("RGB")
    im = im.resize((im.width * 2, im.height * 2), Image.LANCZOS)
    h, s, v = [np.asarray(c).astype(int) for c in im.convert("HSV").split()]
    orange = (h >= 6) & (h <= 38) & (s > 55) & (v > 45)
    mask = Image.fromarray((orange * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    a = np.asarray(im).astype(int)
    mx = a.max(-1)
    grey = (mx - a.min(-1) < 25) & ~orange & (mx > 60)              # the thumbnail's own "cannot see" hatch
    mid = float(np.median(mx[grey])) if grey.any() else 95.0
    yy, xx = np.mgrid[0:im.height, 0:im.width]
    stripe = ((xx + yy) % 5) < 2                                   # 45° hatch, like the film's "cannot see"
    hatch = np.where(stripe, mid + 28, mid - 22)[..., None] * np.array([1.0, 1.0, 1.06])
    m = np.asarray(mask)[..., None] > 0
    off = np.where(m, hatch, a).clip(0, 255).astype(np.uint8)
    save(Image.fromarray(off), f"{key}_map.jpg")
    save(im, f"{key}_nisar.jpg")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tonle_sap()
    for k in THUMB_SITES:
        from_thumb(k)
    for p in sorted(OUT.glob("*.jpg")):
        print(p.relative_to(ROOT), p.stat().st_size // 1024, "KB")
