// In-map analysis: open an analysed area ON the globe (no page change), so scale and context stay.
// A floating panel steps through NISAR passes; the radar / optical photo and the change overlay are draped on the map.
// Deep link: index.html#site=<id>. The full page (site.html) is still there for swipe and pixel history.
(() => {
const $ = id => document.getElementById(id), map = window.UNSEEN_MAP;
map.createPane('analysis').style.zIndex = 350;                 // above map tiles (200), below markers/popups
const fmt = (d, o = { day: 'numeric', month: 'short' }) => new Date(d + 'T00:00:00Z').toLocaleDateString('en-GB', { ...o, timeZone: 'UTC' });
const dn = d => Date.parse(d + 'T00:00:00Z') / 864e5;
let S = null, timer = null;

const panel = document.createElement('div');
panel.id = 'sp'; panel.hidden = true;
panel.innerHTML = `
  <div class="sph"><b id="spT"></b><button id="spX" title="Close (Esc)">✕</button></div>
  <div class="sub" id="spI"></div>
  <div class="sprow"><button id="spP" title="Play through passes">▶</button><input id="spR" type="range" min="0" value="0"><span id="spD"></span></div>
  <div class="spseg" id="spB">
    <button data-b="none" title="Satellite map only">Map</button>
    <button data-b="photo" title="Nearest true-colour optical photo (Landsat / Sentinel-2)">Photo</button>
    <button data-b="nisar" class="on" title="NISAR L-band radar (sees through clouds)">Radar</button>
  </div>
  <div class="sprow sub"><span>image</span><input id="spA" type="range" min="0" max="100" value="85" style="width:80px" title="Image opacity: fade to the map below"></div>
  <div id="spO" class="spchk sub"></div>
  <div class="legend sub" id="spL"></div>
  <canvas id="spC" height="60" title="New water per pass (orange = under cloud that day). Click a bar to jump."></canvas>
  <details class="more2" id="spHd"><summary>Numbers</summary><div id="spH" class="sph2"></div></details>
  <details class="more2" id="spM"><summary>How we measured this</summary><div class="sub" id="spMt"></div></details>
  <div class="sub" id="spN"></div>
  <a id="spF" class="sub" target="_self">Full analysis: swipe, pixel history ↗</a>`;
$('leftcol').appendChild(panel);
L.DomEvent.disableClickPropagation(panel); L.DomEvent.disableScrollPropagation(panel);

async function openSite(id) {
  closeSite(true);
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
        box: L.rectangle(B, { pane: 'analysis', color: '#ff7828', weight: 1.5, fill: false, interactive: false }).addTo(map) };
  const N = D.frames.length, cal = D.calibration && D.calibration.used ? D.calibration : null;
  const f1 = cal ? cal.loo.map(x => x.f1) : (D.validation || []).map(x => x.f1);
  $('spT').textContent = D.title;
  $('spI').innerHTML = `${D.kind || ''}<br>${N} NISAR passes · ${fmt(D.frames[0].date)} → ${fmt(D.frames[N - 1].date)}`
    + (D.event_date ? ` · event ${fmt(D.event_date)}` : '');
  const R = D.report || {};
  $('spH').innerHTML = (R.headline || []).map(h => `<div class="hk${h.strong ? ' strong' : ''}" title="${(h.note || '').replace(/"/g, '&quot;')}">`
    + `<b>${typeof h.value === 'number' ? h.value.toLocaleString() : h.value}<small> ${h.unit || ''}</small></b><span>${h.label}</span>`
    + (h.note ? `<i>${h.note}</i>` : '') + `</div>`).join('') || '<div class="sub">Re-run this area to get its report.</div>';
  S.layers = (R.layers || []).map(l => ({ ...l, ov: L.imageOverlay(A(l.file), L.latLngBounds([[l.corners[1][1], l.corners[0][0]], [l.corners[0][1], l.corners[1][0]]]),
    { pane: 'analysis', interactive: false, opacity: 0 }).addTo(map) }));
  S.P = R.pairs && R.pairs.list && R.pairs.list.length ? R.pairs : null;
  if (S.P) {
    const pb = S.P.corners, PB = L.latLngBounds([[pb[1][1], pb[0][0]], [pb[0][1], pb[1][0]]]), o = { pane: 'analysis', interactive: false, opacity: 0 };
    S.mo = L.imageOverlay(A(S.P.list[0].motion), PB, o).addTo(map); S.fr = L.imageOverlay(A(S.P.list[0].fringes), PB, o).addTo(map);
  }
  $('spO').innerHTML = (S.P ? '<label><input type="checkbox" value="motion">Ground motion (cm)</label><label><input type="checkbox" value="fringes">Fringes</label>' : '')
    + S.layers.map((l, i) => `<label><input type="checkbox" value="L${i}">${l.label}</label>`).join('')
    + '<label><input type="checkbox" value="pass">Seen only by NISAR (this pass)</label>';
  $('spO').querySelectorAll('input').forEach(x => x.onchange = render);
  setOn([S.P ? 'motion' : S.layers.length ? 'L0' : 'pass']);
  if (S.P && D.event_date) { const k = D.frames.findIndex(f => f.date >= D.event_date); if (k >= 0) S.t = k; }
  if (S.P) { S.b = 'none'; } else if (!(R.volcano && R.volcano.vent)) S.b = 'nisar';
  $('spB').querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.b === S.b));
  $('spC').style.display = R.hazard === 'flood' || !R.hazard || R.hazard === 'volcano' ? '' : 'none';
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
  $('spM').hidden = !(R.notes || R.insar);
  $('spMt').innerHTML = (R.notes || []).map(n => `• ${n}`).join('<br>')
    + (R.insar ? `<br>• InSAR pairs: pre ${R.insar.pre.join(' → ')}, across event ${R.insar.co.join(' → ')} (track ${R.insar.track} ${R.insar.direction}).` : '');
  $('spR').max = N - 1; $('spR').value = S.t;
  $('spF').href = `site.html?id=${encodeURIComponent(id)}`;
  panel.hidden = false;
  map.flyToBounds(B, { paddingTopLeft: [panel.offsetWidth + 70, 30], paddingBottomRight: [30, 30], duration: 1.2 });
  render();
}

function setOn(keys) { $('spO').querySelectorAll('input').forEach(x => x.checked = keys.includes(x.value)); }
function closeSite(keepHash) {
  if (timer) togglePlay();
  if (S) { ['base', 'over', 'box', 'mo', 'fr'].forEach(k => S[k] && map.removeLayer(S[k])); (S.layers || []).forEach(l => map.removeLayer(l.ov)); (S.extra || []).forEach(x => map.removeLayer(x)); }
  S = null; panel.hidden = true;
  if (!keepHash && location.hash.startsWith('#site=')) history.replaceState(null, '', location.pathname + location.search);
}

function render() {
  if (!S) return;
  const { D, A, t } = S, f = D.frames[t], s = D.summary[t];
  $('spD').textContent = `${fmt(f.date, { day: 'numeric', month: 'short', year: 'numeric' })} · ${t + 1}/${D.frames.length}`;
  let note = '';
  if (S.b === 'photo') {
    const p = S.photos.length ? S.photos.reduce((a, b) => Math.abs(dn(b[0]) - dn(f.date)) < Math.abs(dn(a[0]) - dn(f.date)) ? b : a) : null;
    if (p) { S.base.setUrl(A(p[1])); const g = Math.round(dn(p[0]) - dn(f.date));
             note = `Photo ${fmt(p[0])}${g ? ` (${g > 0 ? '+' : ''}${g} d from this pass)` : ' (same day)'}. Clouds look white: that's what NISAR sees through.`; }
    else note = 'No optical photo for this area.';
  } else if (S.b === 'nisar') { S.base.setUrl(A(f.nisar)); note = 'Radar colours: R = HH, G = HV, B = HH/HV. Dark = smooth water.'; }
  S.base.setOpacity(S.b === 'none' ? 0 : $('spA').value / 100);
  const on = new Set([...$('spO').querySelectorAll('input:checked')].map(x => x.value));
  S.over.setUrl(A(f.hidden)); S.over.setOpacity(on.has('pass') ? 1 : 0);
  (S.layers || []).forEach((l, i) => l.ov.setOpacity(on.has(`L${i}`) ? 1 : 0));
  let pr = null;
  if (S.P) {                                                       // the 12-day pair for this date (contains it, else nearest)
    const Ls = S.P.list, x = dn(f.date);
    pr = Ls.find(q => dn(q.ref) < x && x <= dn(q.sec)) || Ls.reduce((a, b) => Math.abs(dn(b.sec) - x) < Math.abs(dn(a.sec) - x) ? b : a);
    S.mo.setUrl(A(pr.motion)); S.fr.setUrl(A(pr.fringes));
    S.mo.setOpacity(on.has('motion') ? 1 : 0); S.fr.setOpacity(on.has('fringes') ? 1 : 0);
  }
  const seen = new Set();                                         // one legend per distinct scale
  $('spL').innerHTML = (pr && (on.has('motion') || on.has('fringes')) ? `<div class="pair${pr.event ? ' ev' : ''}">Pair ${fmt(pr.ref)} → ${fmt(pr.sec)}${pr.event ? ' · spans the event' : ''}</div>` : '')
    + [...(on.has('motion') && S.P ? [S.P.motion_legend] : []), ...(on.has('fringes') && S.P ? [S.P.fringe_legend] : [])]
      .map(lg => lg.map(([c, t]) => `<div><span style="background:${c}${c.startsWith('linear') ? ';width:60px' : ''}"></span>${t}</div>`).join('')).join('')
    + (S.layers || []).filter((l, i) => on.has(`L${i}`)).map(l => l.legend.map(([c, t]) => `<div><span style="background:${c}${c.startsWith('linear') ? ';width:60px' : ''}"></span>${t}</div>`).join(''))
    .filter(h => !seen.has(h) && seen.add(h)).join('')
    + (on.has('pass') ? '<div><span style="background:var(--blue)"></span>water, seen by both</div><div><span style="background:var(--orange)"></span>water, only radar (clouds)</div>'
      + '<div><span style="background:var(--green)"></span>water under trees</div><div><span style="background:var(--purple)"></span>surface change</div>' : '');
  $('spN').textContent = note;
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
function chart() {
  if (S.D.report && S.D.report.hazard === 'volcano') return vchart();
  const c = $('spC'), g = c.getContext('2d'), W = c.clientWidth, H = 70, { D, t } = S, n = D.frames.length;
  c.width = W * devicePixelRatio; c.height = H * devicePixelRatio; g.scale(devicePixelRatio, devicePixelRatio); g.clearRect(0, 0, W, H);
  const v = D.summary.map(S.nw), h = D.summary.map(S.hid), mx = Math.max(1, ...v), bw = W / n;
  v.forEach((x, i) => {
    const y = (H - 12) * x / mx, yh = (H - 12) * Math.min(h[i], x) / mx;
    g.globalAlpha = i === t ? 1 : 0.55;
    g.fillStyle = '#2b8cbe'; g.fillRect(i * bw + 1, H - 12 - y, bw - 2, y - yh);
    g.fillStyle = '#ff7828'; g.fillRect(i * bw + 1, H - 12 - yh, bw - 2, yh);
  });
  g.globalAlpha = 1; g.strokeStyle = '#fff'; g.strokeRect(t * bw + 0.5, 0.5, bw - 1, H - 12);
  g.fillStyle = '#8b95a3'; g.font = '10px system-ui'; g.fillText(fmt(D.frames[0].date), 2, H - 1);
  const last = fmt(D.frames[n - 1].date); g.fillText(last, W - g.measureText(last).width - 2, H - 1);
  if (D.event_date) {                                  // event marker on the pass axis
    const d0 = dn(D.frames[0].date), d1 = dn(D.frames[n - 1].date), x = bw / 2 + (W - bw) * (dn(D.event_date) - d0) / Math.max(1, d1 - d0);
    if (x >= 0 && x <= W) { g.strokeStyle = '#f85149'; g.setLineDash([3, 3]); g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H - 12); g.stroke(); g.setLineDash([]); }
  }
}
$('spC').onclick = ev => { if (!S) return; const r = $('spC').getBoundingClientRect(); setT(Math.floor((ev.clientX - r.left) / r.width * S.D.frames.length)); };

function setT(i) { if (!S) return; S.t = Math.max(0, Math.min(S.D.frames.length - 1, i)); $('spR').value = S.t; render(); }
function togglePlay() {
  if (timer) { clearInterval(timer); timer = null; $('spP').textContent = '▶'; return; }
  if (!S) return;
  if (S.t >= S.D.frames.length - 1) setT(0);
  $('spP').textContent = '❚❚';
  timer = setInterval(() => { if (!S || S.t >= S.D.frames.length - 1) return togglePlay(); setT(S.t + 1); }, 900);
}
$('spR').oninput = () => setT(+$('spR').value);
$('spP').onclick = togglePlay;
$('spO').onchange = $('spA').oninput = render;
$('spX').onclick = () => closeSite(false);
$('spB').onclick = ev => { const b = ev.target.dataset.b; if (!b || !S) return; S.b = b;
  $('spB').querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.b === b)); render(); };
addEventListener('keydown', ev => {
  if (!S || /INPUT|TEXTAREA/.test(document.activeElement?.tagName) && document.activeElement.type !== 'range') return;
  if (ev.key === 'Escape') closeSite(false);
  else if (ev.key === 'ArrowRight') setT(S.t + 1);
  else if (ev.key === 'ArrowLeft') setT(S.t - 1);
  else if (ev.key.toLowerCase() === 't') $('spB').querySelector(`[data-b="${S.b === 'nisar' ? 'photo' : 'nisar'}"]`).click();
});
const fromHash = () => { const m = location.hash.match(/^#site=(.+)$/); m ? openSite(decodeURIComponent(m[1])) : closeSite(true); };
addEventListener('hashchange', fromHash);
window.openSite = id => { location.hash = 'site=' + encodeURIComponent(id); };
fromHash();
})();
