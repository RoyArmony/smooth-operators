# 11 · Design

One look for every page. Tokens live in `site/css/design.css`; load it first on every page, then the page's own CSS.
Use the tokens (`var(--…)`), not raw values.

## Type

**Inter** (Google Fonts, weights 400–800) for everything. Numbers use `font-variant-numeric: tabular-nums`.

| Token | Size | Use |
|---|---|---|
| `--fs-xs` | 12 px | captions, eyebrows (uppercase, `.12em` tracking, 600) |
| `--fs-sm` | 13 px | secondary text, buttons |
| `--fs-md` | 14 px | body (line height 1.5) |
| `--fs-lg` | 16 px | lead text, brand |
| `--fs-xl` | 20 px | card titles |
| `--fs-2xl` | 24 px | page / panel titles (700, `-.01em`) |
| `--fs-3xl` | 32 px | big numbers (800) |
| `--fs-display` | 40–84 px | film headlines |

## Colour (dark only)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#070a0f` | page |
| `--surface` / `-2` / `-3` | `#0f141b` / `#161c25` / `#1e2531` | cards, buttons, hover |
| `--line` / `-2` | `#242c38` / `#333d4b` | borders |
| `--text` / `--muted` / `--faint` | `#e8ecf1` / `#9aa4b2` / `#6b7480` | text levels |
| `--accent` | `#ff9a2e` | brand orange: primary actions, key numbers, selected |
| `--water` | `#4aa3ff` | water, links in dialogs |
| `--danger` / `--ok` | `#f85149` / `#3fb950` | alerts / checks |

Map layer colours (NISAR water, cloud-hidden, etc.) stay as each layer's legend defines them.

## Space and shape

- Spacing on a 4 px grid: `--s1`…`--s6` = 4, 8, 12, 16, 24, 32 px.
- Radius: `--r-sm` 6 (inputs), `--r-md` 10 (cards), `--r-lg` 14 (dialogs), `--r-pill` (chips, main buttons).
- One shadow: `--shadow`. Easing: `--ease`.

## Layout

- **Top bar** on every page (`site/js/topbar.js`, height `--bar-h` = 56 px, 52 on phones): brand · Home · Story · Explorer · About ▾ · NISAR chip · GitHub.
  Pages pad their top by `--bar-h`. Mark the page with `<body data-page="home|story|explorer">`.
- **About** opens a dialog over the page (the user stays in place).
- Visitor path: **Home** = welcome page (`site/home.html`) → **Story** = the film (`site/landing.html`) → **Explorer** = the map (`site/viewer/index.html`): map left, 380 px sidebar right.
- Explorer sidebar: list of events → click one → only that event's card + "← All events".
- Phones (< 760 px): Explorer stacks map over sidebar.

## Drawbacks

- Fonts load from Google Fonts; offline the site falls back to system fonts.
- The film (`landing.html`) still has many hand-set sizes for its animation; only its base font and colours use the tokens.
