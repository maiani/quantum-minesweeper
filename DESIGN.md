---
version: alpha
name: Quantum Minesweeper
description: >-
  The visual system for the Quantum Minesweeper board, its contextual help, and
  its setup and about pages. An interface built on CSS custom properties,
  tuned so that a grid of small square tiles stays readable while carrying
  colour-coded quantitative information. Retro, dark, and light are the three
  shipped themes. Retro is the default a first visit opens in, the one place a
  webfont appears, and still getting its narrow-phone and reduced-motion pass;
  dark and light are set in system fonts.
colors:
  # ---- Dark theme (the unclassed base) ---------------------------------
  # These are the values in `:root` in static/styles/base.css, verbatim.
  bg: "#090c13"
  fg: "#e8e8e8"
  muted: "#7a7f87"
  tile-muted: "#5a6070"
  zero-bg: "#1a1d24"
  btn-bg: "#2a2f3f"
  btn-bg-hover: "#353c4e"
  accent: "#6aa0ff"
  accent-hover: "#82b4ff"
  on-accent: "#0b1b33"
  border: "rgba(232, 232, 232, 0.22)"
  header-bg: "rgba(32, 36, 49, 0.95)"
  box-overlay: "rgba(26, 28, 51, 0.55)"
  pin: "#ffcf33"
  boom: "#ff4d4d"
  win: "#57c95e"
  axis-x: "#b98a72"
  axis-y: "#7fae90"
  axis-z: "#8496b8"
  axis-gate: "#f472b6"

  # ---- Light theme -----------------------------------------------------
  # The `html.light` block in base.css. Same token names, `-light` suffix.
  bg-light: "#e6ebf3"
  fg-light: "#1e1e1e"
  muted-light: "#5c636e"
  tile-muted-light: "#9ba7b9"
  zero-bg-light: "#d7dfea"
  btn-bg-light: "#fbfcfe"
  btn-bg-hover-light: "#edf2fa"
  accent-light: "#3f7ad6"
  accent-hover-light: "#5f95ea"
  on-accent-light: "#ffffff"
  border-light: "#dce3ec"
  header-bg-light: "rgba(255, 255, 255, 0.82)"
  box-overlay-light: "rgba(255, 255, 255, 0.62)"
  pin-light: "#d99000"
  boom-light: "#e64545"
  win-light: "#2e7d32"
  axis-x-light: "#8d5f48"
  axis-y-light: "#4c7a5c"
  axis-z-light: "#5a6b8c"
  axis-gate-light: "#a4247e"

  # ---- Retro theme -------------------------------------------------------
  # The `html.retro` block in base.css. Same token names, `-retro` suffix.
  # Colour-sampled from poster-v2.pdf in the repo root; see Colors.
  bg-retro: "#f6dbac"
  fg-retro: "#01204e"
  muted-retro: "#5b6b85"
  tile-muted-retro: "#aa9977"
  zero-bg-retro: "#f4ce9a"
  btn-bg-retro: "#fdf1da"
  btn-bg-hover-retro: "#fff8ea"
  accent-retro: "#018391"
  accent-hover-retro: "#12a3b3"
  on-accent-retro: "#ffffff"
  border-retro: "rgba(1, 32, 78, 0.25)"
  header-bg-retro: "rgba(246, 219, 172, 0.9)"
  box-overlay-retro: "rgba(246, 219, 172, 0.65)"
  pin-retro: "#d48f58"
  boom-retro: "#d14820"
  win-retro: "#46723a"
  axis-x-retro: "#8a6a4a"
  axis-y-retro: "#4c7a62"
  axis-z-retro: "#4a5a7a"
  axis-gate-retro: "#a8397e"

  # ---- Retro-only chrome -------------------------------------------------
  # No dark/light counterpart -- unlike every pair above, these name a
  # feature (the status counters' sunken LCD-digit look) that only exists as
  # a retro flourish, not a role every theme fills. See Colors.
  lcd-bg-retro: "#170f08"
  lcd-fg-retro: "#ff5a36"

  # ---- Theme-independent identity colours ------------------------------
  # The two entanglement-probe regions are deliberately the same on both
  # themes: they identify region A and region B, and they are drawn as rings
  # rather than as text, so they are not part of the surface palette.
  probe-a: "#38bdf8"
  probe-b: "#f59e0b"

  # ---- Conventional aliases --------------------------------------------
  # Provided so the palette reads as a standard design system. The names above
  # are the ones that appear in the stylesheets, as `var(--accent)` and so on.
  primary: "{colors.accent}"
  secondary: "{colors.muted}"
  neutral: "{colors.btn-bg}"
  surface: "{colors.bg}"
  on-surface: "{colors.fg}"
  error: "{colors.boom}"
  success: "{colors.win}"
typography:
  # `fontFamily` is one stack everywhere except retro, the one theme with
  # webfonts; the entries below are the base (dark- and light-shared) set.
  # `fontSize` gives the settled size -- see the Typography section for the
  # fluid ranges the stylesheets actually write, which the Dimension type
  # cannot express.
  headline-page:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 2rem
    fontWeight: 700
  headline-app:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 1.4rem
    fontWeight: 600
  headline-section:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 1.25rem
    fontWeight: 700
  headline-result:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 1.4rem
    fontWeight: 700
  body-md:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 1rem
    fontWeight: 400
  body-sm:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 0.95rem
    fontWeight: 400
  label-md:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 0.95rem
    fontWeight: 400
  label-sm:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 0.85rem
    fontWeight: 400
  label-xs:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 0.78rem
    fontWeight: 400
  # Every figure the player reads off the interface. `tabular-nums` is the point
  # of these two: a clue or a counter must not reflow as its digits change.
  numeric-status:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 1rem
    fontWeight: 600
    fontFeature: "'tnum' 1"
  numeric-clue:
    fontFamily: system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif
    fontSize: 15px
    fontWeight: 600
  # Retro's headings. Racing Sans One (Google Fonts, SIL OFL) -- a bold,
  # slanted "motion" display face -- replaced an earlier pass's Titan One,
  # which chased poster-v2.pdf's lettering more literally; "Racer", the font
  # actually used in that poster's title, turned out to be CC BY-NC-ND and
  # not free for commercial use, so this is an open substitute in the same
  # racing/speed register rather than a literal match. One weight exists,
  # hence 400 here where the base entries hold 600-700 -- see the Typography
  # section for why faking a heavier weight is wrong here.
  headline-page-retro:
    fontFamily: "'Racing Sans One', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif"
    fontSize: 2rem
    fontWeight: 400
  headline-app-retro:
    fontFamily: "'Racing Sans One', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif"
    fontSize: 1.4rem
    fontWeight: 400
  headline-section-retro:
    fontFamily: "'Racing Sans One', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif"
    fontSize: 1.25rem
    fontWeight: 400
  headline-result-retro:
    fontFamily: "'Racing Sans One', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif"
    fontSize: 1.4rem
    fontWeight: 400
  # Retro's body text and controls -- everything the heading face is wrong
  # for (see above). VT323 (Google Fonts, SIL OFL) is set on `body` plus
  # `button`, `input`, and `select` explicitly, since form controls do not inherit
  # `body`'s font in most browsers. One entry stands in for `body-md` through
  # `label-xs` above: the size and weight scale is unchanged by retro, only
  # the family is, so this names the family swap once rather than six times.
  body-md-retro:
    fontFamily: "'VT323', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif"
    fontSize: 1.15rem
    fontWeight: 400
  # `.btn` only -- see the Typography section for why this is not the body
  # face. Press Start 2P (Google Fonts, SIL OFL) at a much smaller size than
  # its surroundings, because it is roughly twice as wide per glyph.
  label-md-retro:
    fontFamily: "'Press Start 2P', 'VT323', system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Helvetica Neue, Arial, sans-serif"
    fontSize: 0.6rem
    fontWeight: 400
  # The status counters' sunken LCD-digit look. VT323 is also the closest
  # open match this set has to a 7-segment display. `tabular-nums` still
  # applies -- VT323 is monospace already, so it costs nothing extra here.
  numeric-status-retro:
    fontFamily: "'VT323', monospace"
    fontSize: 1.4rem
    fontWeight: 400
    fontFeature: "'tnum' 1"
rounded:
  none: 0px
  xs: 2px
  sm: 4px
  md: 6px
  lg: 8px
  xl: 10px
  full: 999px
spacing:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  xl: 16px
  xxl: 24px
  xxxl: 28px
  # Measures, not rhythm: the widths the page and its panels are held to.
  content-max: 1000px
  reading-max: 900px
  form-max: 520px
  sidebar-max: 400px
  # The board's own bounds. A tile is sized between these from the width the
  # board container actually has; it is never a fixed number.
  tile-max: 40px
  tile-min: 16px
  # Retro's bevel spends 2px of each side of a tile, so its minimum is the
  # shared one plus the bevel, leaving clue text the same room.
  tile-min-retro: 20px
  touch-target: 44px
components:
  button:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.fg}"
    typography: "{typography.label-md}"
    rounded: "{rounded.md}"
    padding: 8px 12px
    width: 44px
  button-hover:
    backgroundColor: "{colors.btn-bg-hover}"
  button-active:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
  button-disabled:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.muted}"
  button-tool:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.fg}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.md}"
    padding: 6px 12px
    width: 36px
  button-cta:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.md}"
    padding: 8px 16px
  button-cta-hover:
    backgroundColor: "{colors.accent-hover}"
  button-pill:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.fg}"
    typography: "{typography.label-md}"
    rounded: "{rounded.full}"
    padding: 8px 16px
  tile-unexplored:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.tile-muted}"
    typography: "{typography.numeric-clue}"
    rounded: "{rounded.md}"
  tile-explored:
    backgroundColor: "{colors.zero-bg}"
    textColor: "{colors.fg}"
    typography: "{typography.numeric-clue}"
    rounded: "{rounded.md}"
  tile-pinned:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.pin}"
  tile-mine:
    backgroundColor: "{colors.zero-bg}"
    textColor: "{colors.boom}"
  card:
    backgroundColor: "{colors.box-overlay}"
    textColor: "{colors.fg}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 12px 14px
  panel-modal:
    backgroundColor: "{colors.bg}"
    textColor: "{colors.fg}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.xl}"
    padding: 24px 28px
  app-header:
    backgroundColor: "{colors.header-bg}"
    textColor: "{colors.fg}"
    typography: "{typography.headline-app}"
    rounded: "{rounded.md}"
    padding: 10px 18px
  status-counter:
    backgroundColor: transparent
    textColor: "{colors.fg}"
    typography: "{typography.numeric-status}"
    rounded: "{rounded.md}"
    padding: 0.4em 0.8em
  probe-bar:
    backgroundColor: "{colors.box-overlay}"
    textColor: "{colors.fg}"
    typography: "{typography.label-sm}"
    rounded: "{rounded.md}"
    padding: 0.4rem 0.6rem
  input-field:
    backgroundColor: "{colors.btn-bg}"
    textColor: "{colors.fg}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.md}"
    padding: 8px 10px
  sidebar-header:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.headline-app}"
    padding: 10px 0
  table-header:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.label-sm}"
    padding: 8px 12px
  result-message-win:
    textColor: "{colors.win}"
    typography: "{typography.headline-result}"
  result-message-lost:
    textColor: "{colors.boom}"
    typography: "{typography.headline-result}"

  # ---- Light-theme variants --------------------------------------------
  # Only what actually changes. Geometry, type, and padding are shared with the
  # dark entries above; `html.light` in base.css overrides colour and the
  # shadow tint, nothing else. The one structural difference is stated under
  # Elevation & Depth: dark separates a control from its panel by fill, light
  # by a 1px edge in `border-light`.
  button-light:
    backgroundColor: "{colors.btn-bg-light}"
    textColor: "{colors.fg-light}"
  button-light-hover:
    backgroundColor: "{colors.btn-bg-hover-light}"
  button-light-active:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.on-accent-light}"
  button-light-disabled:
    backgroundColor: "{colors.btn-bg-light}"
    textColor: "{colors.muted-light}"
  button-cta-light:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.on-accent-light}"
  button-cta-light-hover:
    backgroundColor: "{colors.accent-hover-light}"
  tile-unexplored-light:
    backgroundColor: "{colors.btn-bg-light}"
    textColor: "{colors.tile-muted-light}"
  tile-explored-light:
    backgroundColor: "{colors.zero-bg-light}"
    textColor: "{colors.fg-light}"
  tile-pinned-light:
    backgroundColor: "{colors.btn-bg-light}"
    textColor: "{colors.pin-light}"
  tile-mine-light:
    backgroundColor: "{colors.zero-bg-light}"
    textColor: "{colors.boom-light}"
  card-light:
    backgroundColor: "{colors.box-overlay-light}"
    textColor: "{colors.fg-light}"
  panel-modal-light:
    backgroundColor: "{colors.bg-light}"
    textColor: "{colors.fg-light}"
  app-header-light:
    backgroundColor: "{colors.header-bg-light}"
    textColor: "{colors.fg-light}"
  sidebar-header-light:
    backgroundColor: "{colors.accent-light}"
    textColor: "{colors.on-accent-light}"
  result-message-win-light:
    textColor: "{colors.win-light}"
  result-message-lost-light:
    textColor: "{colors.boom-light}"

  # ---- Retro-theme variants ----------------------------------------------
  # Same shape as the light-theme variants above: colour only, borrowed from
  # `html.retro` in base.css. The four heading entries also swap in the
  # matching `-retro` typography token, which is where the Racing Sans One
  # webfont comes from -- see Typography. `button-retro` does too, for Press Start
  # 2P. `status-counter-retro`, at the end, is the one exception to
  # "colour only" beyond that: the LCD-digit look changes its background too,
  # not just its text colour.
  button-retro:
    backgroundColor: "{colors.btn-bg-retro}"
    textColor: "{colors.fg-retro}"
    typography: "{typography.label-md-retro}"
  button-retro-hover:
    backgroundColor: "{colors.btn-bg-hover-retro}"
  button-retro-active:
    backgroundColor: "{colors.accent-retro}"
    textColor: "{colors.on-accent-retro}"
  button-retro-disabled:
    backgroundColor: "{colors.btn-bg-retro}"
    textColor: "{colors.muted-retro}"
  button-cta-retro:
    backgroundColor: "{colors.accent-retro}"
    textColor: "{colors.on-accent-retro}"
  button-cta-retro-hover:
    backgroundColor: "{colors.accent-hover-retro}"
  tile-unexplored-retro:
    backgroundColor: "{colors.btn-bg-retro}"
    textColor: "{colors.tile-muted-retro}"
  tile-explored-retro:
    backgroundColor: "{colors.zero-bg-retro}"
    textColor: "{colors.fg-retro}"
  tile-pinned-retro:
    backgroundColor: "{colors.btn-bg-retro}"
    textColor: "{colors.pin-retro}"
  tile-mine-retro:
    backgroundColor: "{colors.zero-bg-retro}"
    textColor: "{colors.boom-retro}"
  card-retro:
    backgroundColor: "{colors.box-overlay-retro}"
    textColor: "{colors.fg-retro}"
  panel-modal-retro:
    backgroundColor: "{colors.bg-retro}"
    textColor: "{colors.fg-retro}"
  app-header-retro:
    backgroundColor: "{colors.header-bg-retro}"
    textColor: "{colors.fg-retro}"
    typography: "{typography.headline-app-retro}"
  sidebar-header-retro:
    backgroundColor: "{colors.accent-retro}"
    textColor: "{colors.on-accent-retro}"
    typography: "{typography.headline-app-retro}"
  result-message-win-retro:
    textColor: "{colors.win-retro}"
    typography: "{typography.headline-result-retro}"
  result-message-lost-retro:
    textColor: "{colors.boom-retro}"
    typography: "{typography.headline-result-retro}"
  # Not colour-only, unlike the rest of this block: the LCD-digit look (see
  # Colors) has no dark/light counterpart to vary from, so this is the one
  # retro variant with its own backgroundColor rather than a themed swap of
  # the base `status-counter`'s transparent fill.
  status-counter-retro:
    backgroundColor: "{colors.lcd-bg-retro}"
    textColor: "{colors.lcd-fg-retro}"
    typography: "{typography.numeric-status-retro}"
    rounded: "{rounded.xs}"
    padding: 0.4em 0.8em
---

# Quantum Minesweeper

## Overview

Quantum Minesweeper is a research artefact that has to work as a game. It is
played on a dense grid of small square buttons, each carrying a number the
player is expected to reason about, so the interface has one overriding job:
make quantitative information legible at tile sizes down to sixteen pixels,
without the page around it competing for attention.

The result is quiet and instrument-like rather than playful. The chrome is
near-monochrome; a single blue accent marks everything interactive; and colour
is spent almost entirely on the board, where it carries meaning. The default
theme is dark, and the light theme is a full peer rather than an afterthought
-- both are tuned separately, because the same hue cannot read on a near-black
tile and a near-white one.

Two rules follow from this and are worth stating before the palette:

**Colour is declared once.** `:root` and `html.light` in
`static/styles/base.css` are the only two places in the codebase where a colour
value is written. Every other rule refers to a token. A literal outside those
blocks is either a black or white alpha used as a shadow or scrim, or it is a
bug -- a colour that cannot follow the theme. This file mirrors those two
blocks; **`base.css` remains the implementation of record**, and the two are
changed together.

**Presentation lives in the frontend, and is split once more inside it.** The
serialized game state carries no symbols, labels, or colours. `render.js`
decides *which* presentation a cell gets and publishes it as a custom property;
the stylesheet decides what that presentation looks like in the active theme.
The clue phase colour is the worked example, described under Colors below.

## Colors

The palette is a near-neutral surface stack plus one accent, and then a small
set of colours that exist only to mean something.

- **Surface stack.** Three greys in a fixed order on both themes: the page is
  the ground (`bg`), an unexplored tile sits proud of it (`btn-bg`), and an
  explored tile is sunk below it (`zero-bg`). Ordering them consistently is
  what makes the board readable at a glance; when the three light-theme greys
  once sat within three percent luminance of each other, the grid was invisible
  and a cell could only be located by whether it held a number.
- **Accent (`#6aa0ff` dark, `#3f7ad6` light).** The single interaction colour:
  headings, links, focus rings, the selected tool, the help panel's header.
  Because the two themes' accents are blues of very different lightness,
  `on-accent` flips with them -- dark ink on the dark theme's pale blue, white
  on the light theme's deeper one. Text is never drawn on an accent fill
  without it.
- **Outcome colours.** `boom` for mines and losses, `win` for a win, `pin` for
  a player's flag. These are semantics, not decoration: a loss is announced in
  exactly the red the board draws its mines in.
- **Bloch axis colours** (`axis-x`, `axis-y`, `axis-z`). The x, y and z axes of
  the Bloch sphere in the contextual help. Three hues, so the triad can be read
  at a glance, but deliberately held at low chroma: they are reference
  furniture, and every saturated colour in this palette already means something
  (`boom` a mine, `win` a win, `accent` the one interaction colour). An axis at
  full chroma would compete with those, and a blue z-axis at `accent` strength
  would read as the state vector itself.
- **The rotation axis** (`axis-gate`). The axis a gate turns about is the one
  thing on that drawing the reader is asked to look at, so it is the one axis
  colour not held back. It is magenta because magenta is the only hue nothing
  else in the palette uses: it stays distinct from all three axes, from
  `accent` (the state vector it must never share), and from `win` and `boom`.
  It has its own token rather than borrowing `pin` because gold cannot be read
  on the light theme's sphere -- against the disc it reaches 1.9:1, and
  darkening it to compensate turns it into `axis-x`'s brown.

  The sphere's wireframe and guides come from `muted`, separated by opacity
  rather than by colour. It is the only token that is mid-tone on *both*
  themes, which is what a wireframe on a tinted disc needs. `border` is a
  hairline tuned for edges against white; on the sphere's own disc it is
  1.04:1, which is not a faint line but no line at all.
- **Probe identity colours** (`probe-a`, `probe-b`). The only tokens that do
  not change between themes, because they name the two entanglement-probe
  regions rather than participating in the surface palette. They are drawn as
  outlines and rings so that a tile keeps its own clue or pin colour while it
  is in a region.
- **One hairline** (`border`). There were once five spellings of this edge;
  there is now one token.
- **Retro.** A third theme, `html.retro`, colour-sampled from a reference
  poster rather than invented: `accent` is teal, that poster's own "Start
  Game" button and its "QUANTUM" highlight; `boom` is its explosion orange,
  not a new colour competing with it; `win` and `pin` carry its WIN badge's
  green and its title's peach, darkened off the poster's flat, large-shape
  values the way a token drawn as small text next to the board needs to be.
  It follows the light theme's surface-stack ordering (`bg` cream, `btn-bg`
  proud of it, `zero-bg` sunk) and the same low-chroma treatment for the
  Bloch axes. It is a kept theme, not a trial, but still incomplete: its
  shapes (see Elevation & Depth and Shapes) have not had a real narrow-phone
  pass, which is a lower bar than a contrast audit but not yet cleared -- see
  `docs/roadmap.md`'s Retro theme entry for the rest of what is open.

  Two more tokens, `lcd-bg` and `lcd-fg`, exist only under retro: the status
  counters' sunken display, standing in for the original Minesweeper's own
  7-segment LED readout. `lcd-fg` is a second, brighter cousin of `boom`
  rather than a reuse of it, because a small warning colour on a cream page
  and a glowing display digit are different briefs even though they are the
  same hue family.

### The clue phase colour

A clue's number is the Z part of its neighbours' summed Bloch vector: the sum
of their mine probabilities. Its colour is the rest of that same vector sum,
(ΣX, ΣY), sent as `clue_phase` in the game state. The hue is the angle of that
pair -- the neighbourhood's phase on the Bloch sphere -- so a phase gate, which
changes no number at all, still visibly changes the clue: S turns it a quarter
of the way round the wheel, Z half way. A clue whose neighbours carry no phase
(classical, entangled with other cells, or in opposite phases that cancel) is
plain `fg` ink on a plain `zero-bg` tile. Colour no longer says how dangerous a
clue is; the number already does.

- **The wheel.** Phase 0, |+>, sits at OKLCH hue 65 (`--phase-hue0`, one value
  for all themes), so the four equator states read orange (|+>), green (|i>),
  blue (|->) and magenta (|-i>), with the angles between filling the circle in
  the same rainbow order. Of the anchorings tried in 5-degree steps, this
  quartet is the most colourful and, under simulated protan and deutan vision
  (Machado 2009), separates the four almost as well as the most robust offset
  (0.046 against 0.048 OKLab at worst). No hue wheel is safe for every reader:
  the adjacent quarter-turns -- orange and green, blue and magenta -- are the
  pairs a red-green deficiency confuses, which is why every clue's label also
  carries its phase in degrees.
- **Lightness is one value per theme** (`--phase-l`), for every hue, so no
  phase is more legible than another. Chroma is as strong as sRGB can show at
  that hue and lightness, capped at `--phase-c`: at one lightness a teal runs
  out of screen colours long before a magenta does. CSS cannot ask where the
  gamut boundary is, so `render.js` finds it and publishes the result (see
  Do's and Don'ts).
- **The tile takes a pastel of the same hue** at `zero-bg`'s own lightness
  (`--phase-tint-l`, capped at `--phase-tint-c`), so a phased tile still reads
  as an opened one. Thin semibold digits carry very little colour on their own,
  above all on retro's cream; the tint is what makes the phase readable at a
  glance. At game over the digit takes the usual mute while the tint stays.

| Theme | `--phase-l` | `--phase-c` | Tint L / cap | Worst digit on its tint |
|---|---|---|---|---|
| Dark | 0.75 | 0.14 | 0.231 / 0.045 | 7.20:1 |
| Light | 0.48 | 0.14 | 0.901 / 0.05 | 4.66:1 |
| Retro | 0.46 | 0.14 | 0.872 / 0.07 | 4.67:1 |

Every phase clears WCAG AA in every theme, measured at one-degree steps round
the whole wheel. The light themes' lightness is set by that constraint: dark
digits on a pale tile must stay near L 0.47 to reach 4.5:1 at every hue.

## Typography

There is no webfont in the dark or light theme. Both are set in the platform
UI stack (`system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell,
'Helvetica Neue', Arial, sans-serif`), which keeps the installable app
offline-complete and costs nothing to load. Hierarchy is carried by size,
weight, and the muted token -- never by a second family.

Retro is the one deliberate, labelled exception, and now uses three webfonts,
not one, because heading-only turned out to read as "the wrong theme" the
moment a reader's eye left the title:

- **Racing Sans One** on `h1` and `h2` -- a bold, slanted "motion" display
  face (Google Fonts, SIL OFL). The poster's own title face, "Racer", is not
  free for commercial use (CC BY-NC-ND, a paid licence required), so this is
  an open substitute in the same racing/speed register rather than a literal
  match to `poster-v2.pdf`'s lettering; an earlier pass used Titan One,
  which chased that lettering more literally. One weight exists, so
  `font-weight` is forced to 400 under `.retro`: leaving `h1`'s 700 or
  `.app-header h1`'s 600 in place would ask the browser to synthesise a
  bolder weight, and a synthetic bold on a face already this heavy is where
  display fonts go wrong.
- **VT323** on `body`, and explicitly on `button`, `input`, and `select` --
  most browsers' UA stylesheets do not give form controls `body`'s font by
  inheritance, so those three are named directly rather than relying on it.
  Board tiles are the exception: they keep the platform stack and the
  tile-scaled `numeric-clue` size in every theme. Retro's `button` rule used to
  reach them too, and its 1.3em outranked `numeric-clue`, putting ~27px clues
  on tiles of at most 40px, over the bevel. VT323 at `numeric-clue`'s size
  fits, but reads thin and small at the 9px floor, which is why tiles do not
  use it. A
  first pass paired the heading face with Baloo 2, a smooth rounded face, for
  everything else; it read as "not pixel" the moment a reader's eye left the
  title, which is what VT323 -- a bitmap terminal face redrawn as outlines --
  actually is. `font-size` is bumped 1.15x alongside it, because VT323 sits
  smaller than its nominal size at a given `rem` value.
- **Press Start 2P** on `.btn` only -- the canonical 8-bit arcade face, and
  genuinely too wide per glyph for a paragraph, which is why it is not the
  body face: at the same size as VT323 it would roughly double every line's
  width. Buttons are short text -- a single letter on the move row -- so this
  is where "unmistakably pixel" costs nothing. `font-size` drops to 0.62em
  under `.retro` for the same reason in reverse: without it, "Go to Advanced
  Setup" stops fitting on one line on a phone. Buttons are `min-width`, not a
  fixed width (see Buttons in Components), so they still grow to fit rather
  than clip.

Two things keep three webfonts from quietly breaking the "offline-complete"
rule above:

- One stylesheet request, made only while retro is the page's theme: by the
  pre-paint script in `<head>` when retro is the saved choice or the default,
  so the default theme does not flash its fallback fonts on every load, or by
  `theme_toggle.js` when a reader switches to it. It is never linked
  unconditionally, and dark and light never make it. The PWA's service worker
  caches the font files after the first online visit.
- Every `font-family` list still ends in the same system stack (VT323's and
  Press Start 2P's in a bare `sans-serif`, since neither has an obvious system
  equivalent), so a reader who picks retro while offline gets a plausible
  fallback rather than a blank space or a FOUC-flash of the wrong glyph
  shapes.

- **Headings** are centred and accent-coloured. Section headings on document
  pages go to weight 700; the sticky application title stays at 600 and on one
  line at every width.
- **Body and controls** sit at `0.95rem`, one notch below the browser default.
  The interface is dense and control-heavy, and full-size body text made the
  tool rows feel heavier than the board.
- **Weight, not colour, carries the small text.** Clue digits are semibold at
  tile sizes where a regular weight would break up, and the mine glyph goes to
  700.
- **Numbers get `font-variant-numeric: tabular-nums`.** The mine counter, the
  entanglement score, and the probe readout all update continuously;
  proportional digits made them jitter.

Most sizes are fluid, which the `fontSize` tokens above cannot express -- each
records the settled upper value. The stylesheets write:

| Role | CSS |
|:--|:--|
| `headline-page` | `clamp(1.4rem, 5vw, 2rem)` |
| `headline-app` | `clamp(1.2rem, 3vw, 1.4rem)` |
| `headline-section` | `clamp(1.1rem, 1.5vw, 1.25rem)` |
| `numeric-clue` | `max(9px, min(15px, calc(var(--tile-size) * 0.38)))` |

The last is the important one: clue text scales with the *tile*, not the
viewport. A twenty-five-column board has small tiles even on a wide screen, and
a viewport-based size overflows them.

Clues and the mine counter show one decimal place ("2.5"), because on a
quantum board they are sums of probabilities. A Classic game (Measure and Pin
only) writes whole numbers without it ("2", not "2.0"); a fraction keeps its
decimal even there, since Advanced Setup can pair Classic moves with superposed
mines. `formatNumber` in `render.js` is the one place this is decided.

## Layout & Spacing

The spacing scale is a 4px-based progression -- 4, 6, 8, 12, 16, 24, 28 -- used
loosely rather than as a strict grid. It is a rhythm, not a constraint to be
enforced retroactively across existing components.

What *is* strict is the set of measures:

- Page content is capped at **1000px** and centred, with a 16/24px gutter that
  drops to 8px below 480px and 4px below 360px.
- Prose (the About page, setup explainers, the About overlay) is capped at
  **900px**; the setup form at **520px**; the help sidebar at **400px** or 80
  viewport widths, whichever is smaller.
- Interactive targets have a **44px** minimum width.

### The board sizes itself

The board is the one component that does not take a fixed size. Its container
is a containment context, so `100cqw` is the board area's own width; the tile
size is that width divided by the column count, clamped between `tile-max`
(40px) and `tile-min` (16px; `tile-min-retro`, 20px, under retro, whose 2px
bevel on each side would otherwise leave a 16px tile's clue running over its
border). Tiles carry no padding: the browser's default would leave a small
tile a few pixels for its text and then stop centring it. Small boards
therefore do not inflate into slabs, and very wide boards scroll sideways
rather than shrinking to illegibility.
Every offered board size must stay fully reachable at every supported width.

Two consequences are load-bearing and must not be undone:

- **No layout may depend on a hard-coded header height.** The header is
  `position: sticky`, so it occupies its real height whatever the width makes
  that; anything that needs the number reads `--app-header-block-size`, which
  `layout.js` publishes from the measured element.
- **The board container centres with `justify-content: safe center`.** A
  centred flex item that overflows its container overflows in both directions,
  and the part before the scroll origin cannot be reached by scrolling at all.

### Breakpoints

`720px` (help panel goes inline, probe breakdown hides), `640px` (cards and
forms tighten), `600px` (header compacts and drops the player count, modals go
full-screen), `480px` (phone gutters, smaller tile radius), `360px` (minimum
gutters). `prefers-reduced-motion` is honoured globally, and the animations
that would freeze on a wrong keyframe are switched off individually.

## Elevation & Depth

Depth is stated in three ways, in increasing order of force.

1. **Fill.** On the dark theme a control is separated from its panel by being
   lighter than it. The light theme cannot do this -- `btn-bg` is `#fbfcfe` and
   the panel composites to about `#fafbfd` -- so it uses a **1px edge**
   instead. The border box is reserved as `1px solid transparent` on both, so
   toggling the theme never nudges a control's size.
2. **Shadow.** Deliberately soft and short-ranged. `0 1px 2px` for controls and
   tiles, `0 2px 6px` for cards, `0 4px 16px` for the game-over box, `0 12px
   48px` for the modal panel. The light theme's shadows are tinted navy
   (`rgba(30, 45, 80, …)`) rather than black; pure black reads as grime on a
   light ground.
3. **Inset.** The board's primary readout. An explored tile carries
   `inset 0 1px 2px` and the recessed `zero-bg` fill; an unexplored one keeps
   its raised fill and outer shadow. This belongs to the *surface*, not to the
   digit -- before it did, a revealed "2.0" sat on exactly the same tile as its
   unexplored neighbour and the two were told apart only by the number's
   colour.

Panels that float over content (the header, the help sidebar, cards, the probe
bar) use a translucent `box-overlay` or `header-bg` fill with a small
`backdrop-filter: blur()`. Both themes are translucent to the same degree; when
the light theme was once pinned near-opaque, it read as a wall where the dark
one read as frosted glass.

Retro replaces fill-and-shadow with a fourth depth cue instead of adding to
it: a 90s-Windows **bevel**. A raised control (a button, an unexplored tile)
gets a light top and left edge and a dark bottom and right edge; pressing it,
or revealing a tile, swaps the two, so the same two tokens (`--bevel-hi`,
`--bevel-lo`) draw every raised *and* every sunken surface in the theme.
Both are derived, not chosen independently: `--bevel-hi` is `--btn-bg`
lightened, `--bevel-lo` is `--fg` let through at partial opacity over
whatever it sits on, so the bevel keeps working across `--btn-bg`, `--bg`,
and `--zero-bg` without a third colour to keep in sync by hand. The status
counters go one step further, into a genuinely sunken **well**: a dark fill
(`--lcd-bg`) with the bevel inverted, standing in for the physical recess a
7-segment display sits in. Buttons drop the scale-based press animation the
other two themes use for the same reason silent-film title cards drop
colour -- the bevel flip already *is* the press, and animating both would be
two effects fighting to say the same thing.

## Shapes

Everything is a rounded rectangle at **6px** (`--radius`), the `md` step. The
scale exists mostly so the board can shed radius as tiles shrink: `sm` (4px)
below 480px and `xs` (2px) below 360px, because a 6px radius on a 16px square
is a circle.

Retro overrides `--radius` itself, to **2px** -- Win95 chrome had none of the
other themes' rounding, and the bevel above reads as a corner cut at a shallow
angle, not a curve, so a near-square corner is what makes it legible as a
bevel rather than an odd shadow. This is the one token in the file whose
*value* differs by theme rather than only its colour -- flagged here because
the `rounded` table above still gives one number, the dark/light one.

Three shapes depart from this on purpose:

- **Pills** (`full`, 999px) for the sandbox Reveal toggle and the loading
  progress track -- mode switches and progress, not ordinary buttons.
- **The modal panel** at `xl` (10px), one step softer, because it is the only
  element that floats free of the page.
- **Probe rings and badges**, drawn outside the tile box (`inset: -4px`, an 8px
  radius) so that a region outline never replaces the tile's own state colour.

Icons are drawn rather than fetched. The Nordita mark and the GitHub mark are
inlined SVG painted in `currentColor`, so one asset follows both themes; the
entanglement counter's interlocked rings are built in `render.js` for the same
reason, and sized in `em` so they track the text beside them. The board's own
symbols are a small fixed set of glyphs -- `■` unexplored, `⚑` pinned, `💥` a
mine outcome -- decoded in exactly one function.

## Components

### Buttons

One `.btn` base with size modifiers: `tool` (0.85rem, 36px minimum) for the
move row, `help` (0.85rem, 32px) for contextual-help triggers, and the default
(0.95rem, 44px) everywhere else. A selected tool takes an accent fill with
`on-accent` text; a disabled control keeps its fill and drops to `muted` at
60% opacity. Every control has an `active` state of `transform: scale(0.96)`,
which is the whole of the interface's tactility.

The accent *fill* is rationed: at most one per screen. On Setup it is the
research-survey call to action, which is deliberately not a `.btn` at all,
because `.btn` belongs to the game's controls.

Retro replaces `scale(0.96)` with its own tactility: pressing a button flips
its bevel from raised to sunken (see Elevation & Depth), the way a Win95
button did, and drops the scale entirely rather than combining the two.
Everywhere else keeps the scale.

### Tiles

The board button is the densest component and the only one whose type size,
box size, and radius are all derived at runtime. Its state classes --
`unexplored`, `pinned`, `mine`, `clue`, `empty` -- are set by `render.js` from
the numeric grid, plus `phased` on a clue whose neighbourhood has a phase (see
The clue phase colour), and the stylesheet supplies the appearance. Overlays (probe
outlines, reveal fills, entanglement halos and links) are layered over the tile
without disturbing its own colour, each in its own stacking level.

Retro draws its bevel (see Elevation & Depth) off `:disabled` rather than off
a state class: a tile becomes disabled exactly when it is revealed, which is
also exactly when its bevel should flip from raised to sunken, so the one
selector serves both without a second source of truth. `box-sizing:
border-box` is set alongside it, retro-only, because the border a bevel needs
would otherwise grow each tile past the width `--tile-size` derives for the
whole row (see game.css).

### Cards and panels

`card` covers the help cards, the setup form, the loading card, and rendered
document content: translucent fill, 6px radius, soft shadow, blurred backdrop.
The token's padding is the help card's `12px 14px`; the setup and loading cards
run `16px 18px` and document content `10px 20px`, all tightening below 640px.
`panel-modal` is the About overlay. Below 600px the modal stops being a card
and fills the viewport, trading its ✕ for a sticky bottom Close bar, because a
floating card at phone width is cramped and its corner control is hard to
reach.

### Status and probe readouts

The status counters and the entanglement probe bar are instrument readouts:
outlined, tabular-figured, and compact. A status counter's fill is nominally
`transparent` in the token above; in the stylesheet it is a 3% wash of `fg`,
which is enough to separate the pill from the page without introducing a
surface colour. The probe is a single row -- controls
at the start, result at the end -- and it must stay one row. It replaced a
164px five-block panel that pushed the move tools off a laptop screen, and
recovering that height is the standing constraint on anything added there.

Retro's status counters are the one place the theme reaches for a literal
prop rather than a restyled token: `--lcd-bg` replaces the 3% wash outright,
the bevel is sunken rather than raised (see Elevation & Depth), and
`.status-value` switches to VT323 -- see `status-counter-retro` and
`numeric-status-retro` above. `.status-icon`'s colour also changes, to
`--btn-bg`, because it is what carries the label text out of `--fg`, which
has no contrast left to give once the fill goes black.

### Forms

Inputs and selects take the control fill with a transparent 1px border that
becomes the accent on focus. `:focus-visible` puts a 2px accent outline at 2px
offset on every focusable element, and that rule is global -- keyboard
reachability is not per-component.

## Do's and Don'ts

- **Do** write every colour as a token. Add new values to `:root`, `html.light`
  *and* `html.retro` in `base.css`, and mirror them here in the same change.
- **Don't** write a colour literal outside those three blocks. The only
  exception is a black or white alpha used as a shadow or scrim.
- **Do** keep symbols, labels, colours, and visible tool choices in the
  frontend. Game-state payloads stay presentation-free.
- **Don't** let the renderer name a final colour. It publishes a normalised
  value (`--mine-p`, `--cols`, the clue's `--clue-hue`) and the stylesheet
  resolves it, because only CSS knows which theme is on. The clue's chroma is
  the one number the renderer derives from the theme: it reads the theme's
  `--phase-*` tokens to find the sRGB boundary for that hue, publishes the
  fitted chroma, and redraws the board when the theme changes. The colour
  itself is still composed in `game.css`, from tokens.
- **Do** design dark and light together, and check the light one on the board.
  Several of the tokens above exist only because a value that worked on
  near-black was invisible on near-white. Retro has not had that same
  obligation applied yet -- see Colors and Typography -- but should not be
  made to regress once it does.
- **Don't** add a second font family or a webfont to the dark or light theme.
  Both must stay offline-complete. Retro is the one deliberate, labelled
  exception -- see Typography for how it avoids costing the other two
  anything.
- **Do** use `tabular-nums` for any number that updates in place.
- **Don't** size board text or board chrome against the viewport. It scales
  with the tile.
- **Do** keep one accent fill per screen, and give anything drawn on it the
  `on-accent` token.
- **Don't** assume a fixed header height, and don't reintroduce a spacer
  element to fake one.
- **Do** honour `prefers-reduced-motion`, and check what the global freeze
  leaves on screen -- an animation that ends on a hidden keyframe needs its own
  reduced-motion rule.
- **Don't** add vertical furniture between the board and the move tools. That
  space is budgeted, and the probe bar's redesign is what bought it.

## Verification

This file is valid against the DESIGN.md `alpha` specification. To check it:

```
npx --yes @google/design.md lint DESIGN.md
```

It is deliberately not part of `pixi run check`, which stays Python-only and
offline. Run it by hand when the palette or the component list changes.

The linter reports no errors. It reports warnings that are known and expected,
and that should not be "fixed" by changing the palette without deciding the
underlying design question first:

- **`orphaned-tokens` for `border`, `border-light`, `border-retro`, `probe-a`,
  `probe-b`.** These are hairline and outline colours. The component schema
  models `backgroundColor` and `textColor` but has no border or outline slot,
  so there is no way to reference them. They are in active use; see Colors and
  Shapes.
- **`orphaned-tokens` for `axis-x`, `axis-y`, `axis-z`, `axis-gate` and their
  light and retro variants.** Same cause, one step further out: these are
  stroke colours for SVG drawn by `blochkit.js`, and the schema has no stroke
  slot and no component for a drawing. They are in active use; see Colors.
- **`contrast-ratio` on `button-disabled` (3.31:1).** Disabled controls are
  exempt from WCAG 1.4.3.
- **`contrast-ratio` on `tile-unexplored` (2.12:1) and its light (2.37:1) and
  retro (2.49:1) variants.** The `■` on an unexplored tile is decorative: the
  tile's state is carried by its raised fill, and every board button has an
  explicit `aria-label` naming its row, column, and state. The glyph is
  intentionally recessive so it does not compete with the clue digits beside
  it.
- **`contrast-ratio` on `tile-mine-light` (2.95:1) and `tile-mine-retro`
  (3.04:1).** Nominal only. The glyph is `💥`, which the platform renders in
  its own colours; the token applies to the surrounding text box, not to the
  emoji.
- **`contrast-ratio` on `tile-pinned-retro` (2.39:1).** The retro counterpart
  of `tile-pinned-light` below, at the same intent and roughly the same
  ratio: a pin is a player annotation the player needs to find again at a
  glance, not body text.

Two are open questions rather than settled exceptions:

- **White on the light theme's accent is 4.23:1** (`button-light-active`,
  `button-cta-light`, `sidebar-header-light`, and the admin table header). That
  clears AA for large text but not for normal text, and the selected tool
  button is normal text at `0.85rem`. Darkening `accent-light` or reserving the
  accent fill for large text would resolve it.
- **`tile-pinned-light` is 2.58:1** — the `⚑` in `pin-light` on a near-white
  tile. A pin is a player annotation the player needs to find again at a
  glance.

The clue phase colour has no such exception: every phase clears 4.5:1 in every
theme, as measured under Colors above.
