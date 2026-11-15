// In-map analysis: open an analysed area ON the globe (no page change), so scale and context stay.
// A floating panel steps through NISAR passes; the radar / optical photo and the change overlay are draped on the map.
// Deep link: index.html#site=<id>. The full page (site.html) is still there for swipe and pixel history.
(() => {
const $ = id => document.getElementById(id), map = window.UNSEEN_MAP;
map.createPane('analysis').style.zIndex = 350;                 // above map tiles (200), below markers/popups
const fmt = (d, o = { day: 'numeric', month: 'short' }) => new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { ...o, timeZone: 'UTC' });
const dn = d => Date.parse(d + 'T00:00:00Z') / 864e5;
let S = null;

const panel = document.createElement('div');
panel.id = 'sp'; panel.hidden = true;
panel.innerHTML = `
  <div class="sph"><div class="spsteps" id="spS"></div><button id="spX" title="Minimize">–</button></div>
  <div class="spbody">
    <div class="legend sub" id="spL"></div>
    <div class="spch"><span id="spD"></span><span class="spkey" id="spK"></span></div>
    <canvas id="spC" title="Water per pass. Click or drag to change the date (← → keys too)."></canvas>
    <div class="spnav"><button id="spBk">← Back</button><button id="spNx" class="primary"></button></div>
  </div>`;
$('leftcol').appendChild(panel);
L.DomEvent.disableClickPropagation(panel); L.DomEvent.disableScrollPropagation(panel);

async function openSite(id) {
  closeSite('swap');
  if (id.startsWith('ev-')) return openBundle(id.slice(3));
  if (id.startsWith('hist-')) return openHistory(id.slice(5));
  const base = `sites/${encodeURIComponent(id)}/`;
  let D; try { D = await (await fetch(base + 'site.json', { cache: 'no-cache' })).json(); } catch (e) { return; }
  const A = n => (D.assets && D.assets[n]) || base + n;
  const [[w, n], [e, s]] = D.corners, B = L.latLngBounds([[s, w], [n, e]]);
  const photos = Object.entries(D.photos || {}).sort();
  const nw = x => x.new_water ?? x.nisar_water ?? 0, hid = x => x.hidden_new ?? x.hidden_clouds ?? 0;
  const peak = D.summary.reduce((b, x, i) => nw(x) > nw(D.summary[b]) ? i : b, 0);
  S = { id, D, A, B, photos, nw, hid, t: D.hazard && ['WF', 'VO', 'EQ'].includes(D.hazard) ? D.frames.length - 1 : peak, b: 'nisar',
        base: L.imageOverlay('data:,', B, { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map),   // hidden until a step uses it (no raw-radar flash while loading)
        over: L.imageOverlay('data:,', B, { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map),
        box: L.rectangle(B, { pane: 'analysis', color: '#ff7828', weight: 1.5, fill: false, opacity: 0, interactive: false }).addTo(map),
        tag: L.marker([B.getSouth(), B.getCenter().lng], { interactive: false, keyboard: false, icon: L.divIcon({ className: 'sptag', html: '<span></span>', iconSize: [0, 0] }) }).addTo(map) };   // which satellite, under the outline
  const N = D.frames.length, cal = D.calibration && D.calibration.used ? D.calibration : null;
  const f1 = cal ? cal.loo.map(x => x.f1) : (D.validation || []).map(x => x.f1);
  const R = D.report || {};
  S.layers = (R.layers || []).map(l => ({ ...l, ov: L.imageOverlay(A(l.file), L.latLngBounds([[l.corners[1][1], l.corners[0][0]], [l.corners[0][1], l.corners[1][0]]]),
    { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map) }));
  S.P = R.pairs && R.pairs.list && R.pairs.list.length ? R.pairs : null;
  if (S.P) {
    const pb = S.P.corners, PB = L.latLngBounds([[pb[1][1], pb[0][0]], [pb[0][1], pb[1][0]]]), o = { pane: 'analysis', interactive: false, opacity: 0 };
    S.mo = L.imageOverlay(A(S.P.list[0].motion), PB, o).addTo(map); S.fr = L.imageOverlay(A(S.P.list[0].fringes), PB, o).addTo(map);
  }
  S.ev = []; if (!D.history) try {          // history cases draw their own per-image overlay (site.json)
    const eid = id.replace(/-\d+-\d+$/, ''), E = await (await fetch(`../../events/${eid}/event.json`, { cache: 'no-cache' })).json();
    const ORDER = ['gfm_flood', 'gfm_excluded', 'both_blind', 'nisar_water', 'nisar_adds'];
    S.evE = E;                                                       // its timeline: each pass's own km²
    S.ev = Object.entries(E.layers || {}).sort((a, b) => (ORDER.indexOf(a[0]) + 1 || 99) - (ORDER.indexOf(b[0]) + 1 || 99))
      .map(([k, l]) => ({ k, l, base: `../../events/${eid}/`, ov: L.imageOverlay('data:,', L.latLngBounds(l.bounds), { pane: 'analysis', interactive: false, opacity: 0, className: k === 'gfm_excluded' ? 'excl' : '' }).addTo(map) }));
  } catch (e) { S.ev = []; }
  S.official = S.ev.some(x => x.k === 'gfm_flood');
  if (S.official) {                         // keep only passes with all three: optical photo (± 60 d), official map and NISAR (± 6 d)
    const fs = k => Object.keys(((S.ev.find(x => x.k === k) || {}).l || {}).files || {}), near = (L, d, g) => L.some(x => Math.abs(dn(x) - dn(d)) <= g);
    const G = fs('gfm_flood'), Ad = fs('nisar_adds');
    const keep = D.frames.map((f, i) => near(G, f.date, 6) && (!Ad.length || near(Ad, f.date, 6)) && (!photos.length || near(photos.map(p => p[0]), f.date, 60)) ? i : -1).filter(i => i >= 0);
    if (keep.length && keep.length < D.frames.length) {
      const at = D.frames[S.t].date; D.frames = keep.map(i => D.frames[i]); D.summary = keep.map(i => D.summary[i]);
      S.t = D.frames.reduce((b, f, i) => Math.abs(dn(f.date) - dn(at)) < Math.abs(dn(D.frames[b].date) - dn(at)) ? i : b, 0);
    }
  }
  // the flow, as in the Story: the area → optical (clouds, canopy) → official radar map ("cannot see") → NISAR fills the blank
  const has = k => S.ev.some(x => x.k === k), E_ = ks => ks.filter(has).map(k => 'E_' + k);
  S.steps = [{ label: 'Area', b: 'none', on: [], cap: `The area${D.kind ? `: ${D.kind}` : ''}, ${fmt(D.frames[0].date, { month: 'short', year: 'numeric' })} → ${fmt(D.frames[D.frames.length - 1].date, { month: 'short', year: 'numeric' })}.` }];
  if (photos.length) S.steps.push({ label: 'Optical', b: 'photo', on: [], cap: 'Optical satellites: clouds and forest canopy hide the water.' });
  if (has('gfm_flood')) S.steps.push({ label: 'Official', b: 'none', on: E_(['gfm_flood', 'gfm_excluded', 'both_blind']),   // both-blind (Mekong) drawn here, not a step of its own
    cap: OFF.gfm.cap.replace('Grey', 'Hatched') + (has('both_blind') ? ' <b style="color:#d946ef">Magenta</b> = NASA’s optical map is blind under cloud too: only NISAR sees there.' : '') });
  S.steps.push(has('nisar_adds')
    ? { label: 'NISAR', b: 'none', on: E_(['gfm_flood', 'gfm_excluded', 'nisar_adds']), cap: 'NISAR’s L-band radar sees under the canopy. <b class="o">Orange</b> = flood found in the blank.' }
    : { label: D.history ? 'Radar' : 'NISAR', b: 'nisar', on: ['pass'], cap: D.history ? 'Radar through the years: RADARSAT-1 (CSA), then NISAR. Blue = flood.' : 'NISAR’s L-band radar sees through clouds. Dark = water.' });
  S.step = 0;
  if (id.startsWith('peace-athabasca')) try {       // Canada: NISAR vs the CSA's RCM radar, 3 days apart (same layers as the Story)
    const P = await (await fetch('../story/canada/pad.json')).json(), [[pw, pn], [pe, ps]] = P.corners;
    S.rcm = L.imageOverlay('../story/canada/agree.png', L.latLngBounds([[ps, pw], [pn, pe]]), { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map);
    S.extra = [...(S.extra || []), S.rcm];
    S.steps.push({ label: 'RCM', b: 'none', on: ['rcm'], t0: '2026-10-10', csa: true,
      cap: 'Canada’s RCM radar (CSA, C-band), 13 Oct vs NISAR 10 Oct: they agree on 79% of the water.' });
  } catch (e) {}
  await addChecks(id);
  if (S.steps.some(x => x.vs === 'rcm')) S.steps = S.steps.filter(x => x.label !== 'RCM' || x.vs);   // the RCM swipe replaces the old RCM step: one row of steps
  if (S.P && D.event_date) { const k = D.frames.findIndex(f => f.date >= D.event_date); if (k >= 0) S.t = k; }
  // volcano: vent + reference ring on the map, before / during interferograms side by side
  S.extra = S.extra || [];
  const V = R.volcano;
  if (V && V.vent) {
    const c = L.latLng(V.vent[0], V.vent[1]);
    S.extra.push(L.circle(c, { radius: (V.r_vent_km || 1) * 1000, color: '#fff', weight: 2, fill: false, pane: 'analysis', interactive: false }).addTo(map));
    if (V.r_ref_km) {
      S.extra.push(L.circle(c, { radius: V.r_ref_km[0] * 1000, color: '#fff', weight: 1, dashArray: '4 4', fill: false, pane: 'analysis', interactive: false }).addTo(map));
      S.extra.push(L.circle(c, { radius: V.r_ref_km[1] * 1000, color: '#fff', weight: 1, dashArray: '4 4', fill: false, pane: 'analysis', interactive: false }).addTo(map));
    }
  }
  panel.hidden = false;
  map.flyToBounds(B, { paddingTopLeft: [panel.offsetWidth + 70, 30], paddingBottomRight: [30, 30], duration: 1.2 });
  const S0 = S; map.once('moveend', () => S === S0 && S.box.setStyle({ opacity: 1 }));   // draw the outline once the camera lands (SVG is stretched mid-flight)
  setStep(0);
  window.dispatchEvent(new CustomEvent('unseen:site', { detail: id }));   // sidebar shows only this event (globe.js)
}

// ---------- independent checks (docs/12 §11): swipe another sensor | NISAR on the map, with % agreement ----------
// v2 flood folder of this place with "validation": left = RCM (CSA radar) or NASA DSWx (optical), right = NISAR
const VS = { rcm: { label: 'RCM', name: 'RCM (CSA)', radar: 'rcm_radar', water: 'rcm_water', c: '#ff6b6b', csa: true,
                    cap: 'Canada’s RCM radar (CSA, C-band) | NISAR, days apart. Drag the line: does the water match?' },
             dswx: { label: 'NASA', name: 'NASA DSWx', radar: 'photo', water: 'dswx_water', c: '#7fd1ff',
                     cap: 'NASA’s flood map (OPERA DSWx, optical) | NISAR. Drag the line. Grey = clouds.' } };
async function addChecks(id) {
  try {
    const IX = await (await fetch('../../events/index.json', { cache: 'no-cache' })).json();
    const pl = (IX.places || []).find(p => id.startsWith(p.id) && (p.validation || []).length);
    const fl = pl && [...(pl.floods || [])].filter(f => f.validation).sort((a, b) => b.flood_date.localeCompare(a.flood_date))[0];
    if (!fl) return;
    const base = `../../events/${pl.folder || pl.id}/${fl.id}/`, E = await (await fetch(base + 'event.json', { cache: 'no-cache' })).json();
    const o = { pane: 'analysis', interactive: false, opacity: 0 }, ov = () => L.imageOverlay('data:,', S.B, o).addTo(map);
    S.vs = { E, base, l1: ov(), l2: ov(), r1: ov(), r2: ov() };
    S.extra = [...(S.extra || []), S.vs.l1, S.vs.l2, S.vs.r1, S.vs.r2];
    Object.keys(VS).filter(k => E.validation && E.validation[k]).forEach(k => {
      const P = E.passes.filter(p => p.validation && p.validation[k]);
      const best = P.reduce((a, b) => (b.validation[k].compared_pct > a.validation[k].compared_pct ? b : a));
      S.steps.push({ label: VS[k].label, b: 'none', on: [], vs: k, t0: best.date, csa: VS[k].csa, cap: VS[k].cap });
    });
    const bar = S.vbar = document.createElement('div'); bar.className = 'swbar'; bar.hidden = true;
    bar.innerHTML = '<span class="swl"></span><b>⇔</b><span class="swr"></span>';
    map.getContainer().appendChild(bar); L.DomEvent.disableClickPropagation(bar);
    let drag = false;
    bar.onpointerdown = ev => { drag = true; bar.setPointerCapture(ev.pointerId); ev.preventDefault(); };
    bar.onpointermove = ev => { if (!drag) return; const r = map.getContainer().getBoundingClientRect(); S.vx = Math.max(0, Math.min(r.width, ev.clientX - r.left)); vclip(); };
    bar.onpointerup = bar.onpointercancel = () => { drag = false; };
    S.vclipEv = () => vclip(); map.on('move zoom zoomend moveend resize', S.vclipEv);
  } catch (e) { /* no v2 checks for this place */ }
}
function vclip() {                                      // left sensor keeps the left of the line, NISAR the right
  if (!S || !S.vs) return;
  const st = S.steps[S.step] || {}, on = !!st.vs, r = map.getContainer().getBoundingClientRect();
  if (!on) { S.vbar.hidden = true; [S.vs.l1, S.vs.l2, S.vs.r1, S.vs.r2].forEach(o => { const el = o.getElement(); if (el) el.style.clipPath = ''; }); return; }
  if (S.vx == null) S.vx = map.latLngToContainerPoint(S.B.getCenter()).x;   // start in the middle of the box
  S.vbar.hidden = !on; S.vbar.style.left = S.vx + 'px';
  const x = r.left + S.vx, cut = (o, keepLeft) => { const el = o.getElement(); if (!el) return;
    if (!on) { el.style.clipPath = ''; return; }
    const b = el.getBoundingClientRect(), p = Math.max(0, Math.min(100, (x - b.left) / Math.max(1, b.width) * 100));
    el.style.clipPath = keepLeft ? `inset(0 ${100 - p}% 0 0)` : `inset(0 0 0 ${p}%)`; };
  cut(S.vs.l1, true); cut(S.vs.l2, true); cut(S.vs.r1, false); cut(S.vs.r2, false);
}
function renderVs(k) {                                  // one pass: other sensor | NISAR, open water both sides, agreement %
  const V = S.vs, E = V.E, f = S.D.frames[S.t], fy = d => fmt(d, { day: 'numeric', month: 'short', year: 'numeric' });
  const P = E.passes.filter(p => p.validation && p.validation[k]);
  const p = P.reduce((a, b) => Math.abs(dn(b.date) - dn(f.date)) < Math.abs(dn(a.date) - dn(f.date)) ? b : a), v = p.validation[k];
  const put = (o, lid, date, op) => { const l = E.layers[lid], file = l && date && l.files[date];
    if (file) { o.setBounds(L.latLngBounds(l.bounds)); o.setUrl(V.base + file); } o.setOpacity(file ? op : 0); };
  const od = p.matched[k] || v.date;
  put(V.l1, VS[k].radar, k === 'rcm' ? od : p.matched.photo, 0.9); put(V.l2, VS[k].water, od, 1);
  put(V.r1, 'nisar_rgb', p.date, 0.9); put(V.r2, 'nisar_open', p.date, 1);
  [S.base, S.over, S.rcm, S.mo, S.fr].forEach(o => o && o.setOpacity(0)); (S.layers || []).forEach(l => l.ov.setOpacity(0)); drawEv(f.date, new Set());
  const tg = S.tag.getElement()?.firstChild; if (tg) tg.style.display = 'none';
  $('spD').textContent = `${VS[k].name} ${fmt(od)} | NISAR ${fy(p.date)}`;
  $('spK').innerHTML = `<i style="background:${VS[k].c}"></i>${VS[k].name} <i style="background:#ff9a2e"></i>NISAR`;
  S.vbar.querySelector('.swl').textContent = `${VS[k].name} · ${fy(od)}`;
  S.vbar.querySelector('.swr').textContent = `NISAR · ${fy(p.date)}`;
  const A = E.validation[k], X = E.validation.rcm_vs_dswx, pc = x => `${Math.round(x)}%`;
  $('spL').innerHTML = `<div><span style="background:#3aa0ff"></span>open water, ${VS[k].name}</div><div><span style="background:#2882ff"></span>open water, NISAR</div>`
    + `<div class="vagree"><b>${pc(v.agreement_pct)}</b> <em>agree with NISAR · IoU ${v.iou} · this pass, ${v.compared_pct}% of the box compared</em></div>`
    + `<div class="sub" style="grid-column:1/-1">All passes: ${pc(A.agreement_pct)} agree, IoU ${A.iou} (${A.n_dates})${k === 'dswx' && X ? `. RCM vs NASA, without NISAR: ${pc(X.agreement_pct)}, IoU ${X.iou}` : ''}.`
    + `${P.length > 1 ? ' Click a bar near another pass.' : ''}</div>`;
  vclip(); chart();
}
// one pass's own numbers (not the total): official flood, NISAR addition, % for that pass (none if flood < 5 km²)
function passLine(st, date, gdate, gname = 'GFM') {
  if (!st || st.gfm_flood == null) return '';
  const p = st.gfm_flood >= 5 && st.nisar_adds != null ? ` (<b class="o">+${Math.round(100 * st.nisar_adds / st.gfm_flood).toLocaleString('en-GB')}%</b>)` : '';
  return `<div class="sub" style="grid-column:1/-1">This pass ${fmt(date)}${gdate ? ` (${gname} ${fmt(gdate)})` : ''}: official ${km(st.gfm_flood)} km²`
    + (st.nisar_adds != null ? ` · NISAR adds <b class="o">${km(st.nisar_adds)} km²</b>${p}` : '') + '</div>';
}
const R_ = D => D.report || {};
function setStep(i) {
  if (!S) return; S.step = Math.max(0, Math.min(S.steps.length - 1, i));
  const st = S.steps[S.step], n = S.steps.length; S.b = st.b; S.on = new Set(st.on || []);
  if (S.hist && st.t != null) S.t = st.t;
  S.flick = st.label === 'Official';          // entering Official: the "cannot see" blank flickers once
  if (st.t0 && !S.hist) { const k = S.D.frames.reduce((b, f, j) => Math.abs(dn(f.date) - dn(st.t0)) < Math.abs(dn(S.D.frames[b].date) - dn(st.t0)) ? j : b, 0); S.t = k; }
  $('spS').classList.toggle('many', S.steps.length > 4);   // 5+ steps: tighter, still one row
  $('spS').innerHTML = S.steps.map((x, k) => `<button data-k="${k}" class="${k === S.step ? 'on' : k < S.step ? 'done' : ''}${x.label === 'NISAR' || x.nisar ? ' nisar' : ''}${x.csa ? ' csa' : ''}" title="${x.cap.replace(/<[^>]+>/g, '').replace(/"/g, '&quot;')}">${x.label}</button>`).join('<span class="sparr">→</span>');
  $('spBk').style.visibility = S.step ? '' : 'hidden';
  $('spNx').textContent = S.step < n - 1 ? `Next: ${S.steps[S.step + 1].label} →` : '↺ Start over';
  render();
}
// the official map's "cannot see" blank: lit grey; flickers once when it appears or the Official step opens again
function blink(ov, on, again) {
  const el = ov.getElement(); if (!el) return;
  if (!on) { el.classList.remove('blink'); return; }
  if (el.classList.contains('blink') && !again) return;
  el.classList.remove('blink'); void el.offsetWidth; el.classList.add('blink');
}
// an event bundle with no Explorer site (events/<id>/event.json): same panel and steps as a site (Area → Official → NISAR),
// the chart is the bundle's timeline (official flood + NISAR addition per pass)
// the tag under the orange outline: what this image is, which satellite, which day ('' hides it)
const fy = d => fmt(d, { day: 'numeric', month: 'short', year: 'numeric' });
function setTag(txt) { const el = S && S.tag && S.tag.getElement()?.firstChild; if (el) { el.textContent = txt || ''; el.style.display = txt ? '' : 'none'; } }
const mkTag = B => L.marker([B.getSouth(), B.getCenter().lng], { interactive: false, keyboard: false, icon: L.divIcon({ className: 'sptag', html: '<span></span>', iconSize: [0, 0] }) }).addTo(map);
const BASEMAP = 'Basemap · Esri World Imagery';
const NISAR_TAG = d => `NISAR · L-band radar (NASA-ISRO) · ${fy(d)}`;
// official map per pass: Copernicus GFM (Sentinel-1 radar) where it exists, else NASA OPERA DSWx-HLS (optical)
const OFF = { gfm: { layer: 'gfm_classes', name: 'Copernicus GFM', tag: 'Official flood map · Copernicus GFM · Sentinel-1 (ESA) radar',
                     cap: 'The official flood map (Copernicus GFM) uses radar: it sees through clouds, but not under trees. Grey = "cannot see".' },
              dswx: { layer: 'dswx_classes', name: 'NASA DSWx', tag: 'Official flood map · NASA OPERA DSWx-HLS · Landsat / Sentinel-2 optical',
                      cap: 'The official flood map here is NASA’s OPERA DSWx (optical): it cannot see under clouds. White = "cannot see".' } };
async function openBundle(eid) {
  let E; try { E = await (await fetch(`../../events/${eid}/event.json`, { cache: 'no-cache' })).json(); } catch (e) { return; }
  if (E.version === 2 && E.kind === 'validation') return openCheck(eid, E);
  try {                                                 // a v2 flood folder of this place (docs/12): a full map set for every pass
    const P = await (await fetch(`../../events/${eid}/place.json`, { cache: 'no-cache' })).json();
    const f = (P.floods || []).filter(x => x.kind !== 'validation' && x.nisar_adds_km2 != null).sort((a, b) => (b.flood_date || '').localeCompare(a.flood_date || ''))[0];
    const base = `../../events/${eid}/${f.id}/`, F = await (await fetch(base + 'event.json', { cache: 'no-cache' })).json();
    if (openFlood(eid, F, base, E)) return;
  } catch (e) { /* no v2 folder: the bundle's own maps */ }
  const [w, s, e, n] = E.bbox, B = L.latLngBounds([[s, w], [n, e]]), base = `../../events/${eid}/`;
  const ORDER = ['photo', 'gfm_flood', 'gfm_excluded', 'nisar_adds'];
  const files = ORDER.flatMap(k => Object.keys(((E.layers || {})[k] || {}).files || {}));
  // only passes that have the maps (a bar with nothing to show is dropped)
  const T = (E.timeline || []).filter(x => x.date && files.some(f => Math.abs(dn(f) - dn(x.date)) <= 6)).sort((a, b) => a.date.localeCompare(b.date));
  if (!T.length) T.push({ date: (E.headline && E.headline.date) || '', stats: {} });
  const day = (E.headline && E.headline.date) || T[T.length - 1].date;
  S = { bundle: true, id: 'ev-' + eid, E, T, B, t: T.reduce((b, x, i) => Math.abs(dn(x.date) - dn(day)) < Math.abs(dn(T[b].date) - dn(day)) ? i : b, 0),
        box: L.rectangle(B, { pane: 'analysis', color: '#ff7828', weight: 1.5, fill: false, opacity: 0, interactive: false }).addTo(map), tag: mkTag(B),
        ev: ORDER.filter(k => E.layers && E.layers[k]).map(k => ({ k, l: E.layers[k], base,
          ov: L.imageOverlay('data:,', L.latLngBounds(E.layers[k].bounds), { pane: 'analysis', interactive: false, opacity: 0, className: k === 'gfm_excluded' ? 'excl' : '' }).addTo(map) })) };
  const has = k => S.ev.some(x => x.k === k), E_ = ks => ks.filter(has).map(k => 'E_' + k);
  S.steps = [{ label: 'Area', on: [], cap: `The area: ${E.place || E.title}.` }];
  if (has('photo')) S.steps.push({ label: 'Optical', on: E_(['photo']), cap: 'Optical satellites: clouds and forest canopy hide the water.' });
  if (has('gfm_flood')) S.steps.push({ label: 'Official', on: E_(['gfm_flood', 'gfm_excluded']), cap: OFF.gfm.cap.replace('Grey', 'Hatched') });
  if (has('nisar_adds')) S.steps.push({ label: 'NISAR', on: E_(['gfm_flood', 'gfm_excluded', 'nisar_adds']), cap: 'NISAR’s L-band radar sees under the canopy. <b class="o">Orange</b> = flood found in the blank.' });
  panel.hidden = false;
  map.flyToBounds(B, { paddingTopLeft: [panel.offsetWidth + 70, 30], paddingBottomRight: [30, 30], duration: 1.2 });
  const S0 = S; map.once('moveend', () => S === S0 && S.box.setStyle({ opacity: 1 }));
  setStep(0);
  window.dispatchEvent(new CustomEvent('unseen:site', { detail: S.id }));
}
// a v2 flood folder: one bar per pass that has all three (optical photo, official map, NISAR); Area → Optical → Official → NISAR
function openFlood(eid, F, base, E1) {
  const Ly = F.layers || {}, url = (k, d) => d && Ly[k] && Ly[k].files && Ly[k].files[d] ? base + Ly[k].files[d] : null;
  const T = (F.passes || []).map(P => {
    const k = ['gfm', 'dswx'].find(b => (P.layers || []).includes(OFF[b].layer)), od = k && P.matched[k], st = (k && P.baselines[k]) || {};
    return { date: P.date, k, od, pd: P.matched.photo, photo: url('photo', P.matched.photo), off: k && url(OFF[k].layer, od), adds: url('nisar_adds', P.date),
             stats: { gfm_flood: st.flood_km2, nisar_adds: st.nisar_adds_km2 } };
  }).filter(x => x.off && x.adds && x.photo);
  if (!T.length) return false;
  const [w, s, e, n] = F.bbox, B = L.latLngBounds([[s, w], [n, e]]), o = { pane: 'analysis', interactive: false, opacity: 0 };
  const day = (F.summary && F.summary.pass_date) || T[T.length - 1].date;
  S = { bundle: true, v2: true, id: 'ev-' + eid, E: F, T, B, Ly, t: T.reduce((b, x, i) => Math.abs(dn(x.date) - dn(day)) < Math.abs(dn(T[b].date) - dn(day)) ? i : b, 0),
        box: L.rectangle(B, { pane: 'analysis', color: '#ff7828', weight: 1.5, fill: false, opacity: 0, interactive: false }).addTo(map), tag: mkTag(B), ev: [] };
  S.ph = L.imageOverlay('data:,', B, o).addTo(map); S.of = L.imageOverlay('data:,', B, o).addTo(map); S.ad = L.imageOverlay('data:,', B, o).addTo(map);
  S.extra = [S.ph, S.of, S.ad];
  const k0 = T[S.t].k;
  S.steps = [{ label: 'Area', on: [], cap: `The area: ${(E1 && (E1.place || E1.title)) || F.place}.` },
             { label: 'Optical', on: ['photo'], cap: 'Optical satellites: clouds and forest canopy hide the water.' },
             { label: 'Official', on: ['off'], cap: OFF[k0].cap },
             { label: 'NISAR', on: ['off', 'adds'], cap: 'NISAR’s L-band radar sees through clouds and under the canopy. <b class="o">Orange</b> = flood found in the blank.' }];
  panel.hidden = false;
  map.flyToBounds(B, { paddingTopLeft: [panel.offsetWidth + 70, 30], paddingBottomRight: [30, 30], duration: 1.2 });
  const S0 = S; map.once('moveend', () => S === S0 && S.box.setStyle({ opacity: 1 }));
  setStep(0);
  window.dispatchEvent(new CustomEvent('unseen:site', { detail: S.id }));
  return true;
}
function renderFlood() {
  const x = S.T[S.t], on = S.on || new Set(), st = x.stats || {}, O = OFF[x.k], pick = (ov, u, op) => { ov.setUrl(u && op ? u : 'data:,'); ov.setOpacity(u && op ? op : 0); };
  pick(S.ph, x.photo, on.has('photo') ? 0.95 : 0); pick(S.of, x.off, on.has('off') ? 1 : 0); pick(S.ad, x.adds, on.has('adds') ? 1 : 0);
  $('spD').textContent = fy(x.date);
  $('spK').innerHTML = '<i class="kb"></i>official flood <i class="ko"></i>NISAR adds';
  const lg = l => (l && l.legend || []).map(([c, t]) => `<div><span style="background:${c}"></span>${t}</div>`).join('');
  $('spL').innerHTML = (on.has('photo') ? `<div class="sub">Photo ${fmt(x.pd)}${x.pd === x.date ? ' (same day)' : ` (${Math.round(dn(x.pd) - dn(x.date)) > 0 ? '+' : ''}${Math.round(dn(x.pd) - dn(x.date))} d)`}. Clouds look white: that's what NISAR sees through.</div>` : '')
    + (on.has('off') ? lg(S.Ly[O.layer]) : '') + (on.has('adds') ? lg(S.Ly.nisar_adds) : '')
    + (on.has('off') ? passLine(on.has('adds') ? st : { gfm_flood: st.gfm_flood }, x.date, x.od, O.name) : '');
  const lbl = (S.steps[S.step] || {}).label, ps = ((S.Ly.photo || {}).sensors || {})[x.pd] || (S.Ly.photo || {}).sensor || 'optical';
  setTag(lbl === 'Optical' ? `Optical · ${ps.replace(' via NASA GIBS', '')} · NASA GIBS · ${fy(x.pd)}`
       : lbl === 'Official' ? `${O.tag} · ${fy(x.od)}`
       : lbl === 'NISAR' ? `${NISAR_TAG(x.date)} · over ${O.name} ${fmt(x.od)}` : BASEMAP);
  bchart();
}
// v2 validation folder (docs/12 §11, kind "validation"): the area on the original map, NISAR's water, then each official map
// on its own (GFM, NASA DSWx, NASA LANCE) followed by its V step = where it and NISAR agree, with the %
const RN = { gfm: ['GFM', 'Copernicus GFM (Sentinel-1 radar)'], dswx: ['NASA DSWx', 'NASA’s OPERA DSWx map (optical, 30 m)'],
             lance: ['NASA LANCE', 'NASA’s LANCE flood map (VIIRS / MODIS, optical, 250 m)'] };
function openCheck(eid, E) {
  const [w, s, e, n] = E.bbox, B = L.latLngBounds([[s, w], [n, e]]), base = `../../events/${eid}/`;
  const T = E.passes.filter(p => p.validation).map(p => ({ date: p.date, p, stats: {} }));
  const day = T.length ? T[T.length - 1].date : E.summary.pass_date;   // open on the latest pass (the headline % is all passes)
  const V = E.validation || {}, refs = ['gfm', 'dswx', 'lance'].filter(k => V[k] && E.layers[`${k}_water`]);
  const ORDER = ['nisar_open', ...refs.flatMap(k => [`${k}_water`, `agreement_${k}`])];
  S = { bundle: true, check: true, rk: refs[0], id: 'ev-' + eid, E, T, B, t: Math.max(0, T.findIndex(x => x.date === day)),
        box: L.rectangle(B, { pane: 'analysis', color: '#ff7828', weight: 1.5, fill: false, opacity: 0, interactive: false }).addTo(map), tag: mkTag(B),
        ev: ORDER.filter(k => E.layers && E.layers[k]).map(k => ({ k, l: E.layers[k], base,
          ov: L.imageOverlay('data:,', L.latLngBounds(E.layers[k].bounds), { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map) })) };
  const pc = x => `${Math.round(x)}%`, has = k => S.ev.some(x => x.k === k), E_ = ks => ks.filter(has).map(k => 'E_' + k);
  S.steps = [{ label: 'Area', on: [], cap: `${E.place}: a test of NISAR where the official maps can see (no clouds, no "cannot see").` }];
  if (has('nisar_open')) S.steps.push({ label: 'NISAR', on: E_(['nisar_open']), nisar: true, cap: 'NISAR’s L-band radar: water it finds.' });
  refs.forEach(k => {
    const nm = RN[k][0], A = V[k];
    S.steps.push({ label: nm, rk: k, on: E_([`${k}_water`]), cap: `${RN[k][1]}: water, same days.` });
    S.steps.push({ label: `V ${pc(A.agreement_pct)}`, rk: k, on: has(`agreement_${k}`) ? E_([`agreement_${k}`]) : E_([`${k}_water`, 'nisar_open']),
      cap: `Validation vs ${nm}: NISAR and ${nm} agree on <b>${pc(A.agreement_pct)}</b> of pixels (precision ${A.precision ?? '–'}, recall ${A.recall ?? '–'}, ${A.n_dates} passes).`
         + (has(`agreement_${k}`) ? ` Green = both, blue = NISAR only, yellow = ${nm} only.` : '') });
  });
  panel.hidden = false;
  map.flyToBounds(B, { paddingTopLeft: [panel.offsetWidth + 70, 30], paddingBottomRight: [30, 30], duration: 1.2 });
  const S0 = S; map.once('moveend', () => S === S0 && S.box.setStyle({ opacity: 1 }));
  setStep(0);
  window.dispatchEvent(new CustomEvent('unseen:site', { detail: S.id }));
}
function renderCheck() {                                // one pass: this step's map + this pass's agreement with each official map
  const st = S.steps[S.step] || {}; if (st.rk) S.rk = st.rk;
  const x = S.T[S.t], on = S.on || new Set(), v = x.p.validation || {}, pc = y => `${Math.round(y)}%`, nm = RN[S.rk][0];
  $('spD').textContent = fmt(x.date, { day: 'numeric', month: 'short', year: 'numeric' });
  $('spK').innerHTML = `<i style="background:#2ecc71"></i>both <i style="background:#2882ff"></i>NISAR only <i style="background:#ffd700"></i>${nm} only`;
  drawEv(x.date, on);
  $('spL').innerHTML = S.ev.filter(o => on.has('E_' + o.k)).map(o => (o.l.legend && o.l.legend.length ? o.l.legend : [['#888', o.l.label]])
      .map(([c, t]) => `<div><span style="background:${c}"></span>${t}</div>`).join('')).join('')
    + ['gfm', 'dswx', 'lance'].filter(k => v[k] && (!st.rk || k === st.rk)).map(k => `<div class="sub">${RN[k][0]} ${fmt(v[k].date)}: `
      + `<b>${pc(v[k].agreement_pct)}</b> agree · precision ${v[k].precision} · recall ${v[k].recall} · ${v[k].compared_pct}% of the box compared</div>`).join('');
  const rv = v[S.rk];
  setTag(st.label === 'NISAR' ? NISAR_TAG(x.date)
       : st.rk && st.label === RN[S.rk][0] ? (rv ? `Official flood map · ${RN[S.rk][1]} · ${fy(rv.date)}` : '')
       : st.rk ? (rv ? `NISAR ${fmt(x.date)} vs ${nm} ${fmt(rv.date)} · agreement` : '') : BASEMAP);
  cchart();
}
function cchart() {                                     // per pass: % agreement with this step's official map (bars)
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 78, B = H - 12, top = 4, { T, t } = S, n = T.length;
  c.style.height = H + 'px'; c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio); g.clearRect(0, 0, W, H);
  const v = T.map(x => ((x.p.validation || {})[S.rk] || {}).agreement_pct || 0), bw = colW(W, n), Y = y => B - (B - top) * y / 100;
  g.font = '10px system-ui'; g.fillStyle = '#8b95a3'; g.textAlign = 'right';
  [0, 50, 100].forEach(y => { g.fillText(y + '%', AX - 5, Y(y) + 3); g.fillStyle = '#ffffff14'; g.fillRect(AX, Y(y), W - AX, 1); g.fillStyle = '#8b95a3'; });
  T.forEach((x, i) => { g.globalAlpha = i === t ? 1 : 0.55; g.fillStyle = '#2ecc71'; g.fillRect(AX + i * bw + 1, Y(v[i]), bw - 2, B - Y(v[i])); });
  g.globalAlpha = 1; g.strokeStyle = '#fff'; g.strokeRect(AX + t * bw + 0.5, top - 2.5, bw - 1, B - top + 2);
  xLabels(g, T.map(x => x.date), bw, W, H);
}
// drape each bundle layer for this date: the file nearest it (within 6 days); returns the layers that have none
function drawEv(date, on) {
  const miss = [];
  (S.ev || []).forEach(x => {
    const ds = Object.keys(x.l.files || {}); let best = null;
    ds.forEach(d => { if (Math.abs(dn(d) - dn(date)) <= 6 && (!best || Math.abs(dn(d) - dn(date)) < Math.abs(dn(best) - dn(date)))) best = d; });
    if (best) x.ov.setUrl(x.base + x.l.files[best]); x.date = best;
    x.ov.setOpacity(best && on.has('E_' + x.k) ? 1 : 0);
    if (x.k === 'gfm_excluded') { blink(x.ov, !!(best && on.has('E_' + x.k)), S.flick); S.flick = false; }
    if (on.has('E_' + x.k) && !best) miss.push(x.l.label || x.k);
  });
  return miss;
}
// legend swatch = the blank as drawn on the map: lit grey hatch (grayscale, ×1.4) with the same white glow (style.css .excl)
const HATCH = 'repeating-linear-gradient(45deg,#f4f4f8 0 2px,#55555c 2px 6px);box-shadow:0 0 4px #fff,0 0 8px rgba(220,220,235,.8)';
const km = v => Math.round(v).toLocaleString('en-GB');
function renderBundle() {
  const x = S.T[S.t], on = S.on || new Set(), st = x.stats || {};
  $('spD').textContent = fmt(x.date, { day: 'numeric', month: 'short', year: 'numeric' });
  $('spK').innerHTML = '<i class="kb"></i>official flood <i class="ko"></i>NISAR adds';
  const miss = drawEv(x.date, on);
  $('spL').innerHTML = S.ev.filter(v => on.has('E_' + v.k)).map(v => `<div><span style="background:${v.l.legend === 'hatch' ? HATCH : v.l.legend || '#888'}"></span>${v.l.label || v.k}</div>`).join('')
    + (on.size ? passLine(st, x.date, x.gfm_date) : '')
    + (miss.length ? '<div class="sub">No map for this date: pick a bright bar</div>' : '');
  const lbl = (S.steps[S.step] || {}).label, by = k => (S.ev.find(v => v.k === k) || {}).date, ph = ((S.E.layers || {}).photo || {}).sensor || 'optical';
  setTag(lbl === 'Optical' ? (by('photo') ? `Optical · ${ph.replace(' via NASA GIBS', '')} · NASA GIBS · ${fy(by('photo'))}` : '')
       : lbl === 'Official' ? (by('gfm_flood') ? `${OFF.gfm.tag} · ${fy(by('gfm_flood'))}` : '')
       : lbl === 'NISAR' ? NISAR_TAG(by('nisar_adds') || x.date) + (by('gfm_flood') ? ` · over Copernicus GFM ${fmt(by('gfm_flood'))}` : '') : BASEMAP);
  bchart();
}
function bchart() {                                     // per pass: official flood (blue) + NISAR addition (orange); faint = no map that day
  const files = S.v2 ? [] : S.ev.flatMap(e => Object.keys(e.l.files || {})), hasMap = d => S.v2 || files.some(f => Math.abs(dn(f) - dn(d)) <= 6);
  kmChart(S.T.map(x => ({ date: x.date, a: (x.stats || {}).gfm_flood || 0, b: (x.stats || {}).nisar_adds || 0, faint: !hasMap(x.date) })), S.t);
}
// ---------- multi-year view (events/<place>/history): RADARSAT-1 (CSA, 1998–2007) or Sentinel-1 (ESA, 2016–2025) then NISAR (2026), same box ----------
// steps: Then (RADARSAT-1) → Now (NISAR) → Swipe (Then | Now on the map) → Change (flooded both / only then / only now)
const SENS = { 'RADARSAT-1': { c: '#ff6b6b', radar: 'rs1_radar', flood: 'rs1_flood', note: 'RADARSAT-1 · CSA · C-band' },
               'Sentinel-1': { c: '#a78bfa', radar: 's1_radar', flood: 's1_water', note: 'Sentinel-1 · ESA Copernicus · C-band' },
               NISAR: { c: '#ff9a2e', radar: 'nisar_rgb', flood: 'nisar_water', note: 'NISAR · L-band' } };
const OLD_CAP = { 'RADARSAT-1': 'RADARSAT-1 (Canadian Space Agency), its wettest image here.',
                  'Sentinel-1': 'Sentinel-1 (ESA Copernicus), its first year here: before the dam.' };
const CHG = { both: ['#e8eef5', 'flood, then and now'], then: ['#ff6b6b', 'only then'], now: ['#ff9a2e', 'only now (NISAR)'] };
async function openHistory(place) {
  let E; try { E = await (await fetch(`../../events/${place}/history/event.json`, { cache: 'no-cache' })).json(); } catch (e) { return; }
  const [w, so, e, n] = E.bbox, B = L.latLngBounds([[so, w], [n, e]]), base = `../../events/${place}/history/`;
  const I = (E.images || []).slice().sort((a, b) => a.date.localeCompare(b.date));
  const wettest = sn => I.reduce((b, x, i) => x.sensor === sn && (b < 0 || (x.flood_km2 ?? -1) > (I[b].flood_km2 ?? -1)) ? i : b, -1);
  const o = { pane: 'analysis', interactive: false, opacity: 0 };
  const ov = () => L.imageOverlay('data:,', B, o).addTo(map);
  S = { hist: true, id: 'hist-' + place, E, I, B, hbase: base, n: I.length, t: 0,
        hr: ov(), hf: ov(), nr: ov(), nf: ov(), chg: ov(),               // then radar / flood, now radar / flood (swipe), change map
        box: L.rectangle(B, { pane: 'analysis', color: '#ff7828', weight: 1.5, fill: false, opacity: 0, interactive: false }).addTo(map),
        tag: L.marker([so, (w + e) / 2], { interactive: false, keyboard: false, icon: L.divIcon({ className: 'sptag', html: '<span></span>', iconSize: [0, 0] }) }).addTo(map) };
  S.extra = [S.hr, S.hf, S.nr, S.nf, S.chg];
  const old = S.old = (I.find(x => x.sensor !== 'NISAR') || {}).sensor || 'RADARSAT-1';   // RADARSAT-1 (CSA) or Sentinel-1 (ESA)
  S.a = old === 'Sentinel-1' ? I.findIndex(x => x.sensor === old) : wettest(old); S.b2 = wettest('NISAR');                   // the pair compared in Swipe / Change (click a bar to change it)
  const th = S.a, nw = S.b2, fl = (x, sn) => { const l = (E.layers || {})[SENS[sn].flood]; return !!(l && l.files && x && l.files[x.date]); };
  S.steps = [th >= 0 && { label: `Then ${I[th].date.slice(0, 4)}`, t: th, cap: OLD_CAP[old] || '', csa: old === 'RADARSAT-1' },
             nw >= 0 && { label: `Now ${I[nw].date.slice(0, 4)}`, t: nw, cap: 'NISAR, its wettest pass here.', nisar: true },
             th >= 0 && nw >= 0 && { label: 'Swipe', mode: 'swipe', cap: 'Then | Now on the map. Drag the line.' },
             th >= 0 && nw >= 0 && fl(I[th], old) && fl(I[nw], 'NISAR') && { label: 'Change', mode: 'change', cap: 'Where the flood was then, now, or both.' }].filter(Boolean);
  // the swipe line: drag it across the map; each side clips its own images
  const bar = S.bar = document.createElement('div'); bar.className = 'swbar'; bar.hidden = true;
  bar.innerHTML = '<span class="swl"></span><b>⇔</b><span class="swr"></span>';
  map.getContainer().appendChild(bar); L.DomEvent.disableClickPropagation(bar);
  S.sx = null; let drag = false;
  bar.onpointerdown = ev => { drag = true; bar.setPointerCapture(ev.pointerId); ev.preventDefault(); };
  bar.onpointermove = ev => { if (!drag) return; const r = map.getContainer().getBoundingClientRect(); S.sx = Math.max(0, Math.min(r.width, ev.clientX - r.left)); clip(); };
  bar.onpointerup = bar.onpointercancel = () => { drag = false; };
  S.clipEv = () => clip(); map.on('move zoom zoomend moveend resize', S.clipEv);
  panel.hidden = false; panel.classList.add('hist');
  map.flyToBounds(B, { paddingTopLeft: [panel.offsetWidth + 70, 30], paddingBottomRight: [30, 30], duration: 1.2 });
  const S0 = S; map.once('moveend', () => { if (S !== S0) return; S.box.setStyle({ opacity: 1 }); if (S.sx == null) { S.sx = map.latLngToContainerPoint(B.getCenter()).x; clip(); } });
  $('spC').title = (E.summary && E.summary.caveat) || '';
  setStep(0);
  window.dispatchEvent(new CustomEvent('unseen:site', { detail: S.id }));
}
function clip() {                                       // Swipe: then-images keep the left of the line, now-images the right
  if (!S || !S.hist) return;
  const sw = S.mode === 'swipe', r = map.getContainer().getBoundingClientRect();
  if (S.sx == null) S.sx = r.width / 2;
  S.bar.hidden = !sw; S.bar.style.left = S.sx + 'px';
  const x = r.left + S.sx, cut = (o, keepLeft) => { const el = o.getElement(); if (!el) return;
    if (!sw) { el.style.clipPath = ''; return; }
    const b = el.getBoundingClientRect(), p = Math.max(0, Math.min(100, (x - b.left) / Math.max(1, b.width) * 100));
    el.style.clipPath = keepLeft ? `inset(0 ${100 - p}% 0 0)` : `inset(0 0 0 ${p}%)`; };
  cut(S.hr, true); cut(S.hf, true); cut(S.nr, false); cut(S.nf, false);
}
const imgOf = (x, name) => { const l = (S.E.layers || {})[name], f = l && l.files && l.files[x.date]; return f ? S.hbase + f : null; };
function show(o, url, op) { o.setUrl(url || 'data:,'); o.setOpacity(url ? op : 0); }
const loadImg = src => new Promise((ok, no) => { const im = new Image(); im.onload = () => ok(im); im.onerror = no; im.src = src; });
async function changeMap(a, b) {                        // pixel by pixel on the shared grid: flooded both / only then / only now
  const key = a.date + '|' + b.date; S.cmap = S.cmap || {};
  if (S.cmap[key]) return S.cmap[key];
  const [A, Bm] = await Promise.all([loadImg(imgOf(a, SENS[S.old].flood)), loadImg(imgOf(b, 'nisar_water'))]);
  const w = A.naturalWidth, h = A.naturalHeight, cv = document.createElement('canvas'); cv.width = w; cv.height = h;
  const g = cv.getContext('2d'); g.drawImage(A, 0, 0); const da = g.getImageData(0, 0, w, h).data;
  g.clearRect(0, 0, w, h); g.drawImage(Bm, 0, 0, w, h); const db = g.getImageData(0, 0, w, h).data;
  const out = g.createImageData(w, h), o = out.data, rgb = c => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
  const C = { both: rgb(CHG.both[0]), then: rgb(CHG.then[0]), now: rgb(CHG.now[0]) }, n = { both: 0, then: 0, now: 0 };
  for (let i = 0; i < da.length; i += 4) {
    const p = da[i + 3] > 0, q = db[i + 3] > 0; if (!p && !q) continue;
    const k = p && q ? 'both' : p ? 'then' : 'now'; n[k]++; const c = C[k];
    o[i] = c[0]; o[i + 1] = c[1]; o[i + 2] = c[2]; o[i + 3] = 230;
  }
  g.putImageData(out, 0, 0);
  const px = (S.E.area_km2 || 0) / (w * h);              // km² per pixel (the box is the whole grid)
  return (S.cmap[key] = { url: cv.toDataURL(), km: px ? { both: n.both * px, then: n.then * px, now: n.now * px } : null });
}
function renderHist() {
  const st = S.steps[S.step] || {}, mode = S.mode = st.mode || 'single', fy = { day: 'numeric', month: 'short', year: 'numeric' };
  const tg = S.tag.getElement()?.firstChild;
  [S.hr, S.hf, S.nr, S.nf, S.chg].forEach(o => o.setOpacity(0));
  $('spK').innerHTML = Object.entries(SENS).filter(([n]) => S.I.some(i => i.sensor === n)).map(([n, v]) => `<i style="background:${v.c}"></i>${n === 'RADARSAT-1' ? 'RADARSAT-1 (CSA)' : n}`).join(' ');
  if (mode === 'single') {
    const x = S.I[S.t], k = SENS[x.sensor] || SENS.NISAR;
    show(S.hr, imgOf(x, k.radar), 0.9); show(S.hf, imgOf(x, k.flood), 1);
    $('spD').textContent = fmt(x.date, fy);
    $('spL').innerHTML = `<div><span style="background:#2882ff"></span>flood${x.flood_km2 != null ? ` · <b>${km(x.flood_km2)} km²</b>` : ' · not measured'}</div>`
      + (x.open_water_km2 != null ? `<div><span style="background:#0a3a8c"></span>all open water (lake + river) · <b>${km(x.open_water_km2)} km²</b></div>` : '');
    if (tg) { tg.textContent = `${k.note} · ${fmt(x.date, fy)}`; tg.style.display = ''; }
  } else {
    const a = S.I[S.a], b = S.I[S.b2];
    $('spD').textContent = `${a.date.slice(0, 4)} → ${b.date.slice(0, 4)}`;
    if (tg) { tg.textContent = `${S.old} ${fmt(a.date, fy)} vs NISAR ${fmt(b.date, fy)} · change`; tg.style.display = mode === 'change' ? '' : 'none'; }
    if (mode === 'swipe') {
      show(S.hr, imgOf(a, SENS[S.old].radar), 0.9); show(S.hf, imgOf(a, SENS[S.old].flood), 1);
      show(S.nr, imgOf(b, 'nisar_rgb'), 0.9); show(S.nf, imgOf(b, 'nisar_water'), 1);
      S.bar.querySelector('.swl').textContent = `${S.old} · ${fmt(a.date, fy)}`;
      S.bar.querySelector('.swr').textContent = `NISAR · ${fmt(b.date, fy)}`;
      $('spL').innerHTML = `<div><span style="background:#2882ff"></span>flood</div><div class="sub">${a.flood_km2 != null ? km(a.flood_km2) : '–'} → ${b.flood_km2 != null ? km(b.flood_km2) : '–'} km²</div>`
        + '<div class="sub" style="grid-column:1/-1">Click a bar to pick the years.</div>';
    } else {
      const S0 = S; $('spL').innerHTML = '<div class="sub">Comparing…</div>';
      changeMap(a, b).then(r => { if (S !== S0 || S.mode !== 'change') return;
        show(S.chg, r.url, 1);
        $('spL').innerHTML = Object.entries(CHG).map(([k, [c, t]]) => `<div><span style="background:${c}"></span>${t}${r.km ? ` · <b>${km(r.km[k])}</b> km²` : ''}</div>`).join('')
          + `<div class="sub" style="grid-column:1/-1">${(S.E.summary && S.E.summary.caveat) || 'Two radars and two methods: compare the pattern.'}</div>`;
      }).catch(() => { $('spL').innerHTML = '<div class="sub">No flood map for one of these dates.</div>'; });
    }
  }
  clip();
  histChart();
}
function histChart() {                                  // one bar per image: flood km², coloured by satellite; years on the axis
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 78, B = H - 12, top = 4, { I, t } = S, n = I.length;
  c.style.height = H + 'px'; c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio); g.clearRect(0, 0, W, H);
  const raw = Math.max(1, ...I.map(x => x.flood_km2 || 0)), st = 10 ** Math.floor(Math.log10(raw)), mx = Math.ceil(raw / st) * st, bw = colW(W, n);
  const Y = v => B - (B - top) * v / mx;
  g.font = '10px system-ui'; g.fillStyle = '#8b95a3'; g.textAlign = 'right';
  [0, mx / 2, mx].forEach(y => { g.fillText(y.toLocaleString('en-GB'), AX - 5, Y(y) + 3); g.fillStyle = '#ffffff14'; g.fillRect(AX, Y(y), W - AX, 1); g.fillStyle = '#8b95a3'; });
  g.save(); g.translate(8, (B + top) / 2); g.rotate(-Math.PI / 2); g.textAlign = 'center'; g.fillText('km²', 0, 0); g.restore(); g.textAlign = 'left';
  I.forEach((x, i) => { const X = AX + i * bw + 1;
    g.globalAlpha = (S.mode && S.mode !== 'single' ? i === S.a || i === S.b2 : i === t) ? 1 : 0.6; g.fillStyle = (SENS[x.sensor] || SENS.NISAR).c;
    if (x.flood_km2 != null) g.fillRect(X, Y(x.flood_km2), bw - 2, B - Y(x.flood_km2)); else { g.fillRect(X, B - 2, bw - 2, 2); } });
  g.globalAlpha = 1; g.strokeStyle = '#fff'; (S.mode && S.mode !== 'single' ? [S.a, S.b2] : [t]).forEach(k => g.strokeRect(AX + k * bw + 0.5, top - 2.5, bw - 1, B - top + 2));
  g.fillStyle = '#8b95a3'; let lx = -99;
  I.forEach((x, i) => { const y = x.date.slice(0, 4); if (i && y === I[i - 1].date.slice(0, 4)) return;
    const txt = y, X = AX + i * bw + 1; if (X < lx + 4) return; g.fillText(txt, X, H - 1); lx = X + g.measureText(txt).width; });
}
function closeSite(keepHash) {
  panel.classList.remove('hist');
  if (S && S.bar) { S.bar.remove(); map.off('move zoom zoomend moveend resize', S.clipEv); }
  if (S && S.vbar) { S.vbar.remove(); map.off('move zoom zoomend moveend resize', S.vclipEv); }
  if (S) { ['base', 'over', 'box', 'tag', 'mo', 'fr'].forEach(k => S[k] && map.removeLayer(S[k])); (S.layers || []).forEach(l => map.removeLayer(l.ov)); (S.ev || []).forEach(x => map.removeLayer(x.ov)); (S.extra || []).forEach(x => map.removeLayer(x)); }
  const was = !!S; S = null; panel.hidden = true;
  if (was && keepHash !== 'swap') window.dispatchEvent(new CustomEvent('unseen:site', { detail: null }));
  if (!keepHash && location.hash.startsWith('#site=')) history.replaceState(null, '', location.pathname + location.search);
}

function render() {
  if (!S) return;
  if (S.hist) return renderHist();
  if (S.check) return renderCheck();
  if (S.bundle) return S.v2 ? renderFlood() : renderBundle();
  const vst = (S.steps[S.step] || {}).vs;
  if (vst && S.vs) return renderVs(vst);
  if (S.vs) { ['l1', 'l2', 'r1', 'r2'].forEach(k => S.vs[k].setOpacity(0)); vclip(); }
  $('spK').innerHTML = S.official ? '<i class="kb"></i>official flood <i class="ko"></i>NISAR adds' : '<i class="kb"></i>water <i class="ko"></i>hidden from optical';
  const { D, A, t } = S, f = D.frames[t], s = D.summary[t];
  $('spD').textContent = `${fmt(f.date, { day: 'numeric', month: 'short', year: 'numeric' })}${f.sensor && D.history ? ' · ' + f.sensor : ''}`;
  let note = '';
  if (S.b === 'photo') {
    const p = S.photos.length ? S.photos.reduce((a, b) => Math.abs(dn(b[0]) - dn(f.date)) < Math.abs(dn(a[0]) - dn(f.date)) ? b : a) : null;
    if (p && Math.abs(dn(p[0]) - dn(f.date)) > 60) { S.base.setUrl(A(f.nisar)); note = `No optical photo near ${f.date.slice(0, 4)}: showing the radar.`; }
    else if (p) { S.base.setUrl(A(p[1])); S.pd = p[0]; const g = Math.round(dn(p[0]) - dn(f.date));
             note = `Photo ${fmt(p[0])}${g ? ` (${g > 0 ? '+' : ''}${g} d from this pass)` : ' (same day)'}. Clouds look white: that's what NISAR sees through.`; }
    else note = 'No optical photo for this area.';
  } else if (S.b === 'nisar') { S.base.setUrl(A(f.nisar)); note = f.sensor === 'RADARSAT-1'
      ? `RADARSAT-1 (CSA), C-band HH, beam ${f.beam}. Dark = smooth water.`
      : 'Radar colours: R = HH, G = HV, B = HH/HV. Dark = smooth water.'; }
  if (S.b === 'none') S.base.setUrl('data:,');            // drop the radar / photo so it can't flash under other layers
  S.base.setOpacity(S.b === 'none' ? 0 : 0.9);
  const on = S.on || new Set();
  if (S.rcm) S.rcm.setOpacity(on.has('rcm') ? 1 : 0);
  S.over.setUrl(on.has('pass') ? A(f.hidden) : 'data:,'); S.over.setOpacity(on.has('pass') ? 1 : 0);
  (S.layers || []).forEach((l, i) => l.ov.setOpacity(on.has(`L${i}`) ? 1 : 0));
  const evNote = drawEv(f.date, on);
  let pr = null;
  if (S.P) {                                                       // the 12-day pair for this date (contains it, else nearest)
    const Ls = S.P.list, x = dn(f.date);
    pr = Ls.find(q => dn(q.ref) < x && x <= dn(q.sec)) || Ls.reduce((a, b) => Math.abs(dn(b.sec) - x) < Math.abs(dn(a.sec) - x) ? b : a);
    S.mo.setUrl(A(pr.motion)); S.fr.setUrl(A(pr.fringes));
    S.mo.setOpacity(on.has('motion') ? 1 : 0); S.fr.setOpacity(on.has('fringes') ? 1 : 0);
  }
  const seen = new Set();                                         // one legend per distinct scale
  $('spL').innerHTML = (on.has('rcm') ? '<div><span style="background:#f5f5f5"></span>both see water</div><div><span style="background:#2882ff"></span>only NISAR</div><div><span style="background:#ff5050"></span>only RCM</div><div class="sub">Agree on <b>79%</b> of the water</div>' : '') + (S.ev || []).filter(x => on.has('E_' + x.k)).map(x => `<div><span style="background:${x.l.legend === 'hatch' ? HATCH : x.l.legend || '#888'}"></span>${x.l.label || x.k}</div>`).join('')
    + (evNote.length ? `<div class="sub">Not on this date: ${evNote.join(', ')}</div>` : '')
    + ([...on].some(k => k.startsWith('E_')) && S.evE ? (r => r ? passLine(r.stats, r.date, r.gfm_date) : '')(
        (S.evE.timeline || []).find(r => Math.abs(dn(r.date) - dn(f.date)) <= 6)) : '') + (pr && (on.has('motion') || on.has('fringes')) ? `<div class="pair${pr.event ? ' ev' : ''}">Pair ${fmt(pr.ref)} → ${fmt(pr.sec)}${pr.event ? ' · spans the event' : ''}</div>` : '')
    + [...(on.has('motion') && S.P ? [S.P.motion_legend] : []), ...(on.has('fringes') && S.P ? [S.P.fringe_legend] : [])]
      .map(lg => lg.map(([c, t]) => `<div><span style="background:${c}${c.startsWith('linear') ? ';width:60px' : ''}"></span>${t}</div>`).join('')).join('')
    + (S.layers || []).filter((l, i) => on.has(`L${i}`)).map(l => l.legend.map(([c, t]) => `<div><span style="background:${c}${c.startsWith('linear') ? ';width:60px' : ''}"></span>${t}</div>`).join(''))
    .filter(h => !seen.has(h) && seen.add(h)).join('')
    + (on.has('pass') && D.history ? (f.gfm ? R_(D).pass_legend : [['#2882ff', f.sensor === 'NISAR' ? 'flood (no GFM that week)' : 'flood (no official map before 2015)']])
        .map(([c, t]) => `<div><span style="background:${c}"></span>${t}</div>`).join('')
      + (f.gfm ? `<div class="sub">GFM ${s.gfm_date}: ${s.gfm_km2} km² · NISAR ${s.new_water} km²</div>` : '')
    : on.has('pass') ? '<div><span style="background:var(--blue)"></span>water, seen by both</div><div><span style="background:var(--orange)"></span>water, only radar (clouds)</div>'
      + '<div><span style="background:var(--green)"></span>water under trees</div><div><span style="background:var(--purple)"></span>surface change</div>' : '');
  if (D.history) note = `Flood ${Math.round(s.new_water).toLocaleString()} km² (beyond rivers). ` + note;
  const g = (S.ev || []).find(x => x.k === 'gfm_flood' && on.has('E_gfm_flood'));
  if (S.b === 'none') note = [g && g.date ? `GFM (Sentinel-1) ${fmt(g.date)}` : '', on.has('E_nisar_adds') ? `NISAR ${fmt(f.date)}` : '', !on.size ? 'Basemap: Esri World Imagery' : ''].filter(Boolean).join(' · ');
  const lbl = (S.steps[S.step] || {}).label, gd = (S.ev || []).find(x => x.k === 'gfm_flood');   // the tag under the outline
  setTag(on.has('rcm') ? 'RCM (CSA, C-band) 13 Oct 2026 vs NISAR 10 Oct 2026'
    : S.b === 'photo' ? (note.startsWith('Photo') ? `Optical · HLS (Landsat / Sentinel-2) · NASA GIBS · ${fy(S.pd)}` : NISAR_TAG(f.date))
    : S.b === 'nisar' ? (f.sensor === 'RADARSAT-1' ? `RADARSAT-1 (CSA) · C-band radar · ${fy(f.date)}` : NISAR_TAG(f.date))
    : lbl === 'Official' ? (gd && gd.date ? `${OFF.gfm.tag} · ${fy(gd.date)}` : '')
    : lbl === 'NISAR' ? NISAR_TAG(f.date) + (gd && gd.date ? ` · over Copernicus GFM ${fmt(gd.date)}` : '')
    : !on.size ? BASEMAP : '');
  chart();
}

// new water per pass (orange part = hidden by clouds), current pass highlighted; click a bar to jump
function vchart() {                                   // volcano: vent motion per 12-day pair, ± noise, eruptions in red
  const V = S.D.report.volcano, P = (V.pairs || []).filter(p => p.vent_cm != null);
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 90;
  c.height = H; c.style.height = H + 'px'; c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio);
  g.clearRect(0, 0, W, H);
  if (!P.length) return;
  const t0 = dn(P[0].ref), t1 = dn(P[P.length - 1].sec), X = d => 4 + (W - 8) * (dn(d) - t0) / Math.max(1, t1 - t0);
  const mx = Math.max(2, ...P.map(p => Math.abs(p.vent_cm) + p.noise_cm)), Y = v => H / 2 - 12 - v / mx * (H / 2 - 16) + 6;
  g.strokeStyle = '#2a313c'; g.beginPath(); g.moveTo(0, Y(0)); g.lineTo(W, Y(0)); g.stroke();
  (V.eruptions || []).forEach(e => { const x = X(e); if (x >= 0 && x <= W) { g.strokeStyle = '#f85149'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H - 12); g.stroke(); g.setLineDash([]); } });
  P.forEach(p => {
    const x0 = X(p.ref) + 1, x1 = X(p.sec) - 1, y = Y(p.vent_cm);
    g.fillStyle = 'rgba(139,149,163,.25)'; g.fillRect(x0, Y(p.noise_cm), x1 - x0, Y(-p.noise_cm) - Y(p.noise_cm));   // noise band
    g.fillStyle = p.spans_eruption ? '#ff7828' : '#d7dde5'; g.fillRect(x0, Math.min(y, Y(0)), x1 - x0, Math.max(2, Math.abs(y - Y(0))));
  });
  g.fillStyle = '#8b95a3'; g.font = '10px system-ui';
  g.fillText(`vent motion per 12-day pair (cm, ±${mx.toFixed(0)})`, 2, 10);
  g.fillText(fmt(P[0].ref), 2, H - 1); const l = fmt(P[P.length - 1].sec); g.fillText(l, W - g.measureText(l).width - 2, H - 1);
}
const AX = 36;                                          // left margin for the km² axis
const colW = (W, n) => (S.bw = Math.min((W - AX) / Math.max(1, n), 24));   // one bar per pass, never wider than 24 px
function xLabels(g, dates, bw, W, H) {                   // first and last date under the bars
  g.fillStyle = '#8b95a3'; g.textAlign = 'left'; const a = fmt(dates[0]); g.fillText(a, AX + 1, H - 1);
  if (dates.length < 2) return;
  const l = fmt(dates[dates.length - 1]), x = Math.min(W, AX + dates.length * bw) - g.measureText(l).width - 1;
  if (x > AX + g.measureText(a).width + 8) g.fillText(l, x, H - 1);
}
// the one bar chart of every flood panel: official flood (blue) + NISAR addition (orange) per pass, km²
function kmChart(R, t, mark) {
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 78, B = H - 12, top = 4, n = R.length;
  c.style.height = H + 'px'; c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio); g.clearRect(0, 0, W, H);
  const raw = Math.max(1, ...R.map(r => r.a + r.b)), st = 10 ** Math.floor(Math.log10(raw)), mx = Math.ceil(raw / st) * st, bw = colW(W, n), Y = y => B - (B - top) * y / mx;
  g.font = '10px system-ui'; g.fillStyle = '#8b95a3'; g.textAlign = 'right';
  [0, mx / 2, mx].forEach(y => { g.fillText(y.toLocaleString('en-GB'), AX - 5, Y(y) + 3); g.fillStyle = '#ffffff14'; g.fillRect(AX, Y(y), W - AX, 1); g.fillStyle = '#8b95a3'; });
  g.save(); g.translate(8, (B + top) / 2); g.rotate(-Math.PI / 2); g.textAlign = 'center'; g.fillText('km²', 0, 0); g.restore();
  R.forEach((r, i) => { const X = AX + i * bw + 1;
    g.globalAlpha = i === t ? 1 : r.faint ? 0.2 : 0.6;
    g.fillStyle = r.blue || '#2b8cbe'; g.fillRect(X, Y(r.a), bw - 2, B - Y(r.a));
    g.fillStyle = '#ff7828'; g.fillRect(X, Y(r.a + r.b), bw - 2, Y(r.a) - Y(r.a + r.b)); });
  g.globalAlpha = 1; g.strokeStyle = '#fff'; g.strokeRect(AX + t * bw + 0.5, top - 2.5, bw - 1, B - top + 2);
  if (mark != null && mark >= 0) { const x = AX + (mark + 0.5) * bw; g.strokeStyle = '#f85149'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(x, 0); g.lineTo(x, B); g.stroke(); g.setLineDash([]); }
  xLabels(g, R.map(r => r.date), bw, W, H);
}
function chart() {
  if (S.D.report && S.D.report.hazard === 'volcano') return vchart();
  if (!S.D.history) {                                   // same chart as every flood panel: official flood + NISAR addition per pass
    const T = (S.evE && S.evE.timeline) || [], ev = S.D.event_date;
    const R = S.D.frames.map((f, i) => { const r = T.find(x => Math.abs(dn(x.date) - dn(f.date)) <= 6), st = r && r.stats;
      if (S.official) return { date: f.date, a: (st && st.gfm_flood) || 0, b: (st && st.nisar_adds) || 0, faint: !st };
      const w = S.nw(S.D.summary[i]), h = Math.min(S.hid(S.D.summary[i]), w); return { date: f.date, a: w - h, b: h }; });   // no official map here: water / hidden from optical
    return kmChart(R, S.t, ev ? S.D.frames.reduce((b, f, i) => Math.abs(dn(f.date) - dn(ev)) < Math.abs(dn(S.D.frames[b].date) - dn(ev)) ? i : b, 0) : null);
  }
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 78, B = H - 12, { D, t } = S, n = D.frames.length;
  c.style.height = H + 'px'; c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio); g.clearRect(0, 0, W, H);
  const v = D.summary.map(S.nw), h = D.summary.map(S.hid), raw = Math.max(1, ...v);
  const step = 10 ** Math.floor(Math.log10(raw)), mx = Math.ceil(raw / step) * step, bw = colW(W, n), top = 4;
  const Y = x => B - (B - top) * x / mx;
  g.font = '10px system-ui'; g.fillStyle = '#8b95a3'; g.textAlign = 'right';
  [0, mx / 2, mx].forEach(y => { g.fillText(y.toLocaleString('en-GB'), AX - 5, Y(y) + 3); g.fillStyle = '#ffffff14'; g.fillRect(AX, Y(y), W - AX, 1); g.fillStyle = '#8b95a3'; });
  g.save(); g.translate(8, (B + top) / 2); g.rotate(-Math.PI / 2); g.textAlign = 'center'; g.fillText('km²', 0, 0); g.restore();
  g.textAlign = 'left';
  v.forEach((x, i) => {
    const X = AX + i * bw + 1, yh = Math.min(h[i], x);
    g.globalAlpha = i === t ? 1 : 0.55;
    g.fillStyle = D.frames[i].sensor === 'RADARSAT-1' ? '#8fb3d9' : '#2b8cbe'; g.fillRect(X, Y(x), bw - 2, Y(yh) - Y(x));
    g.fillStyle = '#ff7828'; g.fillRect(X, Y(yh), bw - 2, B - Y(yh));
  });
  g.globalAlpha = 1; g.strokeStyle = '#fff'; g.strokeRect(AX + t * bw + 0.5, top - 2.5, bw - 1, B - top + 2);
  g.fillStyle = '#8b95a3';
  if (D.history) {                                      // one label per year, a tick where the year changes
    let lx = -99;
    D.frames.forEach((fr, i) => { const y = fr.date.slice(0, 4);
      if (i && y === D.frames[i - 1].date.slice(0, 4)) return;
      if (i) { g.fillRect(AX + i * bw - 0.5, top, 1, B - top); }
      const txt = y === '2026' ? '2026 NISAR' : "'" + y.slice(2);
      if (AX + i * bw + 2 - lx < 4 && y !== '2026') return;
      if (y === '2026' && AX + i * bw + 2 < lx + 4) g.clearRect(lx - 30, H - 11, 30, 11);
      g.fillText(txt, AX + i * bw + 2, H - 1); lx = AX + i * bw + 2 + g.measureText(txt).width; });
    return;
  }
  g.fillText(fmt(D.frames[0].date), AX + 1, H - 1);
  const last = fmt(D.frames[n - 1].date); g.fillText(last, W - g.measureText(last).width - 1, H - 1);
  if (D.event_date) {                                  // event marker on the pass axis
    const d0 = dn(D.frames[0].date), d1 = dn(D.frames[n - 1].date), x = AX + bw / 2 + (W - AX - bw) * (dn(D.event_date) - d0) / Math.max(1, d1 - d0);
    if (x >= AX && x <= W) { g.strokeStyle = '#f85149'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(x, 0); g.lineTo(x, B); g.stroke(); g.setLineDash([]); }
  }
}
// the chart is the time control: click or drag across the bars
const nOf = () => S.hist ? S.n : S.bundle ? S.T.length : S.D.frames.length;
const pick = ev => { if (!S) return; const r = $('spC').getBoundingClientRect(); setT(Math.floor((ev.clientX - r.left - AX) / (S.bw || (r.width - AX) / nOf()))); };
let drag = false;
$('spC').onpointerdown = ev => { drag = true; $('spC').setPointerCapture(ev.pointerId); pick(ev); };
$('spC').onpointermove = ev => { if (drag) pick(ev); };
$('spC').onpointerup = $('spC').onpointercancel = () => { drag = false; };

function setT(i) {
  if (!S) return; S.t = Math.max(0, Math.min(nOf() - 1, i));
  if (S.hist && S.mode && S.mode !== 'single') { if (S.I[S.t].sensor !== 'NISAR') S.a = S.t; else S.b2 = S.t; }
  render();
}
$('spX').onclick = () => { const m = panel.classList.toggle('min'); $('spX').textContent = m ? '+' : '–'; $('spX').title = m ? 'Expand' : 'Minimize'; };
$('spS').onclick = ev => { const b = ev.target.closest('button'); if (b && S) { setStep(+b.dataset.k); if (panel.classList.contains('min')) $('spX').click(); } };
$('spBk').onclick = () => setStep(S.step - 1);
$('spNx').onclick = () => setStep(S.step < S.steps.length - 1 ? S.step + 1 : 0);
addEventListener('keydown', ev => {
  if (!S || /INPUT|TEXTAREA/.test(document.activeElement?.tagName) && document.activeElement.type !== 'range') return;
  if (ev.key === 'Escape') closeSite(false);
  else if (ev.key === 'ArrowRight') setT(S.t + 1);
  else if (ev.key === 'ArrowLeft') setT(S.t - 1);
  else if (ev.key === 'ArrowDown' || ev.key === 'Enter') { ev.preventDefault(); setStep(S.step + 1); }
  else if (ev.key === 'ArrowUp') { ev.preventDefault(); setStep(S.step - 1); }
});
const fromHash = () => { const m = location.hash.match(/^#site=(.+)$/); m ? openSite(decodeURIComponent(m[1])) : closeSite(true); };
addEventListener('hashchange', fromHash);
window.openSite = id => { location.hash = 'site=' + encodeURIComponent(id); };
window.closeSite = () => closeSite(false);
fromHash();
})();
