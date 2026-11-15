// Globe: gallery of explored areas (static, from sites/index.json) + optional draw-and-analyze (needs the server).
const $ = id => document.getElementById(id);
const API = window.UNSEEN_CONFIG?.apiBase;
// one copy of the world: no horizontal repeats; fully zoomed out = the whole world fits the window (fractional zoom)
const WORLD = L.latLngBounds([[-85, -180], [85, 180]]);
const map = window.UNSEEN_MAP = L.map('map', { worldCopyJump: false, maxBounds: WORLD, maxBoundsViscosity: 1.0, zoomSnap: 0.25, zoomDelta: 0.5, minZoom: 0 })
  .setView(...((m => m ? [[+m[1], +m[2]], +m[3]] : [[10, 40], 2])(location.hash.match(/^#view=(-?[\d.]+),(-?[\d.]+),([\d.]+)/))));
map.attributionControl.setPrefix('ⓘ');                        // credits collapse to an ⓘ, expand on hover
const fitMinZoom = () => {
  const { x, y } = map.getSize(), z = Math.floor(4 * Math.log2(Math.min(x, y) / 256)) / 4;   // world (square in Web Mercator) fits
  map.setMinZoom(Math.max(0, z)); if (map.getZoom() < z) map.setZoom(z);
};
map.on('resize', fitMinZoom); fitMinZoom();
// local fallback basemap (NASA Blue Marble + EOX patches) sits UNDER the live tiles: sharp imagery wins when online,
// the fallback shows only where remote tiles are blocked or offline
map.createPane('fallback').style.zIndex = 150;                       // below the tile pane (200)
L.imageOverlay('img/basemap.jpg', [[-85.0511, -180], [85.0511, 180]], { pane: 'fallback', attribution: 'NASA Blue Marble (GIBS)' }).addTo(map);
const imagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 18, noWrap: true, bounds: WORLD, attribution: 'Esri, Maxar, Earthstar Geographics' }).addTo(map);
const labels = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 18, opacity: .8, noWrap: true, bounds: WORLD }).addTo(map);
const siteLayer = L.layerGroup().addTo(map), covLayer = L.layerGroup().addTo(map), watchLayer = L.layerGroup().addTo(map), eventLayer = L.layerGroup().addTo(map);
const fmtDate = d => new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

// ---------- data: analysed sites + disasters (GDACS) + watched areas -> one feed, one map ----------
const EVT = { EQ: 'Earthquake', FL: 'Flood', VO: 'Volcano', WF: 'Wildfire', TC: 'Cyclone', DR: 'Drought', SITE: 'Area' };
const ICON = { EQ: '〰', FL: '💧', VO: '🌋', WF: '🔥', TC: '🌀', DR: '☀', LS: '⛰', CL: '🌳', SUB: '🕳', SITE: '📡' };
EVT.LS = 'Landslide'; EVT.CL = 'Forest clearing'; EVT.SUB = 'Subsidence';
// what an analysed area is about, from its hazard code or its description (areas we picked ourselves, not from GDACS)
const siteType = s => { const k = `${s.kind || ''} ${s.title || ''}`.toLowerCase();
  return /landslide|debris|avalanche/.test(k) ? 'LS' : /sinkhole|subsid/.test(k) ? 'SUB' : /clearing|deforest/.test(k) ? 'CL'
    : s.hazard || (/flood|inund|wetland/.test(k) ? 'FL' : /volcan|erupt|lava/.test(k) ? 'VO' : /fire|burn/.test(k) ? 'WF' : /quake/.test(k) ? 'EQ' : 'SITE'); };
const getJSON = async u => { try { return await (await fetch(u, { cache: 'no-store' })).json(); } catch (e) { return null; } };
const inBox = (b, lat, lon) => b && lon >= b[0] && lon <= b[2] && lat >= b[1] && lat <= b[3];
const D0 = '2026-06-17', TODAY = new Date().toISOString().slice(0, 10);
const dnum = d => Date.parse(d + 'T00:00:00Z') / 864e5;
let ITEMS = [], filt = 'all', sortBy = 'new', tStart = null, tEnd = null;   // time range (null = all time)

// sharp basemap patches around areas (Sentinel-2 cloudless, EOX), for hosts that block live map tiles
getJSON('img/base/index.json').then(P => (P || []).forEach(p => L.imageOverlay(p.data || 'img/base/' + p.file, p.bounds, { pane: 'fallback', opacity: 1, attribution: 'Sentinel-2 cloudless by EOX (Copernicus data)' }).addTo(baseLayer)));
const baseLayer = L.layerGroup().addTo(map); baseLayer.setZIndex?.(1);

async function loadAll() {
  let [S, E, W, WD] = await Promise.all([getJSON('sites/index.json'), getJSON('sites/events.json'), getJSON('sites/watch.json'), getJSON('../../events/world/event.json')]);
  if (!S) S = await getJSON('sites/samples.json');      // fresh clone / static hosting: only the committed samples
  // NISAR gain per site (water in the official map's blank vs the official flood area), from the world bundle
  (S || []).forEach(s => { const w = !s.history && ((WD && WD.sites) || []).find(x => s.id.startsWith(x.id)); if (w) s.gain = w; });
  window.UNSEEN_SITES = S || []; window.dispatchEvent(new Event('unseen:sites'));
  const sites = window.UNSEEN_SITES, wa = (W && W.areas) || [], used = new Set();
  ITEMS = [];
  ((E && E.events) || []).forEach(e => {
    const site = sites.find(s => inBox(s.bbox, e.lat, e.lon));
    if (site) used.add(site.id);
    ITEMS.push({ kind: 'event', type: e.type, date: e.date, lat: e.lat, lon: e.lon, alert: e.alert, e, site,
      title: `${EVT[e.type] || e.type} · ${e.country.split(',')[0]}`, score: e.rating ? e.rating.score : -1 });
  });
  sites.filter(s => !used.has(s.id)).forEach(s => {
    const [w, so, ea, n] = s.bbox;
    ITEMS.push({ kind: 'site', type: siteType(s), date: s.event_date || s.last, lat: (so + n) / 2, lon: (w + ea) / 2, site: s, title: s.title, score: -1 });
  });
  // "new since your last visit": events not seen before get a NEW badge (kept per browser)
  let seen = null; try { seen = JSON.parse(localStorage.getItem('unseen_seen') || 'null'); } catch (e) {}
  const ids = ITEMS.filter(it => it.e).map(it => it.e.id);
  if (seen) ITEMS.forEach(it => { it.isNew = !!(it.e && !seen.includes(it.e.id)); });
  try { localStorage.setItem('unseen_seen', JSON.stringify([...new Set([...(seen || []), ...ids])])); } catch (e) {}
  FEED_CHECKED = E && E.checked;
  drawMap(wa); renderFeed(); setupSlider(); showFocus(FOCUS);
}
// live feed: the server refreshes GDACS every hour (server/app.py --events); poll the file and pull in new events
let FEED_CHECKED = null;
setInterval(async () => {
  const E = await getJSON('sites/events.json');
  if (!E || !E.checked || E.checked === FEED_CHECKED) return;
  const before = new Set(ITEMS.filter(it => it.e).map(it => it.e.id));
  await loadAll();
  const fresh = ITEMS.filter(it => it.e && !before.has(it.e.id));
  fresh.forEach(it => { it.isNew = true; }); if (fresh.length) renderFeed();
  if (fresh.length) {
    let t = $('toast'); if (!t) { t = document.createElement('div'); t.id = 'toast'; $('leftcol').appendChild(t); }
    t.innerHTML = `<b>New:</b> ${fresh.slice(0, 3).map(it => `${ICON[it.type] || ''} ${it.title}`).join(' · ')}${fresh.length > 3 ? ` +${fresh.length - 3}` : ''}`;
    t.onclick = () => { flyTo(fresh[0]); t.remove(); }; setTimeout(() => t.remove(), 20000);
  }
}, 5 * 60 * 1000);

// ---------- map layers ----------
function drawMap(wa) {
  siteLayer.clearLayers(); watchLayer.clearLayers(); eventLayer.clearLayers();
  (window.UNSEEN_SITES || []).forEach(s => {
    const [w, so, e, n] = s.bbox;
    L.rectangle([[so, w], [n, e]], { color: '#ff7828', weight: 2, fillOpacity: .08 })
      .bindPopup(`<b>${s.title}</b><br>${fmtDate(s.first)} → ${fmtDate(s.last)} · ${s.history ? `${s.n_rs1} RADARSAT-1 + ${s.n_nisar} NISAR images` : `${s.n_dates} passes`}<br><a href="#site=${encodeURIComponent(s.id)}">open analysis</a>`).addTo(siteLayer);
  });
  const sites = new Set((window.UNSEEN_SITES || []).map(s => s.id));
  wa.filter(a => !(a.site && sites.has(a.site))).forEach(a => {
    const [w, so, e, n] = a.bbox;
    L.rectangle([[so, w], [n, e]], { color: '#8b95a3', weight: 1, dashArray: '4 4', fillOpacity: .03 })
      .bindPopup(`<b>${a.name}</b><br><span class="sub">${a.message || a.state}</span>`).addTo(watchLayer);
  });
  ITEMS.filter(it => it.kind === 'event').forEach(it => {
    const e = it.e, ok = e.nisar && e.nisar.status === 'ok', col = e.alert === 'Red' ? '#f85149' : '#ff9f1c', r = e.rating;
    const html = `<b>${ICON[e.type] || ''} ${EVT[e.type] || e.type}</b> · ${e.country}<br>${fmtDate(e.date)} · GDACS ${e.alert}`
      + (e.charter ? ` · <a href="${e.charter.url}" target="_blank">Charter</a>` : '')
      + (r ? `<br><b>Radar needed ${r.radar_needed ?? '–'} · NISAR edge ${r.nisar_edge ?? '–'}</b><br><span class="sub">${r.why.join('<br>')}</span>`
           : `<br><span class="sub">NISAR: ${(e.nisar || {}).status || '–'}</span>`)
      + (it.site ? `<br><a href="#site=${encodeURIComponent(it.site.id)}"><b>open analysis</b></a>` : '')
      + ` · <a href="${e.url}" target="_blank">GDACS ↗</a>`;
    const icon = L.divIcon({ className: '', iconSize: [26, 26], iconAnchor: [13, 13],
      html: `<div class="evi${ok ? ' ok' : ''}${e.charter ? ' ch' : ''}${it.site ? ' an' : ''}" style="--c:${col}">${ICON[e.type] || '•'}</div>` });
    it.marker = L.marker([e.lat, e.lon], { icon, title: it.title }).bindPopup(() => html + anLink(it)).addTo(eventLayer);
  });
}

// ---------- search: every word must match (word start > substring > fuzzy, typos allowed); best matches first ----------
const MONTHS = ['january','february','march','april','may','june','july','august','september','october','november','december'];
const hay = it => {
  const e = it.e || {}, s = it.site || {}, d = new Date(it.date + 'T00:00:00Z');
  return [it.title, e.name, e.country, s.title, s.kind, EVT[it.type], it.type, e.alert, e.charter ? 'charter' : '', it.site ? 'analysed analyzed' : '',
          MONTHS[d.getUTCMonth()], String(d.getUTCFullYear()), it.date].filter(Boolean).join(' ').toLowerCase();
};
function lev(a, b, max) {                                 // edit distance with early exit
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let p = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    const c = [i]; let lo = i;
    for (let j = 1; j <= b.length; j++) { c[j] = Math.min(p[j] + 1, c[j - 1] + 1, p[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1)); lo = Math.min(lo, c[j]); }
    if (lo > max) return max + 1; p = c;
  }
  return p[b.length];
}
function match(q, h) {
  const words = h.split(/[^a-z0-9À-ɏ-]+/).filter(Boolean);
  let total = 0;
  for (const t of q.split(/\s+/)) {
    let best = 0;
    if (words.some(w => w === t)) best = 10;
    else if (words.some(w => w.startsWith(t))) best = 8;
    else if (h.includes(t)) best = 6;
    else {
      const max = t.length <= 3 ? 0 : t.length <= 6 ? 1 : 2;   // typos: 1 for short words, 2 for long
      const d = Math.min(...words.map(w => lev(t, w.slice(0, t.length + 1), max)), ...words.map(w => lev(t, w, max)));
      if (d <= max) best = 5 - d;
      else if (t.length >= 4 && words.some(w => { let i = 0; for (const ch of w) if (ch === t[i]) i++; return i === t.length; })) best = 1;   // letters in order within a word (abbreviations)
    }
    if (!best) return 0;
    total += best;
  }
  return total;
}
let qT = null;
$('q').oninput = () => { clearTimeout(qT); qT = setTimeout(renderFeed, 60); };
$('q').onkeydown = ev => { if (ev.key === 'Enter') { const f = $('feed').querySelector('.fitem'); f && f.click(); } if (ev.key === 'Escape') { $('q').value = ''; renderFeed(); } };

// ---------- feed (right panel): newest first or by score; filter chips; click = smooth fly ----------
const visible = it => (filt === 'all' || (filt === 'analyzed' ? !!it.site : filt === 'edge' ? it.score >= 50 : it.type === filt))
  && (!tEnd || (dnum(it.date) >= dnum(tStart) && dnum(it.date) <= dnum(tEnd)));
function renderFeed() {
  const q = ($('q').value || '').trim().toLowerCase();
  if (q) ITEMS.forEach(it => { it.qs = match(q, hay(it)); });
  const L_ = ITEMS.filter(it => visible(it) && (!q || it.qs > 0)).sort((a, b) => q ? b.qs - a.qs || b.date.localeCompare(a.date)
    : sortBy === 'score' ? b.score - a.score : b.date.localeCompare(a.date));
  $('feed').innerHTML = L_.length ? '' : '<div class="sub" style="padding:10px">Nothing here for this filter / time.</div>';
  L_.forEach(it => {
    const c = document.createElement('div');
    c.className = 'fitem' + (PICK.has(key(it)) ? ' picked' : '');
    const day = new Date(it.date + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
    const g = it.site && it.site.gain;
    const gain = g && g.pct != null ? `+${g.pct.toLocaleString()}%` : g && g.nisar_adds_km2 >= 1 ? `+${Math.round(g.nisar_adds_km2).toLocaleString()} km²` : '';
    c.innerHTML = `<div class="fbody"><div class="ftitle">${it.title}</div><div class="fdate">${day}</div></div>`
      + (gain ? `<div class="fgain" title="More flood water NISAR found than the official flood map showed">${gain}</div>` : '');
    c.onclick = ev => {
      if (ev.target.classList.contains('fsel')) { PICK.has(key(it)) ? PICK.delete(key(it)) : PICK.add(key(it)); c.classList.toggle('picked'); batchBar(); return; }
      if (ev.target.tagName === 'A') return; it.site ? window.openSite(it.site.id) : flyTo(it); };
    c.onmouseenter = () => it.marker && it.marker.getElement()?.classList.add('hl');
    c.onmouseleave = () => it.marker && it.marker.getElement()?.classList.remove('hl');
    $('feed').appendChild(c);
  });
  ITEMS.forEach(it => { if (it.marker) it.marker.setOpacity(visible(it) ? 1 : 0.12); });
  $('fcount').textContent = `${L_.length} of ${ITEMS.length}`;
  SHOWN = L_; batchBar();
}

// ---------- batch: tick events (or take everything the filters/search/time range show) and queue them all ----------
const PICK = new Set(); let SHOWN = [], RUNNING_NAMES = new Set();
const key = it => it.e ? it.e.id : it.site?.id;
const jobName = it => `${it.title} ${it.e.date.slice(0, 7)}`;
const canRun = it => window.UNSEEN_LIVE && it.e && !it.site;
function batchBar() {
  if (!window.UNSEEN_LIVE) { $('batch').hidden = true; return; }
  const picked = ITEMS.filter(it => PICK.has(key(it)) && canRun(it)), todo = picked.length ? picked : SHOWN.filter(canRun);
  const fresh = todo.filter(it => !RUNNING_NAMES.has(jobName(it)));
  $('batch').hidden = !todo.length; $('bask').hidden = true; $('bgo').hidden = false; $('bclr').hidden = !picked.length;
  $('bgo').textContent = `▶ Analyze ${picked.length ? 'selected' : 'all shown'} (${fresh.length})`;
  $('bgo').disabled = !fresh.length;
  $('bgo').onclick = () => { $('bgo').hidden = true; $('bask').hidden = false;
    $('byes').textContent = `Queue ${fresh.length} (~${Math.round(fresh.length * 4.5)} min)`; };
  $('bno').onclick = () => batchBar();
  $('bclr').onclick = () => { PICK.clear(); renderFeed(); };
  $('byes').onclick = async () => {
    $('bask').hidden = true;
    let n = 0;
    for (const it of fresh) {
      const e = it.e, nf = e.nisar || {};
      const bb = nf.status === 'ok' && nf.bbox ? nf.bbox : [e.lon - .5, e.lat - .5, e.lon + .5, e.lat + .5].map(v => +v.toFixed(4));
      const r = await fetch(API + '/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bbox: bb, name: jobName(it), event_date: e.date, kind: `${(EVT[e.type] || e.type).toLowerCase()} (GDACS ${e.alert})` }) });
      if (r.ok) { n++; RUNNING_NAMES.add(jobName(it)); }
    }
    PICK.clear(); jobToast(`Queued ${n} analyses. Progress in Jobs.`); setTimeout(() => jobToast(''), 6000);
    renderFeed(); refreshJobs();
  };
}
// ---------- focus: a picked event replaces the list in the sidebar; "All events" brings the list back ----------
let FOCUS = null;
const focusBox = document.createElement('div'); focusBox.id = 'focus'; focusBox.hidden = true;
$('feed').before(focusBox);
const num = v => typeof v === 'number' ? v.toLocaleString('en-GB') : v;
const BASE_NAME = { gfm: 'Official map (GFM)', dswx: 'NASA OPERA DSWx' };
function gainHTML(m) {
  if (m.base == null || m.adds == null) return '';
  const km = v => `${Math.round(v).toLocaleString('en-GB')}<small> km²</small>`;
  return `<div class="gcol"><b class="gbase">${km(m.base)}</b><span>${BASE_NAME[m.baseline] || 'Official map'}</span></div>`
    + `<div class="gcol"><b class="gadd">+${km(m.adds)}</b><span>NISAR addition</span></div>`
    + (m.pct != null ? `<div class="gpct"><span class="garrow">↑</span><b>${m.pct.toLocaleString('en-GB')}%</b><span>more flood seen with NISAR</span></div>` : '');
}
let V2 = null;
async function loadSummary(s) {
  if (V2 === null) V2 = (await getJSON('../../events/index.json')) || {};
  const pl = ((V2.version === 2 && V2.places) || []).find(p => s.id.startsWith(p.id));
  const fl = pl && pl.floods && pl.floods.length && [...pl.floods].sort((a, b) => (b.flood_date || '').localeCompare(a.flood_date || ''))[0];
  if (!fl) return null;
  const ev = await getJSON(`../../events/${pl.folder || pl.id}/${fl.id}/event.json`), m = ev && ev.summary;
  return m ? { base: m.baseline_flood_km2, adds: m.nisar_adds_km2, pct: m.improvement_pct, baseline: m.baseline } : null;
}
function showFocus(id) {
  FOCUS = id || null;
  const s = FOCUS && (window.UNSEEN_SITES || []).find(x => x.id === FOCUS);
  document.body.classList.toggle('focused', !!FOCUS);
  focusBox.hidden = !FOCUS;
  if (!FOCUS) return;
  const yr = d => d.slice(0, 4), g = s && s.gain;
  const when = !s ? '' : s.history ? `${yr(s.first)}–${yr(s.last)}` : fmtDate((g && g.date) || s.event_date || s.last);
  const tags = !s ? '' : (s.history ? '<span class="stag">RADARSAT-1</span>' : '') + '<span class="stag nisar">NISAR</span>';
  focusBox.innerHTML = `<button class="fback" type="button">← All events</button>`
    + (!s ? '<div class="sub">Loading…</div>' : `<div class="fcard">
      <h2>${s.title}</h2>
      <div class="fwhen">${when}</div>
      <div class="stags">${tags}</div>
      <div class="gainbox" id="gainbox">${g ? gainHTML({ base: g.gfm_flood_km2, adds: g.nisar_adds_km2, pct: g.pct, baseline: 'gfm' }) : ''}</div>
      </div>`);
  // v2 metadata (docs/12): events/<place>/<flood>/event.json, summary = wettest pass vs the main baseline
  if (s && !s.history) loadSummary(s).then(m => { const box = $('gainbox'); if (m && box && FOCUS === s.id) box.innerHTML = gainHTML(m); });
  focusBox.querySelector('.fback').onclick = () => {
    window.closeSite && window.closeSite();
    const all = (window.UNSEEN_SITES || []).map(x => [[x.bbox[1], x.bbox[0]], [x.bbox[3], x.bbox[2]]]).flat();
    if (all.length) map.flyToBounds(L.latLngBounds(all), { padding: [60, 60], maxZoom: 4, duration: 1.2 });
  };
  focusBox.scrollTop = 0;
}
window.addEventListener('unseen:site', e => showFocus(e.detail));

function flyTo(it) {
  const z = it.site ? Math.min(9, map.getBoundsZoom(L.latLngBounds([[it.site.bbox[1], it.site.bbox[0]], [it.site.bbox[3], it.site.bbox[2]]]))) : 8;
  map.flyTo([it.lat, it.lon], z, { duration: 1.4 });
  if (it.marker) map.once('moveend', () => it.marker.openPopup());
}
document.querySelectorAll('#chips [data-f]').forEach(b => b.onclick = () => {
  filt = b.dataset.f; document.querySelectorAll('#chips [data-f]').forEach(x => x.classList.toggle('on', x === b)); renderFeed(); });
document.querySelectorAll('#chips [data-s]').forEach(b => b.onclick = () => {
  sortBy = b.dataset.s; document.querySelectorAll('#chips [data-s]').forEach(x => x.classList.toggle('on', x === b)); renderFeed(); });

// ---------- time range under the map: two handles (start, end), play moves the window ----------
let playT = null;
const isoOf = n => new Date(n * 864e5).toISOString().slice(0, 10);
function setupSlider() {
  const lo = $('tlo'), hi = $('thi');
  const d0 = Math.min(dnum(D0), ...ITEMS.map(it => dnum(it.date)).filter(isFinite));   // range follows the data
  const n = Math.round(dnum(TODAY) - d0);
  [lo, hi].forEach(x => x.max = n);
  if (tEnd) { lo.value = dnum(tStart) - d0; hi.value = dnum(tEnd) - d0; } else { lo.value = 0; hi.value = n; }
  // event density above the track, so you can see where things happened
  const c = $('thist'), g = c.getContext('2d'), W = c.clientWidth || 300, H = 12;
  c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio);
  const bins = new Array(Math.max(1, Math.round(W / 4))).fill(0);
  ITEMS.forEach(it => { const k = Math.floor((dnum(it.date) - d0) / (n + 1) * bins.length); if (k >= 0 && k < bins.length) bins[k]++; });
  const mx = Math.max(1, ...bins); g.fillStyle = '#8b95a3';
  bins.forEach((v, i) => v && g.fillRect(i * W / bins.length, H - Math.max(2, v / mx * H), W / bins.length - 1, Math.max(2, v / mx * H)));
  const show = () => {
    let a = +lo.value, b = +hi.value;
    if (a > b) { if (document.activeElement === lo) lo.value = a = b; else hi.value = b = a; }
    const all = a === 0 && b === n && !playT;
    tStart = all ? null : isoOf(d0 + a); tEnd = all ? null : isoOf(d0 + b);
    $('tfill').style.left = `calc(7px + ${a / n} * (100% - 14px))`;
    $('tfill').style.width = `calc(${(b - a) / n} * (100% - 14px))`;
    lo.style.zIndex = a > n - 2 ? 3 : 2;                 // keep the start handle grabbable at the far right
    renderFeed();
    const k = ITEMS.filter(visible).length;
    $('tlabel').textContent = `${fmtDate(isoOf(d0 + a))} → ${b === n ? 'today' : fmtDate(isoOf(d0 + b))} · ${b - a + 1} d · ${k} item${k === 1 ? '' : 's'}`;
  };
  lo.oninput = hi.oninput = show;
  $('tplay').onclick = () => {
    if (playT) { clearInterval(playT); playT = null; $('tplay').textContent = '▶'; show(); return; }
    let w = +hi.value - +lo.value; if (w >= n - 1) w = 30;      // whole range selected: play a 30-day window
    if (+hi.value >= n || +lo.value + w > n) { lo.value = 0; hi.value = w; }
    $('tplay').textContent = '❚❚';
    playT = setInterval(() => {
      const step = Math.min(3, n - +hi.value); lo.value = +lo.value + step; hi.value = +hi.value + step; show();
      if (+hi.value >= n) $('tplay').click();
    }, 350);
    show();
  };
  $('tall').onclick = () => { if (playT) $('tplay').click(); lo.value = 0; hi.value = n; show(); };
  show();
}
addEventListener('resize', () => ITEMS.length && setupSlider());
function loadSites() { loadAll(); }        // kept for the analyze flow
loadAll();

// ---------- server detection ----------
async function detectServer() {
  if (API === null || API === undefined) return false;
  try {
    const ctl = new AbortController(); setTimeout(() => ctl.abort(), 2500);
    return (await fetch(API + '/api/health', { signal: ctl.signal })).ok;
  } catch (e) { return false; }
}

// ---------- draw a box ----------
let bbox = null, rect = null, drawing = false, start = null, pollT = null;
$('draw').onclick = () => { drawing = true; document.body.classList.add('drawing'); map.dragging.disable(); $('sel').textContent = 'Click and drag on the map…'; };
map.on('mousedown', e => { if (!drawing) return; start = e.latlng; if (rect) map.removeLayer(rect); rect = L.rectangle([start, start], { color: '#2f81f7', weight: 2, fillOpacity: .08 }).addTo(map); });
map.on('mousemove', e => { if (drawing && start) rect.setBounds(L.latLngBounds(start, e.latlng)); });
map.on('mouseup', e => {
  if (!drawing || !start) return;
  drawing = false; document.body.classList.remove('drawing'); map.dragging.enable();
  const b = L.latLngBounds(start, e.latlng); start = null; setBox(b);
});
function setBox(b) {
  const w = b.getWest(), s = b.getSouth(), e = b.getEast(), n = b.getNorth();
  bbox = [w, s, e, n].map(v => +v.toFixed(4));
  if (rect) map.removeLayer(rect); rect = L.rectangle(b, { color: '#2f81f7', weight: 2, fillOpacity: .08 }).addTo(map);
  const dx = e - w, dy = n - s, ok = dx <= 1.5 && dy <= 1.5 && dx >= .03 && dy >= .03;
  $('sel').innerHTML = `${bbox.join(', ')}<br>≈ ${(dx * 111 * Math.cos((n + s) / 2 * Math.PI / 180)).toFixed(0)} × ${(dy * 111).toFixed(0)} km `
    + (ok ? '<span class="ok">✓</span>' : '<span class="bad">size must be 0.03°–1.5° per side</span>');
  $('check').disabled = !ok; $('go').disabled = true; $('cov').textContent = ''; covLayer.clearLayers();
}
$('goto').onkeydown = e => {
  if (e.key !== 'Enter') return;
  const m = e.target.value.match(/(-?\d+(\.\d+)?)\s*[, ]\s*(-?\d+(\.\d+)?)/);
  if (m) map.setView([+m[1], +m[3]], 9);
};

// ---------- coverage: every NISAR footprint touching the box; if none covers all of it, the best-effort parts ----------
$('check').onclick = async () => {
  $('cov').textContent = 'Asking the ASF archive…'; covLayer.clearLayers(); $('check').disabled = true;
  try {
    const r = await fetch(API + '/api/coverage?bbox=' + bbox.join(',')); const j = await r.json();
    if (!r.ok) throw new Error(j.detail || r.status);
    const st = j.stacks || [], parts = j.parts || [];
    st.slice(0, 8).forEach((s, i) => L.geoJSON(s.footprint, { interactive: false,
      style: { color: s.usable ? '#ff7828' : '#8b95a3', weight: s.usable ? 2 : 1, fillOpacity: .05, dashArray: s.usable ? null : '4' } }).addTo(covLayer));
    parts.forEach((p, i) => L.rectangle([[p.bbox[1], p.bbox[0]], [p.bbox[3], p.bbox[2]]], { interactive: false, color: '#3fb950', weight: 2, fillOpacity: .12 })
      .bindTooltip(`part ${i + 1}`, { permanent: true, direction: 'center', className: 'ptip' }).addTo(covLayer));
    const usable = st.filter(s => s.usable);
    if (j.full) $('cov').innerHTML = `<span class="ok">Full coverage.</span> Track ${usable[0].track} ${usable[0].direction}, ${usable[0].n_dates} passes, ${fmtDate(usable[0].first)} → ${fmtDate(usable[0].last)}.`;
    else if (parts.length) $('cov').innerHTML = `<span class="bad">No single NISAR frame covers all of it.</span> Best effort: <b>${parts.length} part${parts.length > 1 ? 's' : ''}</b> (green) = `
      + `<b>${Math.round(100 * parts.reduce((a, p) => a + p.coverage, 0))}%</b> of the box, `
      + parts.map((p, i) => `${i + 1}: ${p.n_dates} passes`).join(', ') + '.';
    else $('cov').innerHTML = `<span class="bad">No NISAR stack with 4+ passes here yet.</span>` + (st.length ? ' Grey = partial frames.' : '');
    $('cov').innerHTML += st.length ? '<div class="sub">Orange = frames covering the whole box, grey dashed = partial frames.</div>' : '';
    $('go').disabled = !(j.full || parts.length);
  } catch (e) { $('cov').innerHTML = `<span class="bad">${e.message}</span>`; }
  finally { $('check').disabled = false; }
};

// ---------- analyze a disaster straight from the feed / its popup ----------
// NISAR-covered events start right away (box from `unseen events`); others (cyclones, no full stack) get a 1° box
// around the point and a coverage check, so you can adjust the box first.
let pending = null;                                     // event context for the next analysis
const anLink = it => window.UNSEEN_LIVE && it.e && !it.site ? ` · <a href="#" data-an="${it.e.id}"><b>Analyze</b></a>` : '';
document.addEventListener('click', ev => {
  const a = ev.target.closest('[data-an]'); if (!a) return;
  ev.preventDefault(); ev.stopPropagation();
  const it = ITEMS.find(x => x.e && x.e.id === a.dataset.an); if (it) analyzeEvent(it);
});
function analyzeEvent(it) {
  const e = it.e, n = e.nisar || {}, name = `${it.title} ${e.date.slice(0, 7)}`;
  const b = n.status === 'ok' && n.bbox ? L.latLngBounds([[n.bbox[1], n.bbox[0]], [n.bbox[3], n.bbox[2]]])
    : L.latLngBounds([[e.lat - .5, e.lon - .5], [e.lat + .5, e.lon + .5]]);
  map.closePopup(); setBox(b); map.flyToBounds(b, { padding: [60, 60], duration: 1 });
  pending = { event_date: e.date, kind: `${(EVT[e.type] || e.type).toLowerCase()} (GDACS ${e.alert})` };
  $('name').value = name;
  if (n.status === 'ok') startJob(name);
  else {                                                  // no ready box: check coverage, then do the best possible
    jobToast(`${it.title}: checking NISAR coverage…`);
    $('check').onclick().then(() => { if (!$('go').disabled) startJob(name);
      else jobToast(`${it.title}: no NISAR passes here yet. Move the box over land, then Check.`); });
  }
}
function jobToast(html) {
  let t = $('jobtoast'); if (!t) { t = document.createElement('div'); t.id = 'jobtoast'; $('leftcol').appendChild(t); }
  t.innerHTML = html; t.hidden = !html;
}

// ---------- analyze + poll ----------
$('go').onclick = () => startJob($('name').value.trim() || `Area ${bbox.map(v => v.toFixed(2)).join(',')}`);
async function startJob(name) {
  $('go').disabled = true;
  const r = await fetch(API + '/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ bbox, name, ...(pending || {}) }) });
  const j = await r.json(); pending = null;
  if (!r.ok) { $('job').innerHTML = `<span class="bad">${j.detail}</span>`; jobToast(`<span class="bad">${j.detail}</span>`); $('go').disabled = false; return; }
  MINE.add(j.id); refreshJobs();
}
// ---------- job queue: every analysis (+ background feed / watch) with its state; stop queued or running ones ----------
const MINE = new Set(), DONE = new Set(); let jobsT = null, jobsOpen = true;
const ST = { queued: '🕒', running: '⏳', done: '✓', error: '⚠', cancelled: '⏹' };
function poll() { refreshJobs(); }
async function refreshJobs() {
  clearTimeout(jobsT);
  if (!window.UNSEEN_LIVE) return;
  let J = [];
  try { J = await (await fetch(API + '/api/jobs')).json(); } catch (e) { jobsT = setTimeout(refreshJobs, 15000); return; }
  const user = J.filter(j => j.kind !== 'background'), active = user.filter(j => j.state === 'queued' || j.state === 'running');
  RUNNING_NAMES = new Set(active.map(j => j.name));
  let box = $('jobs'); if (!box) { box = document.createElement('div'); box.id = 'jobs'; $('leftcol').appendChild(box); L.DomEvent.disableClickPropagation(box); L.DomEvent.disableScrollPropagation(box); }
  box.hidden = !J.length;
  box.innerHTML = `<div class="jh" title="Show / hide"><b>Jobs</b> <span class="sub">${active.length ? `${active.length} active` : 'idle'}</span><span style="margin-left:auto">${jobsOpen ? '▾' : '▸'}</span></div>`
    + (jobsOpen ? J.slice(0, 12).map(j => {
      const pct = Math.round(100 * (j.progress || 0)), bg = j.kind === 'background', can = !bg && (j.state === 'queued' || j.state === 'running') && !j.cancel;
      return `<div class="jr ${j.state}"><span class="js">${ST[j.state] || '•'}</span><div class="jb"><div class="jn">${j.name}</div>`
        + `<div class="sub">${j.message || j.state}${j.state === 'running' && !bg ? ` · ${pct}%` : ''}</div>`
        + (j.state === 'running' && !bg ? `<div class="bar"><div style="width:${pct}%"></div></div>` : '') + `</div>`
        + (can ? `<button data-stop="${j.id}" title="${j.state === 'queued' ? 'Remove from queue' : 'Stop'}">✕</button>` : '')
        + (j.state === 'done' && j.site ? `<a href="#site=${encodeURIComponent(j.site)}">open</a>` : '')
        + (!bg && (j.state === 'error' || j.state === 'cancelled') ? `<button data-retry="${j.id}" title="Run again">↻</button>` : '') + `</div>`;
    }).join('') : '');
  box.querySelector('.jh').onclick = () => { jobsOpen = !jobsOpen; refreshJobs(); };
  box.querySelectorAll('[data-retry]').forEach(b => b.onclick = async () => {
    const j = J.find(x => x.id === b.dataset.retry); if (!j) return; b.disabled = true;
    const r = await fetch(API + '/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bbox: j.bbox, name: j.name, event_date: j.event_date, kind: j.kind }) });
    if (r.ok) MINE.add((await r.json()).id); refreshJobs(); });
  box.querySelectorAll('[data-stop]').forEach(b => b.onclick = async () => { b.disabled = true; await fetch(API + `/api/jobs/${b.dataset.stop}/cancel`, { method: 'POST' }); refreshJobs(); });
  // side panel line for my latest job
  const mine = user.find(j => MINE.has(j.id));
  if (mine) { $('job').innerHTML = `<b>${mine.name}</b>: ${mine.message || mine.state}`; $('prog').style.width = Math.round(100 * (mine.progress || 0)) + '%'; }
  // newly finished: pull them into the feed; open the ones started here
  const fresh = user.filter(j => j.state === 'done' && !DONE.has(j.id));
  const first = !DONE.size && !MINE.size;
  fresh.forEach(j => DONE.add(j.id));
  if (fresh.length && !first) {
    await loadAll();
    const m = fresh.find(j => MINE.has(j.id));
    if (m) { if (rect) { map.removeLayer(rect); rect = null; } covLayer.clearLayers(); window.openSite(m.site); }
  }
  jobsT = setTimeout(refreshJobs, active.length || J.some(j => j.state === 'running') ? 2000 : 15000);
}

(async () => {
  loadSites();
  const live = await detectServer();
  window.UNSEEN_LIVE = live; window.dispatchEvent(new Event('unseen:live')); if (live) renderFeed();
  $('mode').textContent = live ? 'live: analyze anywhere' : 'gallery mode';
  $('analyze').style.display = live ? '' : 'none';
  $('static').style.display = live ? 'none' : '';
  if (live) refreshJobs();
})();
