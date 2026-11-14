// Site viewer: NISAR vs optical swipe, hidden-change overlay, timeline (real time axis), season chart, pixel inspector.
(async () => {
const $ = id => document.getElementById(id);
const sid = new URLSearchParams(location.search).get('id');
if (!sid) { document.body.innerHTML = '<p style="padding:20px">No site selected. <a href="index.html">Back to the globe</a>.</p>'; return; }
const base = `sites/${encodeURIComponent(sid)}/`;
let D;
try { D = await (await fetch(base + 'site.json', { cache: 'no-cache' })).json(); }
catch (e) { document.body.innerHTML = `<p style="padding:20px">Site "${sid}" not found. <a href="index.html">Back to the globe</a>.</p>`; return; }
const asset = n => (D.assets && D.assets[n]) || base + n;   // assets may be inlined (single-file hosting)
D.frames.forEach(f => ['nisar', 'optical', 'hidden'].forEach(k => f[k] = asset(f[k])));
document.title = 'Unseen Earth — ' + D.title;

const F = D.frames, N = F.length, [W, H] = D.size, TL = D.timeline;
const DAY = 864e5, t0 = Date.parse(TL.start + 'T00:00:00Z');
const dayOf = d => Math.round((Date.parse(d + 'T00:00:00Z') - t0) / DAY);
const fmt = (d, o = { day: 'numeric', month: 'short' }) => new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { ...o, timeZone: 'UTC' });

$('title').textContent = 'Unseen Earth — ' + D.title;
const st = D.stack, v = D.validation || [];
const cal = D.calibration && D.calibration.used ? D.calibration : null, f1 = cal ? cal.loo.map(x => x.f1) : v.map(x => x.f1), yr = { day: 'numeric', month: 'short', year: 'numeric' };
$('info').innerHTML = `${N} NISAR passes · ${fmt(F[0].date)} → ${fmt(F[N - 1].date, yr)}`
  + (f1.length ? ` · matches optical water on clear days: F1 ${Math.min(...f1).toFixed(2)}–${Math.max(...f1).toFixed(2)}${cal ? ' (held-out days)' : ''}` : '')
  + ` <details class="more"><summary>details</summary>NISAR GCOV track ${st.track} ${st.direction}, frame ${st.frame}, mode ${st.mode} · ${st.n_dual}/${st.n_dates} passes with HV · ${Math.round(D.pixel_m)} m pixels · ${D.optical_dates} optical days`
  + (cal ? `<br>Water thresholds learned from ${cal.n_days} clear optical days: HH &lt; ${cal.open_hh} dB, HV &lt; ${cal.open_hv} dB (default −17/−24 scored F1 ${cal.f1_default.toFixed(2)}). Each day tested with thresholds learned on the other days: `
      + cal.loo.map(x => `${fmt(x.date)} ${x.f1.toFixed(2)}`).join(' · ') : '')
  + (!cal && v.length ? `<br>F1 per clear day: ` + v.map(x => `${fmt(x.date)} ${x.f1.toFixed(2)}`).join(' · ') : '') + `</details>`;
// ---------- time-to-first-look: after a known event, when did NISAR vs optical first see the area? ----------
const EV = new URLSearchParams(location.hash.slice(1)).get('event') || D.event_date;   // #event=YYYY-MM-DD overrides
let LOOK = null;
if (EV) {
  const after = d => d > EV, CLEAR = 0.5;
  const n = F.find(f => after(f.date)), o = (TL.optical || []).find(x => after(x.date) && x.clear >= CLEAR);
  const days = d => d ? Math.round((Date.parse(d + 'T00:00:00Z') - Date.parse(EV + 'T00:00:00Z')) / DAY) : null;
  LOOK = { ev: EV, nisar: n?.date, optical: o?.date, dn: days(n?.date), dop: days(o?.date) };
  const lastOpt = (TL.optical || []).length ? TL.optical[TL.optical.length - 1].date : TL.end;
  $('event').innerHTML = `<b>Event ${fmt(EV)}</b> · NISAR saw it ` + (n ? `after <b>${LOOK.dn} d</b>` : '<i>not yet</i>')
    + ` · a clear optical view came ` + (o ? `after <b>${LOOK.dop} d</b>` : `<span class="bad">not by ${fmt(lastOpt)}</span>`)
    + (n && (!o || LOOK.dop > LOOK.dn) ? ` · <b style="color:var(--orange)">NISAR first by ${o ? LOOK.dop - LOOK.dn : `> ${days(lastOpt) - LOOK.dn}`} day${o && LOOK.dop - LOOK.dn === 1 ? '' : 's'}</b>` : '');
}
['left', 'right', 'overL', 'overR'].forEach(id => { $(id).width = W; $(id).height = H; });
$('stage').style.width = W + 'px'; $('stage').style.height = H + 'px';

const dec = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
const TS = { hh: dec(D.ts.hh), hv: dec(D.ts.hv), water: dec(D.ts.water), h: D.ts.h, w: D.ts.w, step: D.ts.step };

let t = 0, swipeX = 0.5, overlayOn = true, sel = null, timer = null, mode = 'toggle', showB = false, flickT = null;
const view = { s: 1, x: 0, y: 0 };

// ---------- map ----------
function fit() {
  const r = $('mapwrap').getBoundingClientRect();
  view.s = Math.min(r.width / W, r.height / H); view.x = (r.width - W * view.s) / 2; view.y = (r.height - H * view.s) / 2; apply();
}
function apply() {
  $('stage').style.transform = `translate(${view.x}px,${view.y}px) scale(${view.s})`;
  const r = $('mapwrap').getBoundingClientRect(), sx = swipeX * r.width, swipe = mode === 'swipe';
  $('swipe').style.display = swipe ? '' : 'none'; $('swipe').style.left = sx + 'px';
  // toggle / flicker: B (the "right" layers) is either fully shown or fully hidden
  const pct = swipe ? 100 * Math.max(0, Math.min(W, (sx - view.x) / view.s)) / W : (showB ? 0 : 100);
  $('tagL').style.display = swipe || !showB ? '' : 'none'; $('tagR').style.display = swipe || showB ? '' : 'none';
  Object.assign($('tagR').style, swipe ? { left: '', right: '' } : { left: '10px', right: 'auto' });
  $('right').style.clipPath = $('cvR').style.clipPath = $('overR').style.clipPath = `inset(0 0 0 ${pct}%)`;
  $('overL').style.clipPath = $('cvL').style.clipPath = `inset(0 ${100 - pct}% 0 0)`;
  if (sel) placeMarker();
}
const LABEL = { nisar: 'NISAR L-band radar (R=HH G=HV B=HH/HV)', optical: 'Optical water map: white = clouds, blue = water, tan = land' };

// ---------- true-colour optical photo: NASA GIBS tiles of HLS (Landsat 8/9 + Sentinel-2, 30 m), no login ----------
// The stage is the NISAR UTM grid; tiles are Web Mercator. Each tile is placed by its lon/lat bounds using the same
// linear corner mapping as the pixel inspector (error < ~2 px for a 1° box at low/mid latitudes: UTM grid convergence).
const HLS = ['HLS_L30_Nadir_BRDF_Adjusted_Reflectance', 'HLS_S30_Nadir_BRDF_Adjusted_Reflectance'];
const gibs = (layer, d, z, x, y) => `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/${d}/GoogleMapsCompatible_Level12/${z}/${y}/${x}.png`;
const OPT = TL.optical || [];
const PHOTO = { photo: 'nearest', photoBest: 'clearest' };
function photoDay(i, mode) {           // which optical day to show for pass i
  const d0 = dayOf(F[i].date), gap = o => Math.abs(dayOf(o.date) - d0);
  const c = OPT.filter(o => gap(o) <= 5);
  if (!c.length) return { date: F[i].date, clear: null };      // no optical list: try the pass day itself
  c.sort(mode === 'nearest' ? (a, b) => gap(a) - gap(b) || b.clear - a.clear : (a, b) => b.clear - a.clear || gap(a) - gap(b));
  return c[0];
}
const photoCache = {};
function photo(d) {                    // offscreen canvas (stage size) filled progressively with tiles
  if (photoCache[d]) return photoCache[d];
  const [[lo0, la0], [lo1, la1]] = D.corners, c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'); g.fillStyle = '#1b1f24'; g.fillRect(0, 0, W, H);
  const P = { canvas: c, loaded: 0, total: 0, failed: 0 };
  if (D.photos && D.photos[d]) {                       // pre-rendered in the bundle (works offline / where remote images are blocked)
    const img = new Image(); P.total = 1;
    img.onload = () => { g.drawImage(img, 0, 0, W, H); P.loaded = 1; photoUpdated(); };
    img.onerror = () => { P.failed = 1; photoUpdated(); };
    img.src = asset(D.photos[d]);
    return (photoCache[d] = P);
  }
  const degPx = Math.abs(lo1 - lo0) / W, z = Math.max(3, Math.min(12, Math.ceil(Math.log2(360 / (256 * degPx))))), n = 2 ** z;
  const tx = lon => Math.floor((lon + 180) / 360 * n), r = Math.PI / 180;
  const ty = lat => Math.floor((1 - Math.log(Math.tan(lat * r) + 1 / Math.cos(lat * r)) / Math.PI) / 2 * n);
  const tlon = x => x / n * 360 - 180, tlat = y => Math.atan(Math.sinh(Math.PI * (1 - 2 * y / n))) / r;
  const sx = lon => (lon - lo0) / (lo1 - lo0) * W, sy = lat => (lat - la0) / (la1 - la0) * H;
  const lonA = Math.min(lo0, lo1), lonB = Math.max(lo0, lo1), latA = Math.min(la0, la1), latB = Math.max(la0, la1);
  HLS.forEach(layer => {
    for (let x = tx(lonA); x <= tx(lonB); x++) for (let y = ty(latB); y <= ty(latA); y++) {
      const img = new Image(); P.total++;
      img.onload = () => { const X0 = sx(tlon(x)), Y0 = sy(tlat(y)); g.drawImage(img, X0, Y0, sx(tlon(x + 1)) - X0, sy(tlat(y + 1)) - Y0); P.loaded++; photoUpdated(); };
      img.onerror = () => { P.failed++; photoUpdated(); };
      img.src = gibs(layer, d, z, x, y);
    }
  });
  return (photoCache[d] = P);
}
let photoRaf = 0;
function photoUpdated() { if (!photoRaf) photoRaf = requestAnimationFrame(() => { photoRaf = 0; render(); }); }
function showSide(side, key) {        // side 'L'|'R'
  const img = $(side === 'L' ? 'left' : 'right'), cv = $('cv' + side), tag = $('tag' + side);
  if (!PHOTO[key]) { img.style.display = ''; cv.style.display = 'none'; img.src = F[t][key]; tag.textContent = LABEL[key]; return; }
  const o = photoDay(t, PHOTO[key]), P = photo(o.date);
  img.style.display = 'none'; cv.style.display = ''; cv.width = W; cv.height = H; cv.getContext('2d').drawImage(P.canvas, 0, 0);
  const done = P.loaded + P.failed >= P.total;
  tag.textContent = `Optical photo (HLS true colour) ${fmt(o.date)}` + (o.clear != null ? ` · ${Math.round(100 * o.clear)}% clear` : '')
    + (done ? (P.loaded ? '' : ' · no image that day') : ` · loading ${P.loaded + P.failed}/${P.total}`);
}

function render() {
  const f = F[t], L = $('selL').value, R = $('selR').value, s = D.summary[t];
  showSide('L', L); showSide('R', R); $('overL').src = $('overR').src = f.hidden;
  $('overL').style.opacity = $('overR').style.opacity = overlayOn ? $('op').value / 100 : 0;
  const nw = x => x.new_water ?? x.nisar_water, hid = x => x.hidden_new ?? x.hidden_clouds;
  $('kWater').textContent = Math.round(nw(s)).toLocaleString();
  const pct = nw(s) > 0 ? hid(s) / nw(s) : 0;
  $('kHidden').textContent = nw(s) > 1 ? Math.round(100 * pct) + '%' : '–';
  $('kClear').textContent = Math.round(100 * f.optical_clear) + '%';
  $('kVeg').textContent = Math.round(s.veg_change).toLocaleString();
  const grow = Math.round(nw(s) - nw(D.summary[0]));
  $('story').innerHTML = t === 0
    ? `Baseline pass: everything later is compared with this one.`
    : (Math.max(...D.summary.map(nw)) > 5 ? `Water ${grow >= 0 ? '+' : '−'}${Math.abs(grow).toLocaleString()} km² since ${fmt(F[0].date)}.` : '')
      + (nw(s) > 1 && pct > 0.05 ? ` <b>${Math.round(100 * pct)}%</b> of it was under cloud for optical satellites.` : '');
  drawTimeline(); drawChart(); drawPix();
}

// ---------- timeline: real time axis, NISAR passes on top, optical clear-sky below ----------
const tlc = $('timeline');
function tlGeom() {
  const w = tlc.clientWidth, pad = { l: 12, r: 12 };
  const span = TL.days + 6, X = d => pad.l + (dayOf(d) + 3) / span * (w - pad.l - pad.r);
  return { w, h: tlc.clientHeight, X };
}
function drawTimeline() {
  const g = tlc.getContext('2d'); tlc.width = tlc.clientWidth * devicePixelRatio; tlc.height = tlc.clientHeight * devicePixelRatio;
  g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  const { w, h, X } = tlGeom(); g.clearRect(0, 0, w, h); g.font = '11px system-ui';
  const yN = 30, yO0 = 52, yO1 = 82;      // NISAR row centre, optical bar band
  // month grid
  const s = new Date(TL.start + 'T00:00:00Z'), e = new Date(TL.end + 'T00:00:00Z');
  for (let m = new Date(Date.UTC(s.getUTCFullYear(), s.getUTCMonth(), 1)); m <= e; m.setUTCMonth(m.getUTCMonth() + 1)) {
    const d = m.toISOString().slice(0, 10), x = X(d);
    if (x < 0) continue;
    g.strokeStyle = '#2a313c'; g.beginPath(); g.moveTo(x, 4); g.lineTo(x, h); g.stroke();
    g.fillStyle = '#8b95a3'; g.fillText(m.toLocaleDateString('en-GB', { month: 'short', timeZone: 'UTC' }), x + 3, 12);
  }
  // optical observations: bar height = clear-sky fraction of the area
  (TL.optical || []).forEach(o => {
    const x = X(o.date), bh = Math.max(1.5, o.clear * (yO1 - yO0));
    g.fillStyle = o.clear > 0.5 ? '#d7dde5' : o.clear > 0.15 ? '#8b95a3' : '#4a525e'; g.fillRect(x - 1.5, yO1 - bh, 3, bh);
  });
    if (LOOK) {
    const x = X(LOOK.ev); g.strokeStyle = '#f85149'; g.lineWidth = 2; g.beginPath(); g.moveTo(x, 14); g.lineTo(x, yO1); g.stroke(); g.lineWidth = 1;
    g.fillStyle = '#f85149'; g.fillText('event', x + 3, yO1 + 0 - 34);
  }
  // NISAR passes, gaps > repeat cycle flagged
  F.forEach((f, i) => {
    const x = X(f.date);
    if (i && TL.gaps[i] > TL.repeat_days * 1.5) {
      const xp = X(F[i - 1].date); g.strokeStyle = '#f8514988'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(xp, yN); g.lineTo(x, yN); g.stroke(); g.setLineDash([]);
      g.fillStyle = '#f85149'; g.fillText(`${TL.gaps[i]} d`, (xp + x) / 2 - 10, yN - 7);
    }
    g.fillStyle = i === t ? '#2f81f7' : '#ff7828'; g.beginPath(); g.arc(x, yN, i === t ? 7 : 4.5, 0, 7); g.fill();
    if (i === t) { g.strokeStyle = '#2f81f7'; g.lineWidth = 1.5; g.beginPath(); g.moveTo(x, yN); g.lineTo(x, yO1); g.stroke(); g.lineWidth = 1; }
  });
  const f = F[t];
  $('tlRange').innerHTML = `<span style="color:#ff7828">●</span> NISAR passes · <span style="color:#d7dde5">▮</span> optical clear sky`;
  $('tlNow').innerHTML = `<b>${fmt(f.date, { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}</b>`
    + (t ? ` · ${TL.gaps[t]} d after the last pass${TL.gaps[t] > TL.repeat_days * 1.5 ? ` <span class="bad">(${Math.round(TL.gaps[t] / TL.repeat_days) - 1} missing)</span>` : ''}` : ' · baseline');
}
tlc.addEventListener('click', e => {
  const r = tlc.getBoundingClientRect(), { X } = tlGeom(), x = e.clientX - r.left;
  let best = 0; F.forEach((f, i) => { if (Math.abs(X(f.date) - x) < Math.abs(X(F[best].date) - x)) best = i; });
  t = best; render();
});

// ---------- season chart (x = real time) ----------
function axes(c) {
  const g = c.getContext('2d'); c.width = c.clientWidth * devicePixelRatio; c.height = c.clientHeight * devicePixelRatio;
  g.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  const W2 = c.clientWidth, H2 = c.clientHeight, pad = { l: 44, r: 8, t: 8, b: 22 };
  g.clearRect(0, 0, W2, H2); g.font = '11px system-ui'; g.fillStyle = '#8b95a3'; g.strokeStyle = '#2a313c';
  const X = d => pad.l + dayOf(d) / Math.max(TL.days, 1) * (W2 - pad.l - pad.r);
  return { g, W2, H2, pad, X };
}
function drawChart() {
  const S = D.summary, ymax = Math.max(10, ...S.map(s => Math.max(s.nisar_water, s.veg_change))) * 1.08;
  const { g, W2, H2, pad, X } = axes($('chart')), Yv = v => H2 - pad.b - v / ymax * (H2 - pad.t - pad.b);
  const stepY = Math.pow(10, Math.floor(Math.log10(ymax))) * (ymax / Math.pow(10, Math.floor(Math.log10(ymax))) > 4 ? 1 : .5);
  for (let y = 0; y <= ymax; y += stepY) { g.beginPath(); g.moveTo(pad.l, Yv(y)); g.lineTo(W2 - pad.r, Yv(y)); g.stroke(); g.fillText(Math.round(y).toLocaleString(), 2, Yv(y) + 4); }
  [S[0], S[Math.floor(S.length / 2)], S[S.length - 1]].forEach(s => g.fillText(fmt(s.date), X(s.date) - 16, H2 - 6));
  g.fillStyle = 'rgba(47,129,247,.18)'; g.fillRect(X(S[t].date) - 5, pad.t, 10, H2 - pad.t - pad.b);
  const line = (k, col, w) => {
    g.strokeStyle = col; g.lineWidth = w; g.beginPath(); S.forEach((s, i) => i ? g.lineTo(X(s.date), Yv(s[k])) : g.moveTo(X(s.date), Yv(s[k]))); g.stroke();
    g.fillStyle = col; S.forEach((s, i) => { g.beginPath(); g.arc(X(s.date), Yv(s[k]), i === t ? 4.5 : 2.5, 0, 7); g.fill(); });
  };
  line('nisar_water', '#dddddd', 2); line('both', '#2b8cbe', 2.5); line('hidden_clouds', '#ff7828', 2.5); line('hidden_canopy', '#31a354', 2); line('veg_change', '#be50dc', 2);
  g.lineWidth = 1;
}

// ---------- pixel inspector ----------
function lonlat(px, py) { const [[lo0, la0], [lo1, la1]] = D.corners; return [lo0 + (lo1 - lo0) * px / W, la0 + (la1 - la0) * py / H]; }
function placeMarker() { const m = $('marker'); m.style.display = 'block'; m.style.left = sel.x + 'px'; m.style.top = sel.y + 'px'; m.style.transform = `scale(${1 / view.s})`; }
function drawPix() {
  const c = $('pchart');
  if (!sel) { c.getContext('2d').clearRect(0, 0, c.width, c.height); return; }
  const i = Math.min(TS.h - 1, Math.floor(sel.y / TS.step)), j = Math.min(TS.w - 1, Math.floor(sel.x / TS.step));
  const get = (arr, k) => arr[k * TS.h * TS.w + i * TS.w + j];
  const hh = F.map((_, k) => get(TS.hh, k) / 4 - 35), hv = F.map((_, k) => get(TS.hv, k) / 4 - 35), wt = F.map((_, k) => get(TS.water, k));
  const [lo, la] = lonlat(sel.x, sel.y), first = wt.indexOf(1);
  $('pix').innerHTML = `≈ ${la.toFixed(3)}°, ${lo.toFixed(3)}° · ` + (first < 0 ? 'no water detected' : first === 0 ? 'water from the first pass' : `water arrives by <b>${fmt(F[first].date)}</b> (day ${dayOf(F[first].date)})`)
    + ` · water on ${wt.filter(Boolean).length}/${N} passes`;
  const { g, W2, H2, pad, X } = axes(c), lo_ = -30, hi_ = 0, Yv = v => H2 - pad.b - (v - lo_) / (hi_ - lo_) * (H2 - pad.t - pad.b);
  for (let y = lo_; y <= hi_; y += 10) { g.beginPath(); g.moveTo(pad.l, Yv(y)); g.lineTo(W2 - pad.r, Yv(y)); g.stroke(); g.fillText(y + ' dB', 2, Yv(y) + 4); }
  wt.forEach((w, k) => { if (w) { g.fillStyle = 'rgba(43,140,190,.25)'; g.fillRect(X(F[k].date) - 6, pad.t, 12, H2 - pad.t - pad.b); } });
  g.fillStyle = 'rgba(47,129,247,.3)'; g.fillRect(X(F[t].date) - 1.5, pad.t, 3, H2 - pad.t - pad.b);
  [[hh, '#ff6b6b', 'HH'], [hv, '#7ee787', 'HV']].forEach(([a, col, name], q) => {
    g.strokeStyle = col; g.lineWidth = 2; g.beginPath(); a.forEach((y, k) => k ? g.lineTo(X(F[k].date), Yv(y)) : g.moveTo(X(F[k].date), Yv(y))); g.stroke();
    g.fillStyle = col; g.fillText(name, W2 - 30, pad.t + 12 + q * 13);
  });
  g.fillStyle = '#8b95a3'; [F[0], F[N - 1]].forEach(f => g.fillText(fmt(f.date), X(f.date) - 16, H2 - 6)); g.lineWidth = 1;
  placeMarker();
}

// ---------- interaction ----------
const wrap = $('mapwrap'); let drag = null, moved = false, swiping = false;
$('swipe').addEventListener('mousedown', e => { swiping = true; e.stopPropagation(); });
wrap.addEventListener('mousedown', e => { drag = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y }; moved = false; wrap.style.cursor = 'grabbing'; });
window.addEventListener('mousemove', e => {
  const r = wrap.getBoundingClientRect();
  if (swiping) { swipeX = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width)); apply(); return; }
  if (!drag) return;
  const dx = e.clientX - drag.x, dy = e.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
  view.x = drag.vx + dx; view.y = drag.vy + dy; apply();
});
window.addEventListener('mouseup', e => {
  if (drag && !moved && !swiping) {
    const r = wrap.getBoundingClientRect(), px = (e.clientX - r.left - view.x) / view.s, py = (e.clientY - r.top - view.y) / view.s;
    if (px >= 0 && py >= 0 && px < W && py < H) { sel = { x: px, y: py }; drawPix(); }
  }
  drag = null; swiping = false; wrap.style.cursor = 'grab';
});
wrap.addEventListener('wheel', e => {
  e.preventDefault(); const r = wrap.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  const s2 = Math.min(12, Math.max(0.2, view.s * Math.exp(-e.deltaY * 0.0015)));
  view.x = mx - (mx - view.x) * s2 / view.s; view.y = my - (my - view.y) * s2 / view.s; view.s = s2; apply();
}, { passive: false });
$('selL').onchange = $('selR').onchange = render;
$('op').oninput = render;
const flip = () => { showB = !showB; apply(); };
function setMode(m) {
  mode = m; clearInterval(flickT); flickT = null;
  if (m === 'flicker') flickT = setInterval(flip, 800);
  $('flip').disabled = m === 'swipe'; apply();
}
$('cmp').onchange = () => setMode($('cmp').value);
$('flip').onclick = () => { if (mode === 'flicker') { $('cmp').value = 'toggle'; setMode('toggle'); } flip(); };
$('ovl').onclick = () => { overlayOn = !overlayOn; $('ovl').classList.toggle('on', overlayOn); render(); };
$('reset').onclick = fit;
const togglePlay = () => {
  if (timer) { clearInterval(timer); timer = null; $('play').textContent = '▶ Play'; return; }
  $('play').textContent = '❚❚ Pause'; timer = setInterval(() => { t = (t + 1) % N; render(); }, 900);
};
$('play').onclick = togglePlay;
window.addEventListener('keydown', e => {
  if (e.key === 'ArrowRight') { t = Math.min(N - 1, t + 1); render(); }
  if (e.key === 'ArrowLeft') { t = Math.max(0, t - 1); render(); }
  if (e.key === ' ') { e.preventDefault(); togglePlay(); }
  if (e.key === 't' || e.key === 'T') { if (mode === 'swipe') { $('cmp').value = 'toggle'; setMode('toggle'); } flip(); }
});
window.addEventListener('resize', () => { fit(); render(); });

// deep links: site.html?id=...#t=<pass>&L=nisar|optical&R=...&swipe=0..1
const h = new URLSearchParams(location.hash.slice(1));
if (h.has('t')) t = Math.max(0, Math.min(N - 1, +h.get('t')));
if (h.has('L')) $('selL').value = h.get('L');
if (h.has('R')) $('selR').value = h.get('R');
if (h.has('swipe')) { swipeX = +h.get('swipe'); $('cmp').value = 'swipe'; }
if (h.has('mode')) $('cmp').value = h.get('mode');
if (h.has('B')) showB = h.get('B') === '1';
fit(); render(); setMode($('cmp').value);
})();
