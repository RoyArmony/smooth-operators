# Unseen Earth — Smooth Operators, NASA Space Apps Challenge 2026

Team **Smooth Operators** at the [NASA Space Apps Challenge 2026](https://www.spaceappschallenge.org/2026/), Haifa (Technion), Nov 14–15.

- **Live site:** https://unseenearth.us
- **Team:** Roy Armony, Shai Yehezkel, Noa Shoham
- **Challenge:** [Dancing with the SARs](https://www.spaceappschallenge.org/2026/challenges/dancing-with-the-sars/): an interactive
  app that uses radar data from the NASA-ISRO NISAR mission to track and visualize surface change around the world.

## What it does

Today's official flood map (Copernicus GFM, Sentinel-1 C-band) goes blank ("cannot see") under forests and towns.
NASA-ISRO **NISAR**'s L-band radar sees through the leaves. We keep the official map as it is and add the water NISAR
finds inside its blank, pass by pass, on 16 flood sites (Jun–Oct 2026). Canada's RCM radar and NASA's OPERA DSWx check it;
RADARSAT-1 and Sentinel-1 show the years before.

- **Method:** NISAR L2 GCOV (HH + HV, 80 m) → per-scene threshold (Martinis et al. 2015), dry-season change, HV and GUNW
  coherence → water; NISAR water ∩ GFM "cannot see" = what NISAR adds. Details on the site's **Science** page and in
  [`docs/07`](docs/07-Plan-algorithm.md), results in [`docs/10`](docs/10-Results.md).
- **Limits:** candidate water, not checked on the ground; NISAR products are still PROVISIONAL; 16 chosen sites, not a global total.

## Repo layout

| Folder | What |
|---|---|
| [`site/`](site/), [`index.html`](index.html) | The static site: Home → Story (film) → Explorer (map viewer) → Science |
| [`events/`](events/) | Flood bundles the site reads (PNG layers + `event.json`), written by the pipeline |
| [`pipeline/`](pipeline/) | Python package `unseen`: NISAR → water → gap vs GFM → bundles. See [`pipeline/README.md`](pipeline/README.md) |
| [`scripts/`](scripts/) | One-off helpers: bundle checks, story pictures, land-cover breakdown of the blank |
| [`docs/`](docs/) | Plan, method, data, design and results notes (01–13) |

## Data, references and AI use

- **Data and tools we used** (with how to get each): [`docs/04-Sources-and-tools.md`](docs/04-Sources-and-tools.md).
- **Credits and licences:** [`ACKNOWLEDGMENTS.md`](ACKNOWLEDGMENTS.md). NASA data: NISAR (NASA/JPL-Caltech and ISRO, ASF DAAC),
  OPERA DSWx, HLS, LANCE, GIBS. CSA data: RCM, RADARSAT-1. Our maps are derived products, not official NASA products.
- **AI use:** we used Claude Code (Anthropic) as a coding, research and writing assistant. Commits it helped with carry a
  `Co-Authored-By: Claude` trailer. The idea, the study sites, the method choices and the validation are the team's,
  and we reviewed the AI-assisted code. Maps and pictures on the site are computed from satellite data by our code;
  no AI-generated images, video or audio. Details: [docs/03](docs/03-Citation-and-AI.md#ai-disclosure).

## License

- Code: [MIT](LICENSE).
- Third-party data, imagery, software and papers keep their own terms: [ACKNOWLEDGMENTS.md](ACKNOWLEDGMENTS.md).
  Bundled Leaflet keeps its licence file next to it.
