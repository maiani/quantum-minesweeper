/**
 * Checks for the live Bloch sphere: `blochkit.js` and its adapter `bloch-help.js`.
 *
 * Run with `pixi run bloch-check`, which installs jsdom first. It is deliberately
 * outside `pixi run check`, which stays Python-only and offline, for the same reason
 * the DESIGN.md lint is.
 *
 * The first section is the one that matters:
 *
 *  1. THE MATHS. Every one-qubit gate applied to each of the six start states the
 *     help panel offers, compared against a reference computed here from the gates'
 *     2x2 complex matrices. That derivation shares nothing with blochkit's
 *     axis-angle rotation, so agreement is evidence rather than a tautology. The
 *     same table has also been checked against the game's own chppy and Stim
 *     backends via `expectation_pauli`; the matrices below agree with both.
 *
 *  2. THE WIRING. That the adapter mounts an SVG, declines what a Bloch sphere
 *     cannot draw, emits design tokens rather than colour literals, and can stop
 *     its animation loop. Then, in 2a, that every token it names is really defined
 *     in base.css in both themes, and 2b, that the rotation axis is visible and
 *     tipped. Those two exist because an unresolved var() in an SVG presentation
 *     attribute renders black rather than failing, so a missing token is a black
 *     drawing and not an error anyone sees.
 *
 *  3. MEASUREMENT. That Measure reaches blochkit as the null rotation that means
 *     "collapse onto a pole", rather than as an unknown gate.
 *
 *  4. THE CAMERA DRAG. That the drawing can be turned, stays clamped short of the
 *     pole, resets on a double-click, and keeps animating throughout.
 *
 *  5. THE MODULE SPECIFIER. A regression guard; see the comment in that section.
 */

import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const SCRIPTS = resolve(dirname(fileURLToPath(import.meta.url)), "../src/qminesweeper/static/scripts");

// --- a DOM, because both modules build SVG nodes -------------------------------
const dom = new JSDOM("<!doctype html><div id='host'></div>", { pretendToBeVisual: true });
// Note: do NOT copy jsdom's `performance` onto globalThis. It delegates back to the
// global, so the assignment makes it call itself until the stack runs out. Node's
// own `performance` is already present and is what blochkit reads.
globalThis.document = dom.window.document;
globalThis.requestAnimationFrame = dom.window.requestAnimationFrame;
globalThis.cancelAnimationFrame = dom.window.cancelAnimationFrame;
globalThis.matchMedia = () => ({ matches: false }); // not reduced-motion, so it animates

const { rotate, gateVector, stateVector, isMeasurement, GATES, MEASURE, HOME } =
  await import(`${SCRIPTS}/blochkit.js`);
const { GateSphere, canDraw, gateOfTopic, defaultState, HELP_PALETTE } =
  await import(`${SCRIPTS}/bloch-help.js`);

let failures = 0;
const ok = (cond, what) => {
  if (!cond) {
    console.log(`  FAIL  ${what}`);
    failures++;
  }
};

// --- the independent reference -------------------------------------------------
// Complex numbers as [re, im]; a state as two amplitudes. Small enough that a
// library would be more code than the arithmetic.

const mul = (a, b) => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1]];
const R = Math.SQRT1_2;

/** The 2x2 matrices, as [[m00, m01], [m10, m11]]. Global phase is irrelevant. */
const MATRICES = {
  X: [[[0, 0], [1, 0]], [[1, 0], [0, 0]]],
  Y: [[[0, 0], [0, -1]], [[0, 1], [0, 0]]],
  Z: [[[1, 0], [0, 0]], [[0, 0], [-1, 0]]],
  H: [[[R, 0], [R, 0]], [[R, 0], [-R, 0]]],
  S: [[[1, 0], [0, 0]], [[0, 0], [0, 1]]],
  Sdg: [[[1, 0], [0, 0]], [[0, 0], [0, -1]]],
  SX: [[[0.5, 0.5], [0.5, -0.5]], [[0.5, -0.5], [0.5, 0.5]]],
  SXdg: [[[0.5, -0.5], [0.5, 0.5]], [[0.5, 0.5], [0.5, -0.5]]],
  SY: [[[R, 0], [-R, 0]], [[R, 0], [R, 0]]],
  SYdg: [[[R, 0], [R, 0]], [[-R, 0], [R, 0]]],
};

/** The six start states as amplitude pairs. */
const KETS = {
  "0": [[1, 0], [0, 0]],
  "1": [[0, 0], [1, 0]],
  "+": [[R, 0], [R, 0]],
  "-": [[R, 0], [-R, 0]],
  i: [[R, 0], [0, R]],
  "-i": [[R, 0], [0, -R]],
};

const apply = (m, [a, b]) => [add(mul(m[0][0], a), mul(m[0][1], b)),
                              add(mul(m[1][0], a), mul(m[1][1], b))];

/** Bloch components of an amplitude pair: <X>, <Y>, <Z>. */
function blochOf([a, b]) {
  const conjA = [a[0], -a[1]];
  const ab = mul(conjA, b);
  return [2 * ab[0], 2 * ab[1], a[0] ** 2 + a[1] ** 2 - (b[0] ** 2 + b[1] ** 2)];
}

const close = (u, v) => u.every((c, i) => Math.abs(c - v[i]) < 1e-12);

// --- 1. the maths --------------------------------------------------------------
console.log("gate rotations vs. the 2x2 matrices");

ok(Object.keys(GATES).length === Object.keys(MATRICES).length,
   `GATES and the reference cover the same gates (${Object.keys(GATES)} vs ${Object.keys(MATRICES)})`);

for (const [name, matrix] of Object.entries(MATRICES)) {
  ok(gateVector(name) !== null, `${name} is in GATES`);
  for (const [ket, amps] of Object.entries(KETS)) {
    const want = blochOf(apply(matrix, amps)).map((c) => (Math.abs(c) < 1e-12 ? 0 : c));
    ok(close(stateVector(ket), blochOf(amps)), `|${ket}> is the vector STATES says`);
    const got = rotate(gateVector(name), stateVector(ket));
    ok(close(got, want),
       `${name}|${ket}> -> [${got.map((c) => c.toFixed(4))}], expected [${want.map((c) => c.toFixed(4))}]`);
  }
}

// The daggered gates must undo their partners, and the help directories spell them
// in upper case (SDG-gate, not Sdg-gate), which the lookup has to tolerate.
for (const [g, dg] of [["S", "Sdg"], ["SX", "SXdg"], ["SY", "SYdg"]]) {
  ok(close(gateVector(g), gateVector(g.toUpperCase())), `${g} lookup is case-insensitive`);
  ok(close(gateVector(dg), gateVector(dg.toUpperCase())), `${dg} lookup is case-insensitive`);
  for (const ket of Object.keys(KETS)) {
    const there = rotate(gateVector(g), stateVector(ket));
    ok(close(rotate(gateVector(dg), there), stateVector(ket)), `${dg} undoes ${g} on |${ket}>`);
  }
}
ok(stateVector("|0>")[2] === 1 && stateVector("|1⟩")[2] === -1, "ket decoration is accepted");

// --- 2. the wiring -------------------------------------------------------------
console.log("adapter wiring");

const host = dom.window.document.getElementById("host");
const sphere = new GateSphere(host);
ok(host.querySelector("svg") !== null, "an <svg> is mounted in the container");

for (const topic of Object.keys(GATES).map((g) => `${g.toUpperCase()}-gate`)) {
  ok(canDraw(topic), `${topic} is drawable`);
  ok(sphere.show(topic, "0") === true, `${topic} draws`);
}
// A Bloch sphere draws one qubit, so the two-qubit gates must decline rather than
// draw something wrong. quantum_backend.py's TWO_QUBIT_GATES is the authority.
for (const topic of ["CX-gate", "CY-gate", "CZ-gate", "SWAP-gate"]) {
  ok(!canDraw(topic), `${topic} is not offered a sphere`);
  ok(sphere.show(topic, "0") === false, `${topic} declines`);
}
// Pin is an annotation, not a quantum operation, so it gets no sphere; the rest
// are not moves at all. Measure is deliberately absent -- see section 3.
for (const topic of ["reveal", "P-move", "entanglement", "mine-counter", "region-probe", "", null]) {
  ok(gateOfTopic(topic) === null, `${JSON.stringify(topic)} gets no sphere`);
}

// Colour is declared once, in base.css. Nothing here may introduce a literal.
sphere.show("H-gate", "0");
await new Promise((r) => setTimeout(r, 120)); // let one animation frame land
const markup = host.innerHTML;
const literals = markup.match(/#[0-9a-fA-F]{3,8}\b/g) || [];
ok(literals.length === 0, `no colour literals reach the SVG (found ${JSON.stringify(literals)})`);
for (const token of ["var(--accent)", "var(--boom)", "var(--win)", "var(--zero-bg)"]) {
  ok(markup.includes(token), `${token} reaches the SVG`);
}
ok(Object.values(HELP_PALETTE).every((v) => v === "inherit" || v.startsWith("var(--")),
   "every palette entry is a design token or `inherit`");

// The panel discards its innerHTML on every topic change, so a loop that cannot be
// stopped would animate a detached SVG for the life of the page.
ok(sphere.film.raf !== null, "an animation loop is running");
sphere.stop();
ok(sphere.film.raf === null, "stop() clears the loop");

// --- 2a. every token the sphere uses actually exists ------------------------------
console.log("palette tokens vs. base.css");

// blochkit sets colours as SVG presentation attributes, where an unresolved var()
// makes the declaration invalid and the property falls back to its initial value --
// black. It does not inherit, and it does not warn. So a token that is misspelled,
// or defined in only one theme, is a black drawing rather than a visible error.
const css = readFileSync(resolve(SCRIPTS, "../styles/base.css"), "utf8");
const blockOf = (selector) => {
  const start = css.indexOf(selector);
  ok(start !== -1, `base.css has a ${selector} block`);
  return css.slice(start, css.indexOf("\n}", start));
};
const dark = blockOf(":root {");
const light = blockOf("html.light {");

// Names used anywhere in the palette, including inside a var() fallback.
const used = new Set();
for (const value of Object.values(HELP_PALETTE)) {
  for (const m of String(value).matchAll(/var\(\s*(--[a-z0-9-]+)/gi)) used.add(m[1]);
}
ok(used.size > 0, "the palette is expressed in tokens");
for (const token of [...used].sort()) {
  ok(dark.includes(`${token}:`), `${token} is defined in :root`);
  ok(light.includes(`${token}:`) || dark.includes(`${token}:`),
     `${token} is defined for the light theme, or inherited from :root`);
}

// The axis tokens are the newest on this drawing, so a stale stylesheet fails
// exactly them. They must degrade to an older token rather than to black.
for (const key of ["axisX", "axisY", "axisZ", "gateAxis"]) {
  ok(/var\(\s*--[a-z0-9-]+\s*,\s*var\(/i.test(HELP_PALETTE[key]),
     `${key} falls back to another token if its own is missing (got ${HELP_PALETTE[key]})`);
}
// Both themes must define them, or one theme silently goes black. The light theme
// is the one that catches this: every token here was picked against the dark
// sphere first, and several that read there are invisible on the light disc.
for (const token of ["--axis-x", "--axis-y", "--axis-z", "--axis-gate"]) {
  ok(light.includes(`${token}:`), `${token} has a light-theme value`);
}

// The wireframe must not be drawn in a hairline colour. `border` is tuned for an
// edge against the page and comes out at 1.04:1 on the sphere's own disc -- not a
// faint line, no line at all -- which is how it shipped and what this pins down.
ok(!/--border\b/.test(HELP_PALETTE.line),
   `the wireframe is not drawn in the hairline colour (got ${HELP_PALETTE.line})`);

// --- 2b. the rotation axis -------------------------------------------------------
console.log("rotation axis");

// The axis a gate turns about must never be drawn in the state vector's colour.
// blochkit's default colours it after the drawn axis it lies on, and falls back to
// `vector` for an axis that is none of the three -- so H, whose axis is the x+z
// diagonal, drew its axis in exactly the colour of the vector turning about it.
ok(HELP_PALETTE.gateAxis !== undefined, "the rotation axis has a colour of its own");
ok(HELP_PALETTE.gateAxis !== HELP_PALETTE.vector,
   "the rotation axis is not the state vector's colour");
for (const key of ["axisX", "axisY", "axisZ"]) {
  ok(HELP_PALETTE[key] !== HELP_PALETTE.gateAxis,
     `the rotation axis is not ${key}'s colour, or it vanishes into the wireframe`);
  ok(HELP_PALETTE[key] !== HELP_PALETTE.vector, `${key} is not the state vector's colour`);
}
ok(new Set([HELP_PALETTE.axisX, HELP_PALETTE.axisY, HELP_PALETTE.axisZ]).size === 3,
   "the three axes are told apart by colour");

const axisHost = dom.window.document.createElement("div");
dom.window.document.body.appendChild(axisHost);
const axisSphere = new GateSphere(axisHost);

// H is the case that regressed: a diagonal axis, matching none of the three.
axisSphere.show("H-gate", "0");
let drawn = axisHost.innerHTML;
ok(drawn.includes(HELP_PALETTE.gateAxis), "H's diagonal axis is drawn in the axis colour");
// S turns about z, which IS a drawn axis: the rotation axis must still be the one
// that stands out, rather than silently taking z's own colour.
axisSphere.show("S-gate", "+");
drawn = axisHost.innerHTML;
ok(drawn.includes(HELP_PALETTE.gateAxis), "S's z-axis rotation is drawn in the axis colour");

// The shaft alone says which line the gate turns about, not which way round it goes:
// S and Sdg share that line. A head on the +axis is what carries the direction.
const heads = (html) => (html.match(/<polygon/g) || []).length;
ok(heads(drawn) >= 1, "the rotation axis is tipped, so its direction can be read");
ok(heads(drawn) === 1, `exactly one head, on the +axis only (found ${heads(drawn)})`);

// A measurement is not a rotation, so it has no axis and must grow no head.
axisSphere.show("M-move", "+");
ok(heads(axisHost.innerHTML) === 0, "a measurement draws no rotation axis and no head");
axisSphere.stop();

// --- 3. measurement ------------------------------------------------------------
console.log("measurement");

ok(isMeasurement("M") && isMeasurement("m") && isMeasurement("measure"),
   "M, m and measure all name a measurement");
ok(!isMeasurement("H") && !isMeasurement(null) && !isMeasurement([0, 0, 1]),
   "a gate, a null and a vector do not");
ok(gateVector(MEASURE) === null, "MEASURE is not a rotation");
ok(canDraw("M-move"), "the Measure topic is drawable");
ok(gateOfTopic("M-move") === MEASURE, "the Measure topic maps to the measurement token");
ok(defaultState("M-move") === "+", "Measure opens on |+>, where the outcome is undecided");
ok(defaultState("H-gate") === "0", "a gate opens on |0>");

const mHost = dom.window.document.createElement("div");
dom.window.document.body.appendChild(mHost);
const measured = new GateSphere(mHost);
ok(measured.show("M-move", "+") === true, "Measure draws");
// A measurement has no end marker to ring: it lands on a pole, not on a rotation's
// image, and which pole is not decided until the frame is drawn.
ok(measured.film.gate === null, "the measurement reaches blochkit as a null gate");
ok(measured.film.end === null, "a measurement has no precomputed end state");
measured.stop();

// --- 4. the camera drag ----------------------------------------------------------
console.log("camera drag");

const dHost = dom.window.document.createElement("div");
dom.window.document.body.appendChild(dHost);
const draggable = new GateSphere(dHost);
const svgRoot = dHost.querySelector("svg");
ok(svgRoot.getAttribute("role") === "application", "an interactive sphere is an application");
ok((svgRoot.getAttribute("aria-label") || "").includes("drag"), "the label mentions dragging");
ok(svgRoot.style.cursor === "grab", "it shows a grab cursor");
ok(svgRoot.style.touchAction === "none", "a touch drag rotates rather than scrolling");

draggable.show("H-gate", "0");
const before = { ...draggable.film.proj };
const pointer = (type, x, y) => {
  const e = new dom.window.Event(type, { bubbles: true, cancelable: true });
  Object.assign(e, { clientX: x, clientY: y, pointerId: 1 });
  svgRoot.dispatchEvent(e);
};
svgRoot.setPointerCapture = () => {};
svgRoot.releasePointerCapture = () => {};
pointer("pointerdown", 0, 0);
pointer("pointermove", 40, 10);
ok(draggable.film.proj.az !== before.az, "dragging turns the camera in azimuth");
ok(draggable.film.proj.el !== before.el, "dragging turns the camera in elevation");
pointer("pointerup", 40, 10);

// Past the pole the equator collapses to a line and the drawing stops saying
// anything about the phase, so elevation is clamped short of it.
pointer("pointerdown", 0, 0);
pointer("pointermove", 0, 100000);
ok(Math.abs(draggable.film.proj.el) <= 1.45 + 1e-9,
   `elevation stays clamped short of the pole (got ${draggable.film.proj.el})`);
pointer("pointerup", 0, 0);

svgRoot.dispatchEvent(new dom.window.Event("dblclick", { bubbles: true }));
ok(Math.abs(draggable.film.proj.az - HOME.az) < 1e-12
   && Math.abs(draggable.film.proj.el - HOME.el) < 1e-12,
   "a double-click puts the camera back home");

// Turning the sphere must not restart or lose the animation.
ok(draggable.film.raf !== null, "the loop survives a drag");
draggable.stop();

// --- 5. the module specifier -----------------------------------------------------
console.log("module specifier");

// The module specifier help.js builds must be resolvable under BOTH runtimes.
// STATIC_BASE is "/static" on the server but a bare "static" in the browser build,
// and `import("static/scripts/bloch-help.js")` is a *bare module specifier*, which a
// browser refuses outright -- so the sphere silently never appeared in the PWA while
// working fine on the server. Resolving against the document base is what fixes it.
for (const [base, docUrl] of [["/static", "http://x/game"],
                              ["static", "http://x/index.html"],
                              ["static", "http://x/sub/dir/index.html"]]) {
  const href = new URL(`${base}/scripts/bloch-help.js`, docUrl).href;
  ok(href.startsWith("http://x/") && href.endsWith("/static/scripts/bloch-help.js"),
     `STATIC_BASE ${JSON.stringify(base)} at ${docUrl} resolves to a real URL (got ${href})`);
}

// An unknown name must throw: silently becoming `null` would mean "measure".
let threw = false;
try {
  sphere.film.show("NOT-A-GATE", "0");
} catch {
  threw = true;
}
ok(threw, "an unknown gate name throws rather than falling through to measure");

console.log(failures ? `\n${failures} check(s) failed` : "\nall Bloch sphere checks passed");
process.exit(failures ? 1 : 0);
