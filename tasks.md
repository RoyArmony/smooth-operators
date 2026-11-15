# Tasks

Team task list. Tick a box when done. Add your name in brackets when you take a task, e.g. `[Shai]`.
Hackathon dates, rules and deadlines: [docs/01-Competition.md](docs/01-Competition.md). Submission: [docs/02](docs/02-Submission-guide.md).

## Flood Explorer build (Nov 14–15)

Plan: [05 overview](docs/05-Flood-plan.md) · [06 architecture](docs/06-Plan-architecture.md) · [07 algorithm](docs/07-Plan-algorithm.md) · [08 data](docs/08-Plan-data.md) · [09 UI](docs/09-Plan-UI.md).
P0 = must, P1 = should, P2 = nice. Times are Israel time. Sync points: **Sat 20:30** contract freeze · **Sun 01:00** first real story live · **Sun 13:00** feature freeze.

### All three
- [ ] [All] Sat 19:00 — agree the plan; decide story order, GoDaddy owner, new folders (`site/`, `events/`, `pipeline/`, `scripts/`), story 2 (Inner Niger or Mekong) (docs/05 §6)
- [ ] [All] Sat 20:30 — freeze bundle contract v1 (docs/08 §3); after this only add optional fields
- [ ] [All] Every number we show gets an audit line in `docs/10-Results.md` (script, input, date)
- [ ] [All] Sun 13:00 — feature freeze; only fixes after this
- [ ] [All] Sun 15:00 — full run-through of the demo on the GoDaddy domain, on a laptop and a phone

### Roy — site and integration
- [x] [Roy] P0 Sat 20:00 — `.vercelignore`: add `!site/` and `!events/`; check a preview deploy (live: `events/` served, `docs/` and `tasks.md` 404)
- [x] [Roy] P0 — Domain DNS, set at **Porkbun** (its nameservers), not GoDaddy (Roy does it by hand): add the domain in Vercel → Settings → Domains; in GoDaddy set A `@` → `76.76.21.21`, CNAME `www` → `cname.vercel-dns.com` (or the values Vercel shows); remove the parked record
- [x] [Roy] P0 Sat 20:30 — `events/schema.json` + `scripts/check_bundle.py` (schema, files exist, PNG ≤ 2048 px, total < 20 MB); matches Shai's `bundle.py`
- [x] [Roy] P0 Sat 20:30 — mock bundles (placeholder layers for 2 stories) so the site can be built before real data (`scripts/make_mock_bundles.py`; `"mock": true`, delete when real bundles land)
- [ ] [Roy] P0 Sat 23:00 — app skeleton: one page, Leaflet map, world view with dots from `index.json`, hash routing `#e=<id>&t=<date>`
- [ ] [Roy] P0 Sun 01:00 — event view: fly to box, default layers, 3 numbers + sentence + badge from `event.json`, back button / Esc
- [ ] [Roy] P0 Sun 09:00 — layers panel: groups, on/off, opacity, legend, sensor + date + source link
- [ ] [Roy] P0 Sun 10:00 — science drawer: tabs (Method, Data, Validation, Limits, Sources) rendering `methods.md` + `science.md`
- [ ] [Roy] P1 Sun 11:00 — time play over NISAR passes (preload next pass; numbers update; gaps shown)
- [ ] [Roy] P1 Sun 11:00 — then/now swipe (RADARSAT-1 vs NISAR)
- [x] [Roy] P1 Sun 12:00 — custom domain works over HTTPS; vercel.app kept as backup link
- [ ] [Roy] P1 Sun 14:00 — polish: phone layout, hatch on grey "cannot see", photo date shown, loading states
- [ ] [Roy] P1 Sun 16:00 — 30 s screen recording of the demo (backup for the video part)
- [ ] [Roy] Sun 21:00 — submission: Final Project Link; check it went through

### Noa — science and algorithm
- [ ] [Noa] P0 Sat 22:00 — pick one fixed date per story (no best pass) with each story owner; record in `docs/10-Results.md`
- [ ] [Noa] P0 Sat 23:00 — one shared method for all stories: detector settings, GFM ±2 d match, `adds = NISAR ∩ GFM excluded ∩ valid`, area = pixels × 80 m × 80 m (docs/07)
- [ ] [Noa] P1 Sun 10:00 — combined map layer (GFM flood ∪ NISAR adds), same code for every story
- [ ] [Noa] P0 Sun 10:00 — `events/methods.md`: pipeline, detector rules, equations, physics (dark water, double bounce)
- [ ] [Noa] P0 Sun 11:00 — validation page: EDEN table, RCM agreement, plausibility (wet % over time), GFM agreement; one screen
- [ ] [Noa] P0 Sun 12:00 — limits text: lower bounds, best-pass vs fixed date, no forest ground truth, provisional products
- [ ] [Noa] Sun 14:00 — audit all app numbers against `docs/10-Results.md`; fix what the app reveals
- [ ] [Noa] Sun 20:00 — submission: Project Details (how it works, tools, limitations) + Data & AI Disclosure

### Shai — data pipeline, bundles and pitch
- [ ] [Shai] P0 Sat 23:00 — `pipeline/unseen/bundle.py`: GeoTIFF/stats → `events/<id>/` (PNG layers + `event.json`), passes `check_bundle.py`
- [ ] [Shai] P0 Sun 00:30 — world bundle: 16 floods, km² added per site, +43% total, labelled "best pass" (`index.json`)
- [ ] [Shai] P1 Sun 11:00 — per-pass stats in `timeline` (wet %, km²) for the play button, all stories
- [ ] [Shai] P2 — people in the added area (WorldPop) and land-cover split as context layers
- [ ] [Shai] P2 — daily live job (GitHub Action): GDACS floods → NISAR pass → bundle → commit; Earthdata secret in Actions secrets
- [ ] [Shai] P0 Sun 17:00 — 7-slide deck (problem → NASA data → method → result → validation → CSA → impact)
- [ ] [Shai] P0 Sun 18:00 — deck emailed to the Haifa organizers
- [ ] [Shai] Sun 20:00 — submission: High-Level Summary and References (from `docs/04`, `ACKNOWLEDGMENTS.md`, git history)

### One flood story each (owner makes the bundle + `science.md` for it)
Each owner runs the shared method (Noa) through `bundle.py` (Shai) and checks it in the site (Roy).
- [ ] [Roy] **Peace–Athabasca Delta, Canada** (CSA): ~~P0 Sat 20:00 RADARSAT-1 coverage check~~ ✅ done: 619 scenes 1996–2013, 359 cover ≥ 90% of the box ([docs/10](docs/10-Results.md), `scripts/rs1_coverage.py`) · P0 Sun 01:00 NISAR + RCM same week + agreement layer, 79% / IoU · P1 RADARSAT-1 then layer · P1 verify CSA credit lines in `ACKNOWLEDGMENTS.md`
- [ ] [Noa] **Inner Niger Delta, Mali** (or Mekong, Vietnam): P0 Sun 09:00 GFM flood, "cannot see", NISAR adds, photo; passes Jul–Oct · `science.md`
- [x] [Noa] **Mekong delta, Vietnam** (story 2): flood history case in the Explorer, RADARSAT-1 1998–2007 + NISAR 2026, flood per image vs GFM (`python -m unseen.history`)
- [x] [Noa] Mekong history bundle in `events/mekong-delta-history/` (rs1_water, agreement vs GFM, rs1_rgb for the then/now swipe)
- [ ] [Shai] **Tonle Sap, Cambodia**: P0 Sun 01:00 GFM flood, "cannot see", NISAR adds, DSWx-S1, photo; passes Jun–Oct · `science.md`
