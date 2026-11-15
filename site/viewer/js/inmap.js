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
    <div class="spcap" id="spCap"></div>
    <div class="legend sub" id="spL"></div>
    <div class="spch"><span id="spD"></span><span class="spkey"><i class="kb"></i>water <i class="ko"></i>hidden from optical</span></div>
    <canvas id="spC" title="Water per pass. Click or drag to change the date (← → keys too)."></canvas>
    <div class="spnav"><button id="spBk">← Back</button><button id="spNx" class="primary"></button></div>
  </div>`;
$('leftcol').appendChild(panel);
L.DomEvent.disableClickPropagation(panel); L.DomEvent.disableScrollPropagation(panel);

async function openSite(id) {
  closeSite('swap');
  const base = `sites/${encodeURIComponent(id)}/`;
  let D; try { D = await (await fetch(base + 'site.json', { cache: 'no-cache' })).json(); } catch (e) { return; }
  const A = n => (D.assets && D.assets[n]) || base + n;
  const [[w, n], [e, s]] = D.corners, B = L.latLngBounds([[s, w], [n, e]]);
  const photos = Object.entries(D.photos || {}).sort();
  const nw = x => x.new_water ?? x.nisar_water ?? 0, hid = x => x.hidden_new ?? x.hidden_clouds ?? 0;
  const peak = D.summary.reduce((b, x, i) => nw(x) > nw(D.summary[b]) ? i : b, 0);
  S = { id, D, A, B, photos, nw, hid, t: D.hazard && ['WF', 'VO', 'EQ'].includes(D.hazard) ? D.frames.length - 1 : peak, b: 'nisar',
        base: L.imageOverlay(A(D.frames[0].nisar), B, { pane: 'analysis', interactive: false }).addTo(map),
        over: L.imageOverlay(A(D.frames[0].hidden), B, { pane: 'analysis', interactive: false }).addTo(map),
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
    const ORDER = ['gfm_flood', 'gfm_excluded', 'nisar_water', 'nisar_adds'];
    S.ev = Object.entries(E.layers || {}).sort((a, b) => (ORDER.indexOf(a[0]) + 1 || 99) - (ORDER.indexOf(b[0]) + 1 || 99))
      .map(([k, l]) => ({ k, l, base: `../../events/${eid}/`, ov: L.imageOverlay('data:,', L.latLngBounds(l.bounds), { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map) }));
  } catch (e) { S.ev = []; }
  // the flow, as in the Story: the area → optical (clouds, canopy) → official radar map ("cannot see") → NISAR fills the blank
  const has = k => S.ev.some(x => x.k === k), E_ = ks => ks.filter(has).map(k => 'E_' + k);
  S.steps = [{ label: 'Area', b: 'none', on: [], cap: `The area${D.kind ? `: ${D.kind}` : ''}, ${fmt(D.frames[0].date, { month: 'short', year: 'numeric' })} → ${fmt(D.frames[D.frames.length - 1].date, { month: 'short', year: 'numeric' })}.` }];
  if (photos.length) S.steps.push({ label: 'Optical', b: 'photo', on: [], cap: 'Optical satellites: clouds and forest canopy hide the water.' });
  if (has('gfm_flood')) S.steps.push({ label: 'Official', b: 'none', on: E_(['gfm_flood', 'gfm_excluded']),
    cap: 'The official flood map (GFM) uses radar: it sees through clouds, but not under trees. Hatched = "cannot see".' });
  S.steps.push(has('nisar_adds')
    ? { label: 'NISAR', b: 'none', on: E_(['gfm_flood', 'gfm_excluded', 'nisar_adds']), cap: 'NISAR’s L-band radar sees under the canopy. <b class="o">Orange</b> = flood found in the blank.' }
    : { label: D.history ? 'Radar' : 'NISAR', b: 'nisar', on: ['pass'], cap: D.history ? 'Radar through the years: RADARSAT-1 (CSA), then NISAR. Blue = flood.' : 'NISAR’s L-band radar sees through clouds. Dark = water.' });
  S.step = 0;
  if (S.P && D.event_date) { const k = D.frames.findIndex(f => f.date >= D.event_date); if (k >= 0) S.t = k; }
  // volcano: vent + reference ring on the map, before / during interferograms side by side
  S.extra = [];
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

const R_ = D => D.report || {};
function setStep(i) {
  if (!S) return; S.step = Math.max(0, Math.min(S.steps.length - 1, i));
  const st = S.steps[S.step], n = S.steps.length; S.b = st.b; S.on = new Set(st.on);
  $('spS').innerHTML = S.steps.map((x, k) => `<button data-k="${k}" class="${k === S.step ? 'on' : k < S.step ? 'done' : ''}${x.label === 'NISAR' ? ' nisar' : ''}">${x.label}</button>`).join('<span class="sparr">→</span>');
  $('spCap').innerHTML = st.cap;
  $('spBk').style.visibility = S.step ? '' : 'hidden';
  $('spNx').textContent = S.step < n - 1 ? `Next: ${S.steps[S.step + 1].label} →` : '↺ Start over';
  render();
}
function closeSite(keepHash) {
  if (S) { ['base', 'over', 'box', 'tag', 'mo', 'fr'].forEach(k => S[k] && map.removeLayer(S[k])); (S.layers || []).forEach(l => map.removeLayer(l.ov)); (S.ev || []).forEach(x => map.removeLayer(x.ov)); (S.extra || []).forEach(x => map.removeLayer(x)); }
  const was = !!S; S = null; panel.hidden = true;
  if (was && keepHash !== 'swap') window.dispatchEvent(new CustomEvent('unseen:site', { detail: null }));
  if (!keepHash && location.hash.startsWith('#site=')) history.replaceState(null, '', location.pathname + location.search);
}

function render() {
  if (!S) return;
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
  S.base.setOpacity(S.b === 'none' ? 0 : 0.9);
  const tg = S.tag.getElement()?.firstChild, fy = d => fmt(d, { day: 'numeric', month: 'short', year: 'numeric' });
  if (tg) { const txt = S.b === 'photo' && S.pd && note.startsWith('Photo') ? `Optical · NASA HLS (Landsat / Sentinel-2) · ${fy(S.pd)}` : '';
    tg.textContent = txt; tg.style.display = txt ? '' : 'none'; }
  const on = S.on || new Set();
  S.over.setUrl(A(f.hidden)); S.over.setOpacity(on.has('pass') ? 1 : 0);
  (S.layers || []).forEach((l, i) => l.ov.setOpacity(on.has(`L${i}`) ? 1 : 0));
  const evNote = [];
  (S.ev || []).forEach(x => {                                    // the bundle's file nearest this pass (within 6 days)
    const ds = Object.keys(x.l.files || {}); let best = null;
    ds.forEach(d => { if (Math.abs(dn(d) - dn(f.date)) <= 6 && (!best || Math.abs(dn(d) - dn(f.date)) < Math.abs(dn(best) - dn(f.date)))) best = d; });
    if (best) x.ov.setUrl(x.base + x.l.files[best]); x.date = best;
    x.ov.setOpacity(best && on.has('E_' + x.k) ? 1 : 0);
    if (on.has('E_' + x.k) && !best) evNote.push(x.l.label || x.k);
  });
  let pr = null;
  if (S.P) {                                                       // the 12-day pair for this date (contains it, else nearest)
    const Ls = S.P.list, x = dn(f.date);
    pr = Ls.find(q => dn(q.ref) < x && x <= dn(q.sec)) || Ls.reduce((a, b) => Math.abs(dn(b.sec) - x) < Math.abs(dn(a.sec) - x) ? b : a);
    S.mo.setUrl(A(pr.motion)); S.fr.setUrl(A(pr.fringes));
    S.mo.setOpacity(on.has('motion') ? 1 : 0); S.fr.setOpacity(on.has('fringes') ? 1 : 0);
  }
  const seen = new Set();                                         // one legend per distinct scale
  const HATCH = 'repeating-linear-gradient(45deg,#c8c8d2 0 2px,#3c3c46 2px 6px)';
  $('spL').innerHTML = (S.ev || []).filter(x => on.has('E_' + x.k)).map(x => `<div><span style="background:${x.l.legend === 'hatch' ? HATCH : x.l.legend || '#888'}"></span>${x.l.label || x.k}</div>`).join('')
    + (evNote.length ? `<div class="sub">Not on this date: ${evNote.join(', ')}</div>` : '') + (pr && (on.has('motion') || on.has('fringes')) ? `<div class="pair${pr.event ? ' ev' : ''}">Pair ${fmt(pr.ref)} → ${fmt(pr.sec)}${pr.event ? ' · spans the event' : ''}</div>` : '')
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
function chart() {
  if (S.D.report && S.D.report.hazard === 'volcano') return vchart();
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 78, B = H - 12, { D, t } = S, n = D.frames.length;
  c.style.height = H + 'px'; c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio); g.clearRect(0, 0, W, H);
  const v = D.summary.map(S.nw), h = D.summary.map(S.hid), raw = Math.max(1, ...v);
  const step = 10 ** Math.floor(Math.log10(raw)), mx = Math.ceil(raw / step) * step, bw = (W - AX) / n, top = 4;
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
const pick = ev => { if (!S) return; const r = $('spC').getBoundingClientRect(); setT(Math.floor((ev.clientX - r.left - AX) / (r.width - AX) * S.D.frames.length)); };
let drag = false;
$('spC').onpointerdown = ev => { drag = true; $('spC').setPointerCapture(ev.pointerId); pick(ev); };
$('spC').onpointermove = ev => { if (drag) pick(ev); };
$('spC').onpointerup = $('spC').onpointercancel = () => { drag = false; };

function setT(i) { if (!S) return; S.t = Math.max(0, Math.min(S.D.frames.length - 1, i)); render(); }
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
