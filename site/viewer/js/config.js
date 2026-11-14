// Where the optional analysis server lives.
//  - ""                      same origin (when the page is served by server/app.py)
//  - "http://localhost:8000" a local server while the page is opened from GitHub Pages
//  - null                    gallery only (no draw-and-analyze), e.g. a public GitHub Pages deployment
window.UNSEEN_CONFIG = { apiBase: null };   // static site: gallery only
