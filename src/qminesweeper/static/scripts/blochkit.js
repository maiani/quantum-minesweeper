/**
 * blochkit — a Bloch sphere you can draw, drag and animate.
 *
 * ONE FILE, NO IMPORTS, NO BUILD STEP. Copy it into any project, `import` it from a
 * module script, and it works: it touches nothing but the DOM nodes you hand it.
 * That is deliberate. It was extracted from a game, and a library that drags its
 * former neighbours along with it does not get reused.
 *
 *   import { BlochSphere } from "./blochkit.js";
 *   const sphere = new BlochSphere(document.querySelector("#sphere"));
 *   sphere.update([0, 0, 1]);            // |0>, the north pole
 *
 *   import { GateAnimation } from "./blochkit.js";
 *   const film = new GateAnimation(document.querySelector("#tip"));
 *   film.show([Math.PI / 2, 0, 0], [0, 0, 1]);   // a 90-degree rotation about x
 *   film.show(null, [0, 0.6, 0.8]);              // null = measure and collapse
 *   film.show("H", "|0>");                       // or name the gate and the ket
 *   film.show("M", "+");                         // "M" is a spelling of that null
 *
 * CONVENTIONS. A state is a **unit Bloch vector** `[x, y, z]` as a plain array of
 * three numbers — no complex amplitudes, no density matrices, no numpy-alike. A gate
 * is an **axis-angle vector** `v = angle * axis`, so its length is the rotation angle
 * in radians and its direction is the axis. `[Math.PI, 0, 0]` is X; `[0, 0, Math.PI]`
 * is Z. North is |0>, south is |1>, and `pNorth(r) = (1 + z) / 2` is the Born rule.
 *
 * VOCABULARY. Anywhere a state or a gate is taken, a **name** is taken too: the six
 * cardinal kets (`"0" "1" "+" "-" "i" "-i"`, with or without `|` and `>`) and the
 * named one-qubit Cliffords (`"X" "Y" "Z" "H" "S" "Sdg" "SX" "SXdg" "SY" "SYdg"`,
 * case-insensitive). See `STATES` and `GATES`, which are also readable directly.
 *
 * COLOUR. Every colour comes from a palette object (see DEFAULT_PALETTE) and every
 * value is passed to SVG untouched, so a plain `"#E2503A"`, a `"var(--flag)"` and a
 * `"color-mix(...)"` all work. Pass `{ palette: { vector: "var(--accent)" } }` to
 * override one key; the rest fall back to the defaults.
 *
 * MOTION. Everything respects `prefers-reduced-motion: reduce` by showing the final
 * state instead of animating to it.
 */

const SVG_NS = "http://www.w3.org/2000/svg";

/** Create an SVG element; null and undefined attributes are skipped. */
function svg(name, attrs = {}) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs)) {
    if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  return node;
}

const prefersStill = () =>
  globalThis.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;

// --- the maths ------------------------------------------------------------
// Plain arrays and scalar arithmetic. At three components a vector library costs more
// than it saves, and this has to run inside a requestAnimationFrame loop.

const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1],
                         a[2] * b[0] - a[0] * b[2],
                         a[0] * b[1] - a[1] * b[0]];

/** Rotate `r` by `angle` radians about unit `axis` (Rodrigues' formula). */
export function rotateAround(r, axis, angle) {
  const c = Math.cos(angle), s = Math.sin(angle);
  const k = cross(axis, r), d = dot(axis, r) * (1 - c);
  return [r[0] * c + k[0] * s + axis[0] * d,
          r[1] * c + k[1] * s + axis[1] * d,
          r[2] * c + k[2] * s + axis[2] * d];
}

/** Rotate `r` by the axis-angle vector `v`. A zero-length `v` is the identity. */
export function rotate(v, r) {
  const angle = Math.hypot(v[0], v[1], v[2]);
  if (angle < 1e-15) return r.slice();
  return rotateAround(r, [v[0] / angle, v[1] / angle, v[2] / angle], angle);
}

// --- the standard vocabulary ----------------------------------------------
// The named Clifford gates and the six cardinal states, so a caller with a gate
// *name* and a ket *name* does not have to re-derive the trigonometry. Nothing here
// is specific to any application: these are the textbook definitions, in the same
// axis-angle and Bloch-vector conventions the rest of the file uses.

const HALF_PI = Math.PI / 2;
const DIAGONAL = Math.PI / Math.SQRT2;    // H turns by pi about (x + z)/sqrt(2)

/**
 * What each named gate does to a Bloch vector, as an axis-angle vector.
 *
 * The correspondence is the standard one: the gate exp(-i θ n·σ / 2) turns the Bloch
 * vector by θ about n, right-handed. Global phase is invisible here, which is why a
 * single entry covers every phase convention for the same gate.
 *
 * Only the one-qubit gates appear. A Bloch sphere draws one qubit, so a two-qubit
 * gate has no entry rather than a wrong one.
 */
export const GATES = {
  X: [Math.PI, 0, 0],
  Y: [0, Math.PI, 0],
  Z: [0, 0, Math.PI],
  H: [DIAGONAL, 0, DIAGONAL],
  S: [0, 0, HALF_PI],
  Sdg: [0, 0, -HALF_PI],
  SX: [HALF_PI, 0, 0],
  SXdg: [-HALF_PI, 0, 0],
  SY: [0, HALF_PI, 0],
  SYdg: [0, -HALF_PI, 0],
};

/**
 * The name that means "measure" rather than "rotate".
 *
 * A measurement is not a rotation, so it has no entry in `GATES` and `gateVector`
 * returns null for it -- which is also what an unknown name returns. `isMeasurement`
 * is the discriminator between those two, and anywhere a gate is taken, this name is
 * accepted as a spelling of the null that means measure: `show("M", r)` and
 * `show(null, r)` are the same call.
 */
export const MEASURE = "M";

/** Whether `name` names a measurement. Accepts "M" and "measure", in any case. */
export const isMeasurement = (name) =>
  typeof name === "string" && ["m", "measure"].includes(name.trim().toLowerCase());

/** The six cardinal states, keyed by the bare ket name. North is |0>, south is |1>. */
export const STATES = {
  "0": [0, 0, 1],
  "1": [0, 0, -1],
  "+": [1, 0, 0],
  "-": [-1, 0, 0],
  i: [0, 1, 0],
  "-i": [0, -1, 0],
};

/**
 * Look a name up in `table`, ignoring case and any ket decoration around it, and
 * return a fresh copy of the vector — or null if the name is not one it holds.
 *
 * Case-insensitivity is what lets "Sdg", "SDG" and "sdg" all reach the same gate:
 * every project spells the daggered gates differently and none of them is wrong.
 * `|0>`, `|0⟩` and `0` likewise all name the north pole.
 */
function lookup(table, name) {
  if (Array.isArray(name)) return name;            // already a vector; pass it through
  if (typeof name !== "string") return null;
  const bare = name.replace(/^\|/, "").replace(/[>⟩]$/, "").trim();
  const key = Object.keys(table).find((k) => k.toLowerCase() === bare.toLowerCase());
  return key === undefined ? null : table[key].slice();
}

/** The rotation a named gate performs, or null. Accepts a vector unchanged. */
export const gateVector = (name) => lookup(GATES, name);

/** The Bloch vector a named ket points at, or null. Accepts a vector unchanged. */
export const stateVector = (name) => lookup(STATES, name);

/**
 * Resolve a name the drawing cannot do without, and throw if it is not one we know.
 *
 * The widgets below resolve names through this rather than through `lookup` directly,
 * because their fallbacks are all worse than an exception: an unknown *gate* name
 * would silently become the null that means "measure", and an unknown *state* would
 * leave a wireframe with no vector in it. Both look like the drawing works.
 */
function demand(table, name, kind) {
  const v = lookup(table, name);
  if (v === null) {
    throw new Error(`blochkit: unknown ${kind} ${JSON.stringify(name)}; ` +
                    `expected one of ${Object.keys(table).join(", ")}, or an [x, y, z]`);
  }
  return v;
}

/** The Born rule: the probability that a z-measurement gives |0>. */
export const pNorth = (r) => (1 + r[2]) / 2;

/** Azimuth in degrees. The phase scores nothing and decides everything. */
export const phaseDeg = (r) => (Math.atan2(r[1], r[0]) * 180) / Math.PI;

/** Length of the equatorial component: how far from a pole the state is. */
export const equatorialReach = (r) => Math.hypot(r[0], r[1]);

/**
 * One projective measurement in z: +1 for |0> (north), -1 for |1> (south).
 *
 * `rng` must return a float in [0, 1) as `Math.random` does; pass a seeded generator
 * to make a demo reproducible. The comparison is `rng() < p`, which is exact at both
 * ends: p = 0 can never draw north because nothing is below zero, and p = 1 always
 * draws it because `Math.random` never reaches one.
 */
export function sampleCollapse(r, rng = Math.random) {
  return rng() < pNorth(r) ? 1 : -1;
}

/**
 * A measurement outcome that is redrawn once per repetition of a loop.
 *
 * The point of a looping measurement animation is that it is a *different* sample
 * each time round -- that is the only thing on screen that shows the reader the
 * outcome is not a property of the state. So the outcome is cached, and the cache is
 * dropped when the loop rolls over.
 *
 * It is also dropped when the probability changes, which is not the same condition
 * and is why this is a class rather than a modulo. An animation whose state is
 * updated under it mid-cycle would otherwise keep showing an outcome drawn from the
 * distribution the state used to have.
 */
export class RepeatedCollapse {
  constructor({ period = 2050, rng = Math.random } = {}) {
    this.period = period;
    this.rng = rng;
    this.cycle = null;
    this.p = null;
    this.outcome = 1;
  }

  /** The outcome in force `elapsed` ms into the loop, for the state `r`. */
  at(elapsed, r) {
    const cycle = Math.floor(elapsed / this.period);
    const p = pNorth(r);
    if (cycle !== this.cycle || p !== this.p) {
      this.cycle = cycle;
      this.p = p;
      this.outcome = sampleCollapse(r, this.rng);
    }
    return this.outcome;
  }
}

// --- the picture ----------------------------------------------------------

export const HOME = { az: -0.62, el: 0.32 };
export const EL_LIMIT = 1.45;          // short of the pole, where the equator degenerates
const REFERENCE_RADIUS = 62;           // sizes are quoted here and scaled from it

export const AXES = [
  { key: "x", dir: [1, 0, 0], label: "x", colour: "axisX" },
  { key: "y", dir: [0, 1, 0], label: "y", colour: "axisY" },
  { key: "z", dir: [0, 0, 1], label: "z", colour: "axisZ" },
];

/**
 * Every colour and face the drawing uses. Override any subset.
 *
 * The defaults are a dark palette, because a wireframe sphere on white needs a
 * different set of opacities rather than the same ones inverted -- if you are on a
 * light background, set `face`, `line` and `muted` and check the dimmed far half.
 */
export const DEFAULT_PALETTE = {
  face: "#1D3B20",        // the disc the wireframe sits on
  line: "#3B4E2E",        // equator, meridian, silhouette
  muted: "#C3D6B8",       // drop-line to the equatorial plane, orbit guides
  axisX: "#E08A63",
  axisY: "#63C48C",
  axisZ: "#7FA6E8",
  vector: "#E2503A",      // the state itself
  target: "#4FD18B",      // where a gate would leave it
  // The axis a gate turns about. Null takes the colour of whichever drawn axis it
  // lies on, and falls back to `vector` for an axis that is none of the three --
  // which is a real hazard, because that is the state vector's own colour and the
  // two are then indistinguishable exactly when the picture is least obvious. Set
  // this to give the rotation axis a colour of its own; a palette whose three axes
  // share one colour wants it too, or the axis vanishes into the wireframe.
  gateAxis: null,
  north: "#E2503A",       // |0>
  south: "#FFFFFF",       // |1>
  pole: "#C9A227",        // the flag pole, when the flag marker is on
  mono: 'ui-monospace, SFMono-Regular, Menlo, "IBM Plex Mono", monospace',
};

const withPalette = (p) => ({ ...DEFAULT_PALETTE, ...p });

/** Orthographic projection from a viewing direction given as azimuth and elevation. */
export class Projection {
  constructor({ radius = REFERENCE_RADIUS, az = HOME.az, el = HOME.el, palette } = {}) {
    this.radius = radius;
    this.scale = radius / REFERENCE_RADIUS;
    this.az = az;
    this.el = el;
    this.palette = withPalette(palette);
  }

  /** Project a Bloch vector to screen coordinates, and report its depth. */
  project(v) {
    const { az, el } = this;
    const right = [-Math.sin(az), Math.cos(az), 0];
    const up = [-Math.cos(az) * Math.sin(el), -Math.sin(az) * Math.sin(el), Math.cos(el)];
    const toward = cross(right, up);          // points at the viewer
    return { x: dot(v, right) * this.radius, y: -dot(v, up) * this.radius,
             z: dot(v, toward) };
  }

  /** Split a sampled 3-D curve into the part nearer the viewer and the part behind. */
  path(points) {
    const near = [], far = [];
    let wasNear = null;
    for (const point of points) {
      const p = this.project(point);
      const isNear = p.z >= 0;
      const target = isNear ? near : far;
      // start a new sub-path when the curve crosses the silhouette, or the two halves
      // get joined by a chord straight across the sphere
      target.push(`${isNear === wasNear ? "L" : "M"}${p.x.toFixed(2)} ${p.y.toFixed(2)}`);
      wasNear = isNear;
    }
    return { near: near.join(""), far: far.join("") };
  }

  /** A full circle, as `point(t)` for t over a turn, scaled off the unit sphere. */
  ring(point, scale = 1, steps = 96) {
    const points = [];
    for (let i = 0; i <= steps; i++) {
      points.push(point((i / steps) * Math.PI * 2).map((c) => c * scale));
    }
    return this.path(points);
  }

  line(a, b, attrs) {
    return svg("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, ...attrs });
  }

  text(at, content, { size = 10.5, ...attrs } = {}) {
    const node = svg("text", {
      x: at.x, y: at.y, "text-anchor": "middle",
      "font-size": (size * this.scale).toFixed(2),
      "font-family": this.palette.mono, "font-weight": 600, ...attrs,
    });
    node.textContent = content;
    return node;
  }
}

/**
 * A triangular head at the projected point `at`, pointing away from the centre.
 *
 * Screen-space, not 3-D: the shaft it caps is already a projected line from the
 * origin, so the head only has to agree with that line on the page. Building it in
 * 3-D and projecting it would leave it disagreeing with the shaft by a fraction of a
 * degree for no visible gain.
 *
 * Returns nothing when the projected point sits too close to the centre, which is
 * what happens when the axis points nearly at or away from the viewer. There is no
 * meaningful direction to point in then, and a head drawn end-on reads as a blob.
 */
function arrowhead(at, size, attrs) {
  const len = Math.hypot(at.x, at.y);
  if (len < Math.max(1e-6, size * 0.6)) return [];
  const ux = at.x / len, uy = at.y / len;      // outward along the shaft
  const px = -uy, py = ux;                     // and across it
  const baseX = at.x - ux * size, baseY = at.y - uy * size;
  const half = size * 0.42;
  const points = [
    [at.x, at.y],
    [baseX + px * half, baseY + py * half],
    [baseX - px * half, baseY - py * half],
  ];
  return [svg("polygon", {
    points: points.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" "),
    ...attrs,
  })];
}

/** Name a rotation axis, and colour it, when it is one of the three drawn. */
export function namedAxis(n, palette) {
  const pal = withPalette(palette);
  for (const axis of AXES) {
    for (const sign of [1, -1]) {
      if (dot(n, axis.dir) * sign > 0.9995) {
        return { name: `${sign > 0 ? "+" : "−"}${axis.label}`,
                 colour: pal[axis.colour] };
      }
    }
  }
  return { name: `(${n.map((c) => c.toFixed(2)).join(", ")})`, colour: pal.vector };
}

/**
 * The sphere itself: the disc, the equator, one meridian, two latitude parallels, the
 * three axes and the two poles. Returns the far half and the near half separately --
 * parts behind the sphere are dimmed rather than hidden, because on a wireframe "which
 * way is it pointing" is otherwise genuinely ambiguous.
 *
 * `labels` names the poles. The default is ket notation; pass `null` for none.
 */
export function wireframe(proj, { labels = ["|0⟩", "|1⟩"] } = {}) {
  const pal = proj.palette;
  const back = [], front = [];

  back.push(svg("circle", {
    cx: 0, cy: 0, r: proj.radius, fill: pal.face, stroke: pal.line, "stroke-width": 1,
  }));

  for (const [point, dash] of [
    [(t) => [Math.cos(t), Math.sin(t), 0], null],
    [(t) => [Math.cos(t), 0, Math.sin(t)], "3 3"],
  ]) {
    const { near, far } = proj.ring(point);
    back.push(svg("path", { d: far, fill: "none", stroke: pal.line,
                            "stroke-width": 1, "stroke-dasharray": dash,
                            "stroke-opacity": 0.6 }));
    front.push(svg("path", { d: near, fill: "none", stroke: pal.line,
                             "stroke-width": 1.2, "stroke-dasharray": dash }));
  }

  // A pair of latitude parallels, one on each side of the equator. Unlike the equator
  // and the meridian, nobody is meant to read these as *anything* -- they carry no
  // axis, no phase, no label -- their only job is to keep the disc from reading as
  // flat. Dotted, so they stay a step under the two great circles even at full
  // strength, but not so faint they disappear against the face.
  for (const h of [0.5, -0.5]) {
    const r = Math.sqrt(1 - h * h);
    const { near, far } = proj.ring((t) => [r * Math.cos(t), r * Math.sin(t), h]);
    back.push(svg("path", { d: far, fill: "none", stroke: pal.line,
                            "stroke-width": 1, "stroke-dasharray": "2 3",
                            "stroke-opacity": 0.45 }));
    front.push(svg("path", { d: near, fill: "none", stroke: pal.line,
                             "stroke-width": 1, "stroke-dasharray": "2 3",
                             "stroke-opacity": 0.65 }));
  }

  // each axis is two half-shafts, so the one going away from the viewer is dimmer --
  // gently: which half that is flips every time the camera turns past the silhouette,
  // and a strong swing there reads as a highlight jumping between axes rather than as
  // depth, so the near/far difference is kept small on purpose.
  for (const axis of AXES) {
    const colour = pal[axis.colour];
    for (const sign of [1, -1]) {
      const end = proj.project(axis.dir.map((c) => c * sign));
      const near = end.z >= 0;
      (near ? front : back).push(proj.line({ x: 0, y: 0 }, end, {
        stroke: colour, "stroke-width": near ? 1.2 : 1,
        "stroke-opacity": near ? 0.85 : 0.65,
        "stroke-dasharray": near ? null : "2 2",
      }));
    }
    front.push(proj.text(proj.project(axis.dir.map((c) => c * 1.17)), axis.label,
                         { fill: colour, size: 10 }));
  }

  if (labels) {
    front.push(proj.text(proj.project([0, 0, 1.3]), labels[0],
                         { fill: pal.north, size: 11 }));
    front.push(proj.text(proj.project([0, 0, -1.34]), labels[1],
                         { fill: pal.south, size: 11 }));
  }

  return { back, front };
}

// --- the widget -----------------------------------------------------------

const DRAG_SPEED = 0.011;              // radians per pixel

/**
 * Turn the camera by dragging, and put it back on a double-click.
 *
 * Factored out of BlochSphere so that GateAnimation can take the same gesture. On a
 * wireframe, "which way is that pointing" is genuinely ambiguous from a single fixed
 * angle -- dimming the far half only narrows it -- and turning the thing by hand is
 * most of the answer. A drawing you can interrogate beats a better-chosen viewpoint.
 *
 * `onChange` is called after every change to `proj`; the caller redraws however it
 * needs to. Nothing here touches the drawing itself.
 */
function bindCameraDrag(root, proj, onChange) {
  root.style.cursor = "grab";
  root.style.touchAction = "none";     // a drag must rotate, not scroll the page

  let last = null;
  root.addEventListener("pointerdown", (event) => {
    last = { x: event.clientX, y: event.clientY };
    root.setPointerCapture(event.pointerId);
    root.style.cursor = "grabbing";
    event.preventDefault();
  });
  root.addEventListener("pointermove", (event) => {
    if (!last) return;
    proj.az += (event.clientX - last.x) * DRAG_SPEED;
    // clamped short of the pole: at the pole the equator collapses to a line and
    // the picture stops saying anything about the phase
    proj.el = Math.max(-EL_LIMIT,
                       Math.min(EL_LIMIT, proj.el + (event.clientY - last.y) * DRAG_SPEED));
    last = { x: event.clientX, y: event.clientY };
    onChange();
  });
  const release = (event) => {
    if (!last) return;
    last = null;
    root.releasePointerCapture?.(event.pointerId);
    root.style.cursor = "grab";
  };
  root.addEventListener("pointerup", release);
  root.addEventListener("pointercancel", release);
  root.addEventListener("dblclick", () => {
    proj.az = HOME.az;
    proj.el = HOME.el;
    onChange();
  });
}

/**
 * A Bloch sphere in a container, showing one state, optionally draggable.
 *
 * The view angle is the widget's only state beyond the vector itself, and everything
 * is re-projected from it on every draw, so there is no second representation to keep
 * in step.
 */
export class BlochSphere {
  /**
   * `dragVector: false` (the default) spins the camera around a vector you cannot
   * otherwise move — right when the state is something else's to set. `true` drags
   * the vector itself across the surface, trackball-style, relative to wherever the
   * camera currently is.
   *
   * `flag: true` plants a small flag where the vector meets the surface, tinted from
   * `north` to `south` by z. It is off by default: it is a nice way to show which
   * pole a state currently favours, and it is also a flag on your sphere.
   */
  constructor(container, {
    interactive = true, dragVector = false, flag = false, radius = 62,
    palette, label = "Bloch sphere", poleLabels,
  } = {}) {
    this.proj = new Projection({ radius, palette });
    this.pal = this.proj.palette;
    this.poleLabels = poleLabels;
    this.v = [1, 0, 0];
    this.dragVector = dragVector;
    this.flag = flag;
    this.homeV = null;

    const viewbox = radius * 1.58;     // room for the axis labels outside the sphere
    const root = svg("svg", {
      viewBox: `${-viewbox} ${-viewbox} ${2 * viewbox} ${2 * viewbox}`,
      role: interactive ? "application" : "img",
      "aria-label": label + (interactive
        ? (dragVector ? "; drag the state, double-click to reset"
                      : "; drag to rotate, double-click to reset")
        : ""),
    });
    root.style.width = "100%";
    root.style.display = "block";
    if (interactive) {
      root.style.cursor = "grab";
      root.style.touchAction = "none";      // a drag must rotate, not scroll the page
    }

    // Two layers only: everything is re-projected on every draw, so splitting further
    // would just be more things to keep in step.
    this.back = svg("g");     // the far half of the wireframe and axes
    this.front = svg("g");    // the near half, the state vector, the labels
    root.append(this.back, this.front);

    this.root = root;
    container.replaceChildren(root);
    if (interactive) this.#bindDrag(root);
    this.#draw();
  }

  /** The camera, so another drawing can be made from the angle the reader is already
   *  looking from. Turning this sphere turns the next one with it. */
  get view() { return { az: this.proj.az, el: this.proj.el }; }

  /**
   * Show `v`, either as an `[x, y, z]` or as a ket name such as `"+"` or `"|0>"`.
   * The first vector shown becomes the double-click reset target.
   */
  update(v) {
    v = demand(STATES, v, "state");
    if (!this.homeV) this.homeV = [...v];
    this.v = v;
    this.#draw();
  }

  #draw() {
    const { back, front } = wireframe(this.proj, { labels: this.poleLabels });
    const proj = this.proj, pal = this.pal;

    const v = this.v;
    const tip = proj.project(v);
    const foot = proj.project([v[0], v[1], 0]);
    const behind = tip.z < 0;

    // the circle of states with this much equatorial reach: what any rotation about
    // z can reach without changing the score
    const reachRing = proj.ring((t) => [Math.cos(t), Math.sin(t), 0], equatorialReach(v));
    front.push(svg("path", { d: reachRing.near, fill: "none", stroke: pal.vector,
                             "stroke-width": 1, "stroke-opacity": 0.45 }));
    back.push(svg("path", { d: reachRing.far, fill: "none", stroke: pal.vector,
                            "stroke-width": 1, "stroke-opacity": 0.2 }));

    const layer = behind ? back : front;
    layer.push(proj.line(tip, foot, { stroke: pal.muted, "stroke-width": 1,
                                      "stroke-dasharray": "2 3" }));
    layer.push(proj.line({ x: 0, y: 0 }, tip, {
      stroke: pal.vector, "stroke-width": behind ? 2.2 : 2.6, "stroke-linecap": "round",
      "stroke-opacity": behind ? 0.65 : 1,
    }));
    layer.push(svg("circle", { cx: tip.x, cy: tip.y, r: behind ? 4.2 : 5,
                               fill: pal.vector, "fill-opacity": behind ? 0.65 : 1 }));

    if (this.flag) layer.push(...this.#flag(tip, v[2], behind));

    this.back.replaceChildren(...back);
    this.front.replaceChildren(...front);
  }

  /**
   * A flag planted where the vector meets the surface, blending from `north` to
   * `south` with z so it shows which side the state currently favours without a
   * legend. Sized off the sphere's own radius so it stays inside the viewBox margin.
   */
  #flag(tip, z, behind) {
    const proj = this.proj, pal = this.pal;
    const out = Math.hypot(tip.x, tip.y) || 1;
    const ox = tip.x / out, oy = tip.y / out;
    const poleLen = proj.radius * 0.55, flyLen = proj.radius * 0.26;
    const top = { x: tip.x + ox * poleLen, y: tip.y + oy * poleLen };
    const mid = { x: tip.x + ox * poleLen * 0.5, y: tip.y + oy * poleLen * 0.5 };
    const fly = { x: mid.x - oy * flyLen, y: mid.y + ox * flyLen };
    const opacity = behind ? 0.4 : 1;
    return [
      svg("line", { x1: tip.x, y1: tip.y, x2: top.x, y2: top.y,
                    stroke: pal.pole, "stroke-width": 2.2, "stroke-linecap": "round",
                    "stroke-opacity": opacity }),
      svg("polygon", {
        points: `${top.x.toFixed(2)},${top.y.toFixed(2)} `
              + `${fly.x.toFixed(2)},${fly.y.toFixed(2)} `
              + `${mid.x.toFixed(2)},${mid.y.toFixed(2)}`,
        fill: `color-mix(in srgb, ${pal.north} ${(50 + z * 50).toFixed(1)}%, ${pal.south})`,
        "fill-opacity": opacity,
      }),
    ];
  }

  /**
   * Camera drag is the shared gesture, so it comes from `bindCameraDrag`. Only the
   * vector-drag mode is implemented here, because only this widget has a vector of
   * its own to drag.
   */
  #bindDrag(root) {
    if (!this.dragVector) {
      bindCameraDrag(root, this.proj, () => this.#draw());
      return;
    }

    root.style.cursor = "grab";
    root.style.touchAction = "none";
    let last = null;
    root.addEventListener("pointerdown", (event) => {
      last = { x: event.clientX, y: event.clientY };
      root.setPointerCapture(event.pointerId);
      root.style.cursor = "grabbing";
      event.preventDefault();
    });
    root.addEventListener("pointermove", (event) => {
      if (!last) return;
      const dx = event.clientX - last.x, dy = event.clientY - last.y;
      // trackball-style: drag relative to wherever the camera currently is
      const { az, el } = this.proj;
      const right = [-Math.sin(az), Math.cos(az), 0];
      const up = [-Math.cos(az) * Math.sin(el), -Math.sin(az) * Math.sin(el),
                  Math.cos(el)];
      let v = rotateAround(this.v, up, dx * DRAG_SPEED);
      v = rotateAround(v, right, -dy * DRAG_SPEED);
      const mag = Math.hypot(v[0], v[1], v[2]);
      this.v = v.map((c) => c / mag);
      last = { x: event.clientX, y: event.clientY };
      this.#draw();
    });
    const release = (event) => {
      if (!last) return;
      last = null;
      root.releasePointerCapture?.(event.pointerId);
      root.style.cursor = "grab";
    };
    root.addEventListener("pointerup", release);
    root.addEventListener("pointercancel", release);
    root.addEventListener("dblclick", () => {
      if (this.homeV) this.v = [...this.homeV];   // the sphere itself never moved
      this.#draw();
    });
  }
}

// --- the animation --------------------------------------------------------

const ease = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);

/**
 * What a gate does to a state, on a loop: the vector swept around that gate's own
 * axis, from where the state is now to where the gate would leave it. Pass a null
 * gate and it measures instead — the state sits there, then collapses onto a pole.
 *
 * Three things stay on screen for the whole loop: the start (dimmed), the end (ringed)
 * and the full circle the vector orbits. The question is usually "does this help me",
 * which is the difference between two points rather than the path between them — but
 * the path is what makes a phase gate legible, because it is the only picture in which
 * "moves nothing, changes everything" looks like anything at all.
 *
 * The moving vector is drawn above the whole wireframe rather than sorted into it, and
 * dimmed when it goes round the back. Getting that exactly right costs a layer split
 * per frame and buys nothing: opacity is what the eye reads as depth here.
 */
export class GateAnimation {
  /**
   * `interactive: true` lets the reader turn the camera, exactly as on a
   * BlochSphere. It is off by default because this widget is often a small inline
   * tip that should not be capturing pointer events; turn it on wherever the
   * drawing is large enough to be worth interrogating.
   */
  constructor(container, {
    radius = 54, palette, poleLabels, rng = Math.random,
    interactive = false,
    sweep = 1150,        // ms spent rotating
    hold = 900,          // ms resting on the result before looping
    fade = 300,          // ms of that hold spent fading out, so the restart reads
    arcSteps = 56,       //   as a rewind rather than a glitch
    label = "What this gate does to the state",
  } = {}) {
    this.proj = new Projection({ radius, palette });
    this.pal = this.proj.palette;
    this.poleLabels = poleLabels;
    this.sweep = sweep;
    this.period = sweep + hold;
    this.fade = fade;
    this.arcSteps = arcSteps;
    this.collapse = new RepeatedCollapse({ period: this.period, rng });

    const viewbox = radius * 1.52;
    this.root = svg("svg", {
      viewBox: `${-viewbox} ${-viewbox} ${2 * viewbox} ${2 * viewbox}`,
      role: interactive ? "application" : "img",
      "aria-label": label + (interactive ? "; drag to rotate, double-click to reset" : ""),
    });
    this.root.style.width = "100%";
    this.root.style.display = "block";

    this.scene = svg("g");
    this.moving = svg("g");
    this.root.append(this.scene, this.moving);
    container.replaceChildren(this.root);
    this.container = container;

    this.raf = null;
    this.t0 = 0;
    this.elapsed = 0;

    // The static scene is only redrawn when `show` is called, so a camera change has
    // to redraw it explicitly. While the loop is running the next frame repaints the
    // moving half anyway; while it is stopped -- paused, or reduced-motion -- nothing
    // would repaint at all, so replay the frame the reader is looking at.
    if (interactive) {
      bindCameraDrag(this.root, this.proj, () => {
        if (this.start) {
          this.#scene();
          if (this.raf === null) this.#frame(this.elapsed);
        }
      });
    }
  }

  /**
   * @param gate    the axis-angle rotation vector, or a gate name such as `"H"` or
   *                `"Sdg"`, or null to measure
   * @param start   the state now, as a vector or a ket name such as `"+"` or `"|0>"`
   * @param view    optional camera, so this can match a sphere the reader is looking at
   * @param restart false to carry on the current loop when only `start` changed, so an
   *                update under an open animation does not jump back to the beginning
   */
  show(gate, start, view = null, restart = true) {
    if (view) { this.proj.az = view.az; this.proj.el = view.el; }
    // Only null and the measurement name mean measure; any other unrecognised name
    // must throw rather than quietly fall through to it -- see `demand`.
    gate = gate === null || isMeasurement(gate) ? null : demand(GATES, gate, "gate");
    start = demand(STATES, start, "state");
    this.start = start;
    this.gate = gate;
    this.angle = gate ? Math.hypot(gate[0], gate[1], gate[2]) : 0;
    this.axis = this.angle > 1e-9 ? gate.map((c) => c / this.angle) : [0, 0, 1];
    this.end = gate ? rotate(gate, start) : null;
    this.#scene();

    if (prefersStill()) {              // no loop: show the answer, which is the end
      this.stop();
      this.#frame(this.sweep);
      return;
    }
    if (restart || this.raf === null) this.t0 = performance.now();
    if (this.raf === null) this.raf = requestAnimationFrame((t) => this.#tick(t));
  }

  stop() {
    if (this.raf !== null) cancelAnimationFrame(this.raf);
    this.raf = null;
  }

  #tick(now) {
    this.raf = requestAnimationFrame((t) => this.#tick(t));
    this.#frame(now - this.t0);
  }

  /** The static half: wireframe, the gate's axis, the orbit, and both endpoints. */
  #scene() {
    const proj = this.proj, pal = this.pal;
    const { back, front } = wireframe(proj, { labels: this.poleLabels });

    if (this.gate) {
      // The axis the rotation turns about, drawn as two half-shafts like the axes
      // themselves so the half going away stays behind the sphere. Where the gate
      // turns about a drawn axis this lands on top of it in its own colour and simply
      // makes it the bright one, which is exactly the right picture.
      const colour = pal.gateAxis ?? namedAxis(this.axis, pal).colour;
      for (const sign of [1, -1]) {
        const end = proj.project(this.axis.map((c) => c * sign * 1.06));
        const near = end.z >= 0;
        const layer = near ? front : back;
        layer.push(proj.line({ x: 0, y: 0 }, end, {
          stroke: colour, "stroke-width": near ? 2.3 : 1.8,
          "stroke-opacity": near ? 0.9 : 0.5, "stroke-linecap": "round",
        }));
        // Only the positive half is tipped. A bare shaft names the line the gate
        // turns about but not which way round it goes, and those are different
        // gates: S and Sdg share this line. The head is what the right-hand rule
        // is read from, so it has to sit on the +axis and nowhere else.
        if (sign > 0) {
          layer.push(...arrowhead(end, proj.radius * 0.14, {
            fill: colour, "fill-opacity": near ? 0.9 : 0.5,
          }));
        }
      }

      // the whole circle the vector rides, so the swept arc reads as part of a path
      const orbit = proj.path(this.#orbit(0, Math.PI * 2, 96));
      back.push(svg("path", { d: orbit.far, fill: "none", stroke: pal.muted,
                              "stroke-width": 1, "stroke-opacity": 0.22,
                              "stroke-dasharray": "2 3" }));
      front.push(svg("path", { d: orbit.near, fill: "none", stroke: pal.muted,
                               "stroke-width": 1, "stroke-opacity": 0.4,
                               "stroke-dasharray": "2 3" }));
    }

    this.#marker(back, front, this.start, pal.muted, false);
    if (this.end) this.#marker(back, front, this.end, pal.target, true);
    if (!this.gate) {
      // A measurement has no path and two possible answers, so both are drawn as
      // candidates, sized by the Born rule that is about to choose between them.
      for (const sign of [1, -1]) {
        const p = sign > 0 ? pNorth(this.start) : 1 - pNorth(this.start);
        const at = proj.project([0, 0, sign]);
        const colour = sign > 0 ? pal.north : pal.south;
        front.push(svg("circle", {
          cx: at.x, cy: at.y, r: 2.5 + 4 * p,
          fill: colour, "fill-opacity": 0.25, stroke: colour, "stroke-width": 1.4,
        }));
      }
    }

    this.scene.replaceChildren(...back, ...front);
  }

  /** Sample the orbit R_n(theta) r0 over an angle range. */
  #orbit(from, to, steps) {
    const points = [];
    for (let i = 0; i <= steps; i++) {
      const theta = from + ((to - from) * i) / steps;
      points.push(rotateAround(this.start, this.axis, theta));
    }
    return points;
  }

  /**
   * One endpoint: a shaft to the surface and a dot. Three things have to stay telling
   * apart at a glance — where the state was, where it is, and where this gate would
   * leave it — so the end is a ring wide enough for the flier to land inside it
   * without covering it.
   */
  #marker(back, front, v, colour, ring) {
    const proj = this.proj;
    const at = proj.project(v);
    const behind = at.z < 0;
    const layer = behind ? back : front;
    layer.push(proj.line({ x: 0, y: 0 }, at, {
      stroke: colour, "stroke-width": 1.6, "stroke-linecap": "round",
      "stroke-opacity": behind ? 0.35 : 0.5,
      "stroke-dasharray": ring ? "3 2.5" : null,
    }));
    layer.push(svg("circle", {
      cx: at.x, cy: at.y, r: ring ? 6 : 3.6,
      fill: ring ? "none" : colour, stroke: ring ? colour : "none",
      "stroke-width": 2, "fill-opacity": behind ? 0.6 : 1,
      "stroke-opacity": behind ? 0.6 : 1,
    }));
  }

  /** The moving half, for one instant of the loop. */
  #frame(elapsed) {
    this.elapsed = elapsed;          // so a camera drag can repaint a stopped loop
    const proj = this.proj, pal = this.pal;
    const t = elapsed % this.period;
    const alpha = 1 - Math.max(0, (t - (this.period - this.fade)) / this.fade);
    const nodes = [];

    if (this.gate) {
      const theta = this.angle * ease(Math.min(1, t / this.sweep));
      const v = rotateAround(this.start, this.axis, theta);
      const arc = proj.path(this.#orbit(0, theta, this.arcSteps));
      for (const [d, opacity] of [[arc.far, 0.3], [arc.near, 0.85]]) {
        nodes.push(svg("path", { d, fill: "none", stroke: pal.target,
                                 "stroke-width": 2, "stroke-linecap": "round",
                                 "stroke-opacity": opacity * alpha }));
      }
      nodes.push(...this.#flier(v, alpha));
    } else {
      // A measurement: the state sits there while the clock runs, then collapses onto
      // one pole. Instantly -- it is not a rotation, and drawing it as one would be a
      // lie about the only genuinely non-unitary moment there is. A fresh outcome is
      // drawn once per repetition, so watching the loop is watching the distribution.
      const outcome = this.collapse.at(elapsed, this.start);
      const collapsed = t >= this.sweep;
      const v = collapsed ? [0, 0, outcome] : this.start;
      if (!collapsed) {
        const pulse = (t % 600) / 600;             // a ring closing in: measuring
        const at = proj.project(this.start);
        nodes.push(svg("circle", {
          cx: at.x, cy: at.y, r: 4 + 9 * (1 - pulse), fill: "none",
          stroke: pal.vector, "stroke-width": 1.4,
          "stroke-opacity": 0.5 * pulse * alpha,
        }));
      }
      nodes.push(...this.#flier(v, alpha,
        collapsed ? (outcome > 0 ? pal.north : pal.south) : pal.vector));
    }

    this.moving.replaceChildren(...nodes);
  }

  /** The vector in flight: bright in front, gently dimmed when it goes round the back. */
  #flier(v, alpha, colour = this.pal.vector) {
    const at = this.proj.project(v);
    const behind = at.z < 0;
    const depth = behind ? 0.65 : 1;
    return [
      this.proj.line({ x: 0, y: 0 }, at, {
        stroke: colour, "stroke-width": behind ? 2.2 : 2.6, "stroke-linecap": "round",
        "stroke-opacity": depth * alpha,
      }),
      svg("circle", { cx: at.x, cy: at.y, r: behind ? 3.6 : 4.4, fill: colour,
                      "fill-opacity": depth * alpha }),
    ];
  }
}
