"""Write placeholder ("mock") bundles to events/ so the site can be built before real data.

    python scripts/make_mock_bundles.py

Every number is 0 and every layer is a fake blob marked MOCK. Each event.json has "mock": true.
Real bundles from pipeline/unseen/bundle.py replace these; delete a mock folder when its real bundle lands.
Needs Pillow.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent / "events"
PX = 512

STORIES = [
    {
        "id": "peace-athabasca-2026",
        "title": "Peace–Athabasca Delta, Canada",
        "place": "Alberta, Canada",
        "bbox": [-112.0, 58.3, -110.8, 59.0],
        "sentence": "MOCK: Canada's RCM radar checks NISAR's water, the same week.",
        "numbers": [("RCM agrees", "%"), ("NISAR water", "km²"), ("since 1998", "km²")],
        "badge": "Independent radar check",
        "dates": ["2026-09-28", "2026-10-10"],
        "layers": {
            "photo": ("base", "HLS", "#ffffff", True),
            "nisar_water": ("result", "NISAR", "#1e90ff", True),
            "rcm_water": ("validation", "RCM", "#3aa0ff", False),
            "agreement": ("validation", "NISAR + RCM", "#2ecc71", False),
            "rs1_rgb": ("radar", "RADARSAT-1", "#c0c0c0", False),
        },
    },
    {
        "id": "tonle-sap-2026",
        "title": "Tonle Sap, Cambodia",
        "place": "Cambodia",
        "bbox": [103.6, 12.3, 104.7, 13.3],
        "sentence": "MOCK: NISAR sees flood water under the forest that the official map leaves blank.",
        "numbers": [("Official map", "km²"), ("NISAR adds", "km²"), ("More water", "%")],
        "badge": "Checked against optical and elevation",
        "dates": ["2026-08-20", "2026-09-13", "2026-10-07"],
        "layers": {
            "photo": ("base", "HLS", "#ffffff", True),
            "gfm_flood": ("official", "Sentinel-1 (GFM)", "#5dade2", True),
            "gfm_excluded": ("official", "Sentinel-1 (GFM)", "#808080", True),
            "nisar_adds": ("result", "NISAR", "#ff3b30", True),
        },
    },
]

COLORS = {"#ffffff": (230, 230, 230), "#1e90ff": (30, 144, 255), "#3aa0ff": (58, 160, 255),
          "#2ecc71": (46, 204, 113), "#c0c0c0": (192, 192, 192), "#5dade2": (93, 173, 226),
          "#808080": (128, 128, 128), "#ff3b30": (255, 59, 48)}


def mock_png(path, color, seed):
    img = Image.new("RGBA", (PX, PX), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = COLORS[color]
    for k in range(5):
        x = (seed * 97 + k * 131) % (PX - 160)
        y = (seed * 53 + k * 89) % (PX - 160)
        d.ellipse([x, y, x + 80 + k * 15, y + 60 + k * 10], fill=(r, g, b, 150))
    d.text((8, 8), "MOCK", fill=(255, 255, 255, 220))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


def main():
    index = {"version": 1, "mock": True, "events": []}
    for n, s in enumerate(STORIES):
        w, so, e, no = s["bbox"]
        bounds = [[so, w], [no, e]]
        out = ROOT / s["id"]
        layers = {}
        for i, (lid, (group, sensor, color, default)) in enumerate(s["layers"].items()):
            files = {}
            for j, date in enumerate(s["dates"]):
                rel = f"layers/{lid}_{date}.png"
                mock_png(out / rel, color, seed=n * 31 + i * 7 + j)
                files[date] = rel
            layers[lid] = {"group": group, "sensor": sensor, "legend": color,
                           "files": files, "bounds": bounds, "default": default}
        numbers = [{"label": lab, "value": 0, "unit": unit} for lab, unit in s["numbers"]]
        event = {
            "id": s["id"], "title": s["title"], "place": s["place"], "kind": "story", "mock": True,
            "bbox": s["bbox"],
            "headline": {"date": s["dates"][-1], "sentence": s["sentence"], "numbers": numbers,
                         "badge": {"text": s["badge"], "ref": "validation"}},
            "timeline": [{"date": d, "stats": {}, "layers": list(layers)} for d in s["dates"]],
            "layers": layers,
            "validation": {},
            "sources": [{"name": "MOCK", "url": "https://example.com", "credit": "Placeholder, not real data"}],
        }
        (out / "event.json").write_text(json.dumps(event, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "science.md").write_text(f"# {s['title']}\n\nMOCK bundle. Real science text comes with the real bundle.\n",
                                        encoding="utf-8")
        index["events"].append({"id": s["id"], "title": s["title"], "place": s["place"], "date": s["dates"][-1],
                                "bbox": s["bbox"], "kind": "story", "mock": True,
                                "headline": {"sentence": s["sentence"], "numbers": numbers}})
    (ROOT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(STORIES)} mock bundles to {ROOT}")


if __name__ == "__main__":
    main()
