# 05 · Flood Explorer: plan overview

**Noa, 14.11.26 18:09:14 says:** plan for the hackathon build (with Claude). Builds on Shai's flood work in
shadow repo `docs/26-Edge-and-validation.md` (GFM gap, +43%, RCM 79%) and Roy's three-radar test at Site C.
**Noa, 14.11.26 18:19:10 says:** update: serverless site (Vercel → GoDaddy domain), the app opens on the world view (not Tonle Sap),
plan split into pages.

| Page | What |
|---|---|
| **05 · Overview** (this) | pitch, stories, work split, timeline, decisions |
| [06 · Architecture](06-Plan-architecture.md) | serverless site, Vercel, GoDaddy domain, modules, offline pipeline |
| [07 · Algorithm](07-Plan-algorithm.md) | detector, gap vs official maps, validation, numbers |
| [08 · Data](08-Plan-data.md) | sources, common grid, event bundle contract |
| [09 · UI design](09-Plan-UI.md) | screens, layers, time play, science drawer |

Each page ends with **Drawbacks**: what is weak, and what we do about it.

---

## 1. The pitch in one line

**Official flood maps leave the forest blank. NISAR fills it, Canada's radars check it.**

| Judges look for | Our answer |
|---|---|
| Problem | Flood maps used by responders (Copernicus **GFM** / GloFAS, NASA **OPERA DSWx-S1**, NASA LANCE MODIS/VIIRS) are blind under cloud (optical) and under dense vegetation (C-band). GFM marks that area "cannot see". |
| NASA data | NISAR L2 GCOV (L-band, HH/HV); OPERA DSWx-S1; HLS optical. |
| Method | NISAR water + flooded-vegetation detector → keep what falls in the official map's blank → **official + NISAR = fuller flood map** ([07](07-Plan-algorithm.md)). |
| Result | Across 16 floods in 2026: **+1,182 km², +43%** over the official map. |
| Validity | CSA **RCM** same week (79%), USGS EDEN gauges (precision 0.95–1.00), **RADARSAT-1** for the long-term record. |

---

## 2. Order of the story (first view = the world, not one site)

The app and the pitch open on the **global problem**: a world map of 16 floods, each official map's blank in grey,
and one number: **+43%**. Then the stories. (Matches Shai's updated film, which also starts from the global maps and their
blanks.)

| # | Story | Now (2026) | Over time | Checked by |
|---|---|---|---|---|
| 0 | **World: 16 floods** | +1,182 km² in the blank, +43% | Jun → Oct 2026 | summary of all checks |
| 1 | **Peace–Athabasca Delta, Canada** | NISAR vs RCM same week: 79% agree | RADARSAT-1 (1996–2013) vs NISAR 2026, then/now swipe | RCM (independent radar) |
| 2 | **Inner Niger Delta, Mali** (or **Mekong**, Vietnam) | +253 km² to GFM's 51 (Mekong: +170, mostly farmland) | flood rising Jul → Oct | optical on clear days |
| 3 | **Tonle Sap, Cambodia** | GFM 554 km², NISAR adds 561 (×2) | flood pulse Jun → Oct, play button | timing, elevation, land cover, DSWx-S1 |
| Live | current GDACS floods | same pipeline, daily | – | labelled "not yet validated" |

Why this order: it leads with the problem and with validation (CSA data), then shows the effect grows where forests
flood. Tonle Sap stays the strongest number but is not the opener. Team can still swap 1 ↔ 3 (§6).

---

## 3. Work split

**Noa, 14.11.26 18:32:52 says:** update: Roy = site and integration, Noa = science and algorithm, Shai = data pipeline,
bundles and pitch. **Each of us also owns one flood story** end to end. Task list: `tasks.md` → Flood Explorer build.

| | **Roy** (site + integration) | **Noa** (science + algorithm) | **Shai** (data pipeline + pitch) |
|---|---|---|---|
| Owns | [06](06-Plan-architecture.md), [09](09-Plan-UI.md), `index.html` + `site/`, bundle schema, Vercel + GoDaddy | [07](07-Plan-algorithm.md), `methods.md`, validation, limits, number audit | `bundle.py`, world bundle, timeline stats, live job, deck |
| Flood story | **Peace–Athabasca** (RCM, RADARSAT-1, CSA) | **Inner Niger** (or Mekong) | **Tonle Sap** |
| Tonight | DNS; schema + checker + mock bundles; app skeleton; RADARSAT-1 coverage check | fixed dates; shared method | `bundle.py`; world bundle; Tonle Sap bundle |
| Sat morning | layers, science drawer, play, swipe, domain | combined map; `methods.md`; validation page; Inner Niger bundle | timeline stats; P2 context layers / live job |
| Sat afternoon | polish, phone, 30 s video | audit numbers; limits | deck → email 18:00 |
| Evening | Final link | Project Details, Disclosure | Summary, References |

Sync points: 20:30 contract freeze, 01:00 first real bundle live on vercel.app, 13:00 feature freeze.

## 4. Timeline (Israel time)

| When | Milestone |
|---|---|
| Fri 20:30 | Contract v1 frozen; empty site live on `*.vercel.app`; GoDaddy DNS set (needs hours to spread) |
| Sat 01:00 | **P0**: world view + one real story on vercel.app |
| Sat 11:00 | **P1**: 3 stories, time play, science drawer; custom domain works |
| Sat 13:00 | Feature freeze |
| Sat 18:00 | Deck emailed |
| Sat 22:00 | Submitted (hard deadline 23:59) |

- **P0:** world view, event list, event view (3 numbers + sentence), GFM / NISAR adds / photo layers, back, 2 stories, science text, public link.
- **P1:** time play, then/now swipe (RADARSAT-1), story 3, RCM agreement layer, validation charts, custom domain.
- **P2:** live GDACS floods (daily job), COG downloads, people affected, ALOS "then" at Tonle Sap, SWOT check.

## 5. Drawbacks of the whole plan

- **Not live analysis.** Serverless means results are computed before, offline. A user can't draw a new area and get a NISAR answer on the site. We show "processed" events plus a daily job. ([06](06-Plan-architecture.md))
- **The detector is not ours long-term.** NASA's DSWx-NI will publish NISAR water maps. Our lasting value is the gap vs official maps and the checks. ((shadow repo docs/26 §2))
- **Numbers are lower bounds** (low recall in marsh) and **forest extent has no ground truth yet**. ([07](07-Plan-algorithm.md))
- **Validation sites ≠ headline sites.** RCM never imaged Tonle Sap; the 79% is from Canada's marsh, not from flooded forest.
- **Tight time:** ~28 h left, three people. The flood film (shadow repo `web/landing-flood.html`) is the fallback demo.
- **Two hosts, two accounts** (Vercel + GoDaddy): one more thing that can break on demo day. Test the domain Saturday morning.

## 6. Decisions for the team

1. Story order: Peace–Athabasca first (recommended, CSA + validation) or Tonle Sap first after the world view.
2. Map library: keep **Leaflet** (recommended) vs MapLibre GL ([09](09-Plan-UI.md)).
3. Commit curated bundles in `events/` (< 20 MB) so the serverless site has its data ([08](08-Plan-data.md)).
4. GoDaddy domain owner (Vercel already deploys this repo) and the new folders `site/`, `events/`, `pipeline/`, `scripts/` ([06 §3b](06-Plan-architecture.md)).
5. Story 2: Inner Niger (bigger gain) or Mekong (farms, people).
