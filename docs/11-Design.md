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

## Colour: "Deep water" (dark only)

| Token | Value | Use |
|---|---|---|
| `--bg` | `#06141b` | page |
| `--surface` / `-2` / `-3` | `#0c222b` / `#112a34` / `#16323c` | cards, buttons, hover |
| `--line` / `-2` | `#1b3843` / `#23444f` | borders |
| `--text` / `--muted` / `--faint` | `#e6f1f2` / `#8fb0b8` / `#5f7f88` | text levels |
| `--accent` (+ `--accent-hi`, `--on-accent`) | `#2dd4bf` (`#5eead4`, `#04342c`) | aqua: buttons, active, key numbers |
| `--sand` | `#f4c27a` | rare highlight |
| `--water` | `#4aa3ff` | links in dialogs |
| `--danger` / `--ok` | `#f85149` / `#3fb950` | alerts / checks |

**Map data colours are not UI colours.** GFM flood blue `#2882ff`, the grey "cannot see" hatch and NISAR orange `#ff9a2e`
belong to the layers and their legends only. Don't use orange for buttons or headings, so NISAR's water stands out.

## Space and shape

- Spacing on a 4 px grid: `--s1`…`--s6` = 4, 8, 12, 16, 24, 32 px.
- Radius: `--r-sm` 6 (inputs), `--r-md` 10 (cards), `--r-lg` 14 (dialogs), `--r-pill` (chips, main buttons).
- One shadow: `--shadow`. Easing: `--ease`.

## Layout

- **Top bar** on every page (`site/js/topbar.js`, height `--bar-h` = 56 px, 52 on phones): brand · Home · Story · Explorer · About ▾ · Satellites in Use (comparison dialog) · GitHub.
  Pages pad their top by `--bar-h`. Mark the page with `<body data-page="home|story|explorer">`.
- **About** opens a dialog over the page (the user stays in place).
- Visitor path: **Home** = welcome page (`site/home.html`) → **Story** = the film (`site/landing.html`) → **Explorer** = the map (`site/viewer/index.html`): map left, 380 px sidebar right.
- Explorer sidebar: list of events → click one → only that event's card + "← All events".
- Phones (< 760 px): Explorer stacks map over sidebar.

## Drawbacks

- Fonts load from Google Fonts; offline the site falls back to system fonts.
- The film (`landing.html`) still has many hand-set sizes for its animation; only its base font and colours use the tokens.
