// Shared top bar for every page: brand, Home / Explorer, About menu (info dialogs), repo link.
// Use: <link rel="stylesheet" href="…/css/design.css"> + <script src="…/js/topbar.js" defer></script>, and <body data-page="home|story|explorer">.
(() => {
  const root = new URL('..', document.currentScript.src);          // the site/ folder, wherever this page lives
  const u = p => new URL(p, root).href;
  const page = document.body.dataset.page || '';
  const REPO = 'https://github.com/RoyArmony/smooth-operators';

  const INFO = {
    project: { k: 'The Project', t: 'Floods the official map leaves blank', b: `
      <p>NASA Space Apps Challenge 2026 · <b>Dancing with the SARs</b>.<br>By team <b>Smooth Operators</b> from Haifa, Israel.</p>
      <p>Flood maps from optical and C-band radar satellites leave gaps: cloud, forest canopy and cities hide the water.
      <b>NISAR's L-band radar</b> sees through them.</p>
      <p>Unseen Earth shows, flood by flood, the water NISAR finds where the official map says <b>"cannot see"</b>.</p>` },
    method: { k: 'How It Works', t: 'Problem → NASA data → method → result', b: `
      <ul>
        <li><b>Data:</b> NISAR L2 GCOV radar passes (every 12 days), Copernicus Global Flood Monitoring (GFM), optical photos.</li>
        <li><b>Detect:</b> open water is dark to radar; flooded forest is bright (double bounce).</li>
        <li><b>Compare:</b> NISAR water inside the area GFM excludes = water the official map misses.</li>
        <li><b>Check:</b> against Canada's RADARSAT Constellation Mission (CSA) and the GFM flood map.</li>
      </ul>
      <p>Areas are lower bounds: NISAR products are still provisional.</p>` },
    data: { k: 'Data & Credits', t: 'Built on open data', b: `
      <ul>
        <li>NISAR L2 GCOV: NASA/ISRO, via ASF DAAC</li>
        <li>OPERA DSWx: NASA JPL</li>
        <li>Copernicus GFM: European Commission</li>
        <li>RADARSAT Constellation Mission, RADARSAT-1: Canadian Space Agency</li>
        <li>Basemap: Esri World Imagery · NASA Blue Marble · Sentinel-2 cloudless (EOX)</li>
        <li>Map: Leaflet · Font: Inter</li>
      </ul>
      <p>Full list and licences: <a href="${REPO}/blob/main/ACKNOWLEDGMENTS.md" target="_blank" rel="noopener">ACKNOWLEDGMENTS.md ↗</a></p>` },
    team: { k: 'Team', t: 'Smooth Operators', b: `
      <p><b>Roy</b> · <b>Shai</b> · <b>Noa</b></p>
      <p>NASA Space Apps Challenge 2026, Haifa (Technion).</p>
      <p>Code: <a href="${REPO}" target="_blank" rel="noopener">GitHub ↗</a> · made with help from Claude Code (AI).</p>` },
  };

  const bar = document.createElement('header');
  bar.className = 'ue-bar';
  bar.innerHTML = `
    <a class="ue-brand" href="${u('home.html')}"><img src="${u('favicon.svg')}" alt=""><span>Unseen Earth</span></a>
    <nav class="ue-nav">
      <a href="${u('home.html')}" class="${page === 'home' ? 'on' : ''}">Home</a>
      <a href="${u('landing.html')}" class="${page === 'story' ? 'on' : ''}">Story</a>
      <a href="${u('viewer/index.html')}" class="${page === 'explorer' ? 'on' : ''}">Explorer</a>
      <div class="ue-menu"><button type="button" aria-haspopup="true" aria-expanded="false">About</button>
        <div class="ue-drop" role="menu">
          <button data-i="project">The Project<small>What and why</small></button>
          <button data-i="method">How It Works<small>Data, method, checks</small></button>
          <button data-i="data">Data &amp; Credits<small>Sources and licences</small></button>
          <button data-i="team">Team<small>Smooth Operators</small></button>
        </div></div>
    </nav>
    <div class="ue-right">
      <span class="ue-chip"><b>NISAR</b> · L-band radar</span>
      <a class="ue-cta" href="${REPO}" target="_blank" rel="noopener">GitHub ↗</a>
    </div>`;
  document.body.prepend(bar);

  const modal = document.createElement('div');
  modal.className = 'ue-modal';
  modal.innerHTML = '<div class="ue-card" role="dialog" aria-modal="true"></div>';
  document.body.appendChild(modal);
  const card = modal.firstChild;

  const menu = bar.querySelector('.ue-menu'), mbtn = menu.querySelector('button');
  const setMenu = on => { menu.classList.toggle('open', on); mbtn.setAttribute('aria-expanded', on); };
  mbtn.onclick = e => { e.stopPropagation(); setMenu(!menu.classList.contains('open')); };
  document.addEventListener('click', () => setMenu(false));
  menu.querySelectorAll('[data-i]').forEach(b => b.onclick = () => {
    const x = INFO[b.dataset.i];
    card.innerHTML = `<button class="x" aria-label="Close">×</button><div class="k">${x.k}</div><h2>${x.t}</h2>${x.b}`;
    card.querySelector('.x').onclick = close;
    setMenu(false); modal.classList.add('open');
  });
  const close = () => modal.classList.remove('open');
  modal.onclick = e => { if (e.target === modal) close(); };
  addEventListener('keydown', e => { if (e.key === 'Escape' && modal.classList.contains('open')) { e.stopImmediatePropagation(); close(); } }, true);
})();
