# Paperhands — Style Guide

Transcribed from `docs/design/Paperhands.dc.html` (a Claude Design canvas
containing all four dashboard views plus a "Style guide" reference page).
Every value below is copied from that canvas's own `:root` block, type
scale, and glass/chrome CSS comments — not eyeballed from a screenshot.

## Color tokens

| Token | Value | Use |
|---|---|---|
| `--bg` | `#0a0d13` | app background |
| `--surface` | `#0f1319` | card fill |
| `--surface-raised` | `#141a22` | hover, nested cells |
| `--border` | `rgba(255,255,255,.07)` | 1px card edge |
| `--text` | `#eef2f7` | primary text |
| `--text-dim` | `#8e99a9` | secondary text |
| `--text-faint` | `#6f7a8a` | axis labels, captions |
| `--accent` | `#5fdfc0` | primary accent, active state (mint; canvas exposes this as a themeable prop — treat as fixed for the real app) |
| `--gain` | `#8ff0d9` | positive numbers |
| `--loss` | `#f4a89f` | negative numbers |
| `--warn` | `#e8b46a` | rejected, invalidation, "sample data" badge |
| `--sage` | `#8fb3a8` | Cohort B (screener) series/accent |
| (unnamed) | `#6b7686` (gray) | Cohort A (cash) series/accent |

Background also carries two very large, very soft radial glows (teal
`rgba(28,118,116,.50)`, violet `rgba(97,64,150,.45)`, both `filter: blur(60-70px)`,
fixed position, `z-index: 0`, slow drift animation) — decorative only, must
never reduce text contrast in front of them.

## Radius scale

| Token | Value | Use |
|---|---|---|
| `--r-card` | `20px` | hero, panels, tables |
| `--r-panel` | `16px` | nested cards, notes |
| `--r-field` | `14px` | list rows, code blocks |
| `--r-chip` | `9px` | contract chips |
| `--r-pill` | `999px` | buttons, tabs, search, badges |

## Spacing scale

| Token | Value | Use |
|---|---|---|
| `--s-1` | `4px` | icon gap |
| `--s-2` | `8px` | chip gap |
| `--s-3` | `12px` | inline groups |
| `--s-4` | `18px` | card gap |
| `--s-5` | `24px` | card padding, column gap |
| `--s-6` | `40px` | page gutter |
| `--s-7` | `72px` | page bottom padding |

## Type scale — Inter, tabular numerals right-aligned for all numbers

| Token | Size / weight / letter-spacing | Use |
|---|---|---|
| `--t-display` | 30px / 700 / -2% | hero price (e.g. ticker price on Today) |
| `--t-h1` | 22px / 700 / -1.5% | page title |
| `--t-h2` | 16px / 650 / 0 | card title |
| `--t-body` | 14px / 400 / 0, line-height 1.6 | prose (thesis text) |
| `--t-row` | 13px / 500 / 0 | table cells, chips |
| `--t-label` | 12px / 400 / 0 | secondary labels |
| `--t-micro` | 10.5px / 500 / +5%, uppercase | micro-labels ("CONFIDENCE", column headers) |

Fonts: `Inter` (400/500/600/700) for UI text, `JetBrains Mono` (400/500) for
anything numeric-tabular, code, timestamps, or pill badges that read like
data (`font-variant-numeric: tabular-nums` wherever a number can change).

## Liquid glass panel

Hero card and right rail only. Requires a dim glow behind it (see the two
radial glows above) — glass without a glow behind it looks flat.

```css
--glass-bg: linear-gradient(180deg, rgba(255,255,255,.075), rgba(255,255,255,.030));
--glass-blur: blur(26px) saturate(1.3);
--glass-border: 1px solid rgba(255,255,255,.10);
--glass-shadow: 0 24px 60px rgba(0,0,0,.45);
/* a 1px top edge highlight, inset 14px from each side */
--glass-edge: linear-gradient(90deg, transparent, rgba(255,255,255,.55), transparent);
```

Secondary panels (right-rail cards, scoreboard cards) use a slightly
lighter variant: `blur(24px) saturate(1.25)`, `box-shadow: 0 20px 50px rgba(0,0,0,.4)`,
same border and top-edge treatment.

Flat panels (agent reasoning panel, positions table, logs table) skip the
blur entirely: `background: rgba(255,255,255,.028); border: 1px solid rgba(255,255,255,.07)`,
no shadow, no top edge.

## Chrome accent

A decorative metallic-gradient accent used for icon marks only (the
wordmark icon, the "read-only" lock icon, the Cash/Screener/Agent
strategy-row icons).

```css
--chrome: linear-gradient(145deg, #ffffff 0%, #a2adbb 22%, #f4f7fb 40%, #6f7c8e 58%, #dfe6ee 78%, #8c97a6 100%);
--chrome-orb: radial-gradient(circle at 32% 26%, #ffffff, #d8e0ea 16%, #8e9aa9 44%, #4e5a6b 72%, #c4cedb 100%);
--chrome-gloss: inset 0 1px 1px rgba(255,255,255,.85);
--chrome-drop: 0 3px 12px rgba(0,0,0,.55);
```

Hard rules from the canvas: **max object size 34px, one per card, never
behind text.** It is a decorative gradient only — never a text or surface
background above 40px.

## Layout

- Max content width 1440px, min width 1100px, centered, `padding: 0 40px`
  (the `--s-6` page gutter).
- Top bar: 72px tall. Wordmark + search field (left), then a flexible
  spacer, then status pills (run status, next run time, "read-only" badge)
  right-aligned.
- Tabs: bottom-bordered, 26px gap between tabs, active tab gets a 2px
  bottom border in `--accent` and full-brightness text; inactive tabs are
  `--text-dim` with a transparent border.
- Today view: two-column grid, `minmax(0,1fr) 332px` — main column (hero
  card + agent reasoning panel) and a sticky right rail (watchlist, open
  positions summary, disclaimer note).
- Tables (Positions, Logs): header row in `--text-micro` uppercase style
  over `rgba(255,255,255,.025)`, data rows separated by
  `1px solid rgba(255,255,255,.055)`, row hover `rgba(255,255,255,.022)`.

## Non-negotiable honesty label

Every view that shows P&L must carry a visible "Simulated results,
conservative fills" label (PRD.md section 9) — the canvas renders this as
a pill badge in the Scoreboard header; Positions and Today need the same
treatment wherever a dollar P&L number appears.
