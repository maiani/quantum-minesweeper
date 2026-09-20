// static/scripts/bloch-help.js
//
// Adapter between this game's help panel and `blochkit.js`, the standalone Bloch
// sphere widget vendored beside it. blochkit knows nothing about minesweeper: it
// speaks Bloch vectors, gate names and ket names, and takes every colour from a
// palette object. What lives here is only what is genuinely this game's -- which
// design token each colour comes from, how a help topic id names a gate, and the
// lifecycle of the one animation the help panel owns.
//
// This is a trial surface, reached only when the JS_BLOCH_SPHERE feature flag
// is on. The tracked, LaTeX-rendered SVGs under static/help/*/svgs/ stay the
// default and are untouched.

import { GateAnimation, MEASURE, gateVector, isMeasurement } from "./blochkit.js";

/**
 * blochkit's palette keys, mapped onto this project's design tokens.
 *
 * Every value is a `var(--token)` rather than a literal, which is both what DESIGN.md
 * requires -- colour is declared once, in `:root` and `html.light` in base.css -- and
 * what makes the sphere follow the light/dark toggle for free: blochkit passes these
 * strings to SVG untouched, so the browser resolves them per theme on every repaint.
 *
 * Two deliberate departures from blochkit's defaults, both because this game means
 * something different by the picture than the game blochkit came from did:
 *
 *  - The gate's rotation axis gets its own colour, `axis-gate`. Left unset, blochkit
 *    colours it after whichever drawn axis it lies on and falls back to the state
 *    vector's colour for an axis that is none of the three -- so H, whose axis is
 *    the x+z diagonal, drew its axis in exactly the colour of the vector turning
 *    about it.
 *  - South is `boom`, not white. In blochkit's home game north is the interesting
 *    pole; here the interesting pole is |1>, because |1> is the mine.
 */
export const HELP_PALETTE = {
  face: "var(--zero-bg)", // the disc, matching an explored tile
  // The wireframe and its guides, both from `muted`, separated by the opacities
  // blochkit already draws them at rather than by colour. It is the only token in
  // the palette that is mid-tone on BOTH themes -- it exists to be readable
  // secondary text either way -- and that is exactly what a wireframe on a tinted
  // disc needs. `border` and `tile-muted` were the obvious picks and both fail on
  // the light theme: `border` is a hairline tuned for edges against white, and on
  // the sphere's own disc it comes out at 1.04:1, which is not a faint line but no
  // line at all.
  line: "var(--muted)", // equator, meridian, silhouette
  muted: "var(--muted)", // drop-line to the equatorial plane, orbit guides
  // Low-chroma hues, so the triad reads without competing with the colours that
  // carry meaning on the board. See the note beside them in base.css.
  //
  // Each falls back to `muted`, and the fallback is not decoration. These are the
  // newest tokens in the palette, and blochkit sets them as SVG *presentation
  // attributes* (`fill="var(--axis-x)"`). An unresolved var() there is not ignored
  // in favour of an inherited colour -- the declaration is invalid, so the property
  // takes its initial value, which is black. A stylesheet cached from before these
  // tokens existed therefore renders black axes and black x/y/z labels, invisible
  // on the dark theme, while every older token on the same drawing still resolves.
  // The fallback degrades that to the previous monochrome axes instead. It names a
  // token rather than a literal, so colour is still declared only in base.css.
  axisX: "var(--axis-x, var(--muted))",
  axisY: "var(--axis-y, var(--muted))",
  axisZ: "var(--axis-z, var(--muted))",
  gateAxis: "var(--axis-gate, var(--pin))", // the axis this gate turns about, never --accent
  vector: "var(--accent)", // the state itself: the subject of the picture
  target: "var(--win)", // where the gate would leave it
  north: "var(--fg)", // |0> -- no mine
  south: "var(--boom)", // |1> -- the mine
  pole: "var(--pin)", // unused unless `flag` is turned on, but pin is the flag here
  // No second font family: DESIGN.md sets everything in the platform UI stack, so
  // inherit it rather than let blochkit fall back to its own monospace list.
  mono: "inherit",
};

/**
 * Topics that are a move rather than a gate, and the blochkit token for each.
 *
 * Measure is the one so far. blochkit draws it from the same widget -- a measurement
 * is a null rotation there, and `MEASURE` is its name -- showing the state sitting
 * still and then collapsing onto a pole, with a fresh outcome drawn on every
 * repetition so the reader can see that the result is a sample and not a property of
 * the state. That is exactly what Measure is in this game, and `M-move` has never had
 * an illustration at all.
 */
const MOVE_TOKENS = { "M-move": MEASURE };

/**
 * The blochkit token a help topic is about, or null if the sphere cannot draw it.
 *
 * Help topics are the directory names under static/help/, which name a gate as
 * `"<GATE>-gate"` in upper case -- `SDG-gate`, not `Sdg-gate`. blochkit's lookup is
 * case-insensitive precisely so that spelling needs no table here.
 *
 * The two-qubit gates fall out for free: CX, CY, CZ and SWAP have no entry in blochkit's
 * `GATES`, because a Bloch sphere draws one qubit, so they keep their circuit diagrams
 * and are never given a sphere. ONE_QUBIT_GATES in quantum_backend.py stays the
 * authority on which gates are which; this only has to agree with it, and a gate added
 * there without a `GATES` entry simply gets no sphere rather than a wrong one.
 */
export function gateOfTopic(topicId) {
  if (!topicId) return null;
  if (Object.hasOwn(MOVE_TOKENS, topicId)) return MOVE_TOKENS[topicId];
  const match = /^(.+)-gate$/.exec(topicId);
  if (!match) return null;
  return gateVector(match[1]) ? match[1] : null;
}

/**
 * Which start state a topic opens on.
 *
 * A gate's own visual.html already names one in its `<img src>`, so this only has to
 * answer for the topics drawn from nothing. Measure opens on |+>, because |0> and |1>
 * are exactly the two states whose measurement shows nothing: the interesting picture
 * is the one where the outcome is not already decided.
 */
export const defaultState = (topicId) =>
  isMeasurement(gateOfTopic(topicId)) ? "+" : "0";

/** Whether the live sphere can draw this help topic at all. */
export const canDraw = (topicId) => gateOfTopic(topicId) !== null;

/**
 * The live gate animation the help panel owns.
 *
 * One of these is kept for the whole panel and re-pointed at whatever topic is on
 * screen, rather than one per topic: `GateAnimation` owns a requestAnimationFrame
 * loop, and the help panel replaces its own innerHTML whenever the topic changes,
 * which would otherwise orphan the SVG while leaving its loop running forever.
 */
export class GateSphere {
  constructor(container) {
    this.film = new GateAnimation(container, {
      radius: 54,
      palette: HELP_PALETTE,
      poleLabels: ["|0⟩", "|1⟩"],
      // The help panel's drawing is the whole point of the panel, not an inline
      // tip, so it is worth being able to turn. Which way a vector points is
      // genuinely ambiguous from one fixed angle -- this is the answer to that,
      // and it is the same gesture blochkit's own sphere has.
      interactive: true,
      label: "What this move does to the state",
    });
  }

  /**
   * Show what help topic `topicId` does to the state named by `stateKey` -- a
   * `data-state` value from the existing state-selector buttons, which are already
   * spelled the way blochkit names its kets. Returns false, having drawn nothing, if
   * this is not a topic the sphere can draw.
   *
   * The camera is deliberately not reset between calls: if the reader has turned the
   * sphere to see something, picking another start state must not undo it.
   */
  show(topicId, stateKey) {
    const token = gateOfTopic(topicId);
    if (token === null) return false;
    // `token` is a gate name, or MEASURE, which blochkit reads as "measure".
    this.film.show(token, stateKey);
    return true;
  }

  /** Halt the animation loop. Always call this before the container goes away. */
  stop() {
    this.film.stop();
  }
}
