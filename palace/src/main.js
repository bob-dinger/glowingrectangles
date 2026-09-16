import * as THREE from 'three';
import { PRESIDENTS, STOPS } from './presidents.js';

// ---------------------------------------------------------------------------
// Layout
//
// The spine is a serpentine of rooms you walk in strict order. Two presidents
// serve non-consecutive terms, so their room is entered TWICE — the president
// who interrupts them lives in a dead-end alcove off that same room. Walking
// it teaches the fact: you go into Cleveland, get interrupted by Harrison,
// and come back out into Cleveland again.
// ---------------------------------------------------------------------------

const ROOM = 20;          // interior width/depth
const WALL = 0.6;
const HEIGHT = 11;
const PITCH = ROOM + 8;   // room centre to room centre, along a leg
const ROW_PITCH = PITCH * 2; // legs are spaced double, leaving a band for alcoves
const DOOR_W = 4.4;
const DOOR_H = 6.0;
const PER_LEG = 8;        // rooms per serpentine leg before turning
const EYE = 1.7;

const roomIndexOf = name => PRESIDENTS.findIndex(p => p.name === name);
const CLEVELAND = roomIndexOf('Grover Cleveland');
const B_HARRISON = roomIndexOf('Benjamin Harrison');
const TRUMP = roomIndexOf('Donald Trump');
const BIDEN = roomIndexOf('Joseph R. Biden');

// Spine order: every room except the two that interrupt a repeated term.
const SPINE = [];
for (const s of STOPS) {
  if (s.roomIndex === B_HARRISON || s.roomIndex === BIDEN) continue;
  if (SPINE[SPINE.length - 1] === s.roomIndex) continue; // skip the re-entry
  SPINE.push(s.roomIndex);
}

// Grid position for each spine slot, snaking back and forth. Legs run along Z
// and step along X, which gives the whole palace a landscape footprint — it
// has to read as one picture in the overhead view.
function spineCell(i) {
  const leg = Math.floor(i / PER_LEG);
  let pos = i % PER_LEG;
  if (leg % 2 === 1) pos = PER_LEG - 1 - pos;
  return { x: leg * ROW_PITCH, z: pos * PITCH };
}

// roomIndex -> world centre
const CENTRE = new Array(PRESIDENTS.length);
SPINE.forEach((ri, i) => { CENTRE[ri] = spineCell(i); });
// Alcoves hang into the empty band between legs, so they never collide with
// the spine no matter where the repeated-term president lands.
CENTRE[B_HARRISON] = { x: CENTRE[CLEVELAND].x - PITCH, z: CENTRE[CLEVELAND].z };
CENTRE[BIDEN] = { x: CENTRE[TRUMP].x - PITCH, z: CENTRE[TRUMP].z };

// Connections: [roomA, roomB]
const LINKS = [];
for (let i = 0; i < SPINE.length - 1; i++) LINKS.push([SPINE[i], SPINE[i + 1]]);
LINKS.push([CLEVELAND, B_HARRISON]);
LINKS.push([TRUMP, BIDEN]);

// ---------------------------------------------------------------------------
// Geometry toolkit handed to each president's `make`
// ---------------------------------------------------------------------------

const geoCache = new Map();
const cached = (key, build) => {
  let g = geoCache.get(key);
  if (!g) { g = build(); geoCache.set(key, g); }
  return g;
};
const mat = (color, o = {}) => new THREE.MeshStandardMaterial({
  color,
  roughness: o.r ?? 0.75,
  metalness: o.m ?? 0.05,
  emissive: o.e ?? 0x000000,
  emissiveIntensity: o.ei ?? 1,
  transparent: o.t !== undefined,
  opacity: o.t ?? 1,
  side: o.side === 2 ? THREE.DoubleSide : THREE.FrontSide,
});
const K = {
  g: () => new THREE.Group(),
  box: (w, h, d, c, o) => new THREE.Mesh(cached(`b${w},${h},${d}`, () => new THREE.BoxGeometry(w, h, d)), mat(c, o)),
  cyl: (rt, rb, h, c, o) => new THREE.Mesh(cached(`c${rt},${rb},${h}`, () => new THREE.CylinderGeometry(rt, rb, h, 20)), mat(c, o)),
  sph: (r, c, o) => new THREE.Mesh(cached(`s${r}`, () => new THREE.SphereGeometry(r, 20, 14)), mat(c, o)),
  cone: (r, h, c, o) => new THREE.Mesh(cached(`n${r},${h}`, () => new THREE.ConeGeometry(r, h, 18)), mat(c, o)),
  tor: (r, t, c, o) => new THREE.Mesh(cached(`t${r},${t}`, () => new THREE.TorusGeometry(r, t, 10, 28)), mat(c, o)),
  at: (m, x, y, z) => { m.position.set(x, y, z); return m; },
  rot: (m, x, y, z) => { m.rotation.set(x, y, z); return m; },
};

// ---------------------------------------------------------------------------
// Wallpaper
//
// Each room gets its own pattern, drawn to a canvas in that room's accent. A
// distinct surface per room is worth real mnemonic money — it gives you a
// second cue for "where am I" beyond the object on the plinth. Patterns are
// assigned by index so consecutive rooms never share one.
// ---------------------------------------------------------------------------

const PAPER = 256;
// Draw a motif nine times so anything crossing an edge reappears on the other
// side — cheap seamless tiling without hand-fitting each pattern.
const wrap9 = (c, draw) => {
  for (let ox = -1; ox <= 1; ox++) for (let oy = -1; oy <= 1; oy++) {
    c.save(); c.translate(ox * PAPER, oy * PAPER); draw(); c.restore();
  }
};

const PAPERS = [
  // broad stripes
  (c, S) => { for (let x = 0; x < S; x += S / 4) c.fillRect(x, 0, S / 9, S); },
  // pinstripe pairs
  (c, S) => { for (let x = 0; x < S; x += S / 8) { c.fillRect(x, 0, 3, S); c.fillRect(x + 9, 0, 1.5, S); } },
  // polka dots, half-drop
  (c, S) => {
    for (let j = 0; j < 4; j++) for (let i = 0; i < 4; i++) {
      const x = i * S / 4 + (j % 2 ? S / 8 : 0) + S / 8, y = j * S / 4 + S / 8;
      wrap9(c, () => { c.beginPath(); c.arc(x, y, S / 26, 0, 7); c.fill(); });
    }
  },
  // harlequin diamonds
  (c, S) => {
    for (let j = -1; j < 4; j++) for (let i = -1; i < 4; i++) {
      if ((i + j) % 2) continue;
      const x = i * S / 3 + S / 6, y = j * S / 3 + S / 6;
      wrap9(c, () => {
        c.beginPath();
        c.moveTo(x, y - S / 6); c.lineTo(x + S / 6, y); c.lineTo(x, y + S / 6); c.lineTo(x - S / 6, y);
        c.closePath(); c.fill();
      });
    }
  },
  // chevron
  (c, S) => {
    c.lineWidth = 5;
    for (let y = -S; y < S * 2; y += S / 5) {
      c.beginPath();
      for (let x = 0; x <= S; x += S / 8) c.lineTo(x, y + (Math.floor(x / (S / 8)) % 2 ? S / 10 : 0));
      c.stroke();
    }
  },
  // tile grid
  (c, S) => { c.lineWidth = 3; for (let i = 0; i <= 4; i++) { const p = i * S / 4; c.beginPath(); c.moveTo(p, 0); c.lineTo(p, S); c.moveTo(0, p); c.lineTo(S, p); c.stroke(); } },
  // diagonal trellis
  (c, S) => {
    c.lineWidth = 3;
    for (let i = -4; i <= 8; i++) {
      const p = i * S / 4;
      c.beginPath(); c.moveTo(p, 0); c.lineTo(p + S, S); c.stroke();
      c.beginPath(); c.moveTo(p, S); c.lineTo(p + S, 0); c.stroke();
    }
  },
  // fish-scale
  (c, S) => {
    c.lineWidth = 3;
    for (let j = 0; j < 5; j++) for (let i = -1; i < 5; i++) {
      const x = i * S / 4 + (j % 2 ? S / 8 : 0), y = j * S / 5;
      wrap9(c, () => { c.beginPath(); c.arc(x, y, S / 8, 0, Math.PI); c.stroke(); });
    }
  },
  // damask medallion
  (c, S) => {
    for (let j = 0; j < 2; j++) for (let i = 0; i < 2; i++) {
      const x = i * S / 2 + (j % 2 ? S / 4 : 0) + S / 4, y = j * S / 2 + S / 4;
      wrap9(c, () => {
        for (let k = 0; k < 8; k++) {
          c.save(); c.translate(x, y); c.rotate(k * Math.PI / 4);
          c.beginPath(); c.ellipse(0, -S / 14, S / 42, S / 15, 0, 0, 7); c.fill();
          c.restore();
        }
        c.beginPath(); c.arc(x, y, S / 34, 0, 7); c.fill();
      });
    }
  },
  // herringbone
  (c, S) => {
    for (let j = -1; j < 6; j++) for (let i = -1; i < 6; i++) {
      const x = i * S / 5, y = j * S / 5 + (i % 2 ? S / 10 : 0);
      c.save(); c.translate(x, y); c.rotate((i % 2 ? -1 : 1) * Math.PI / 4);
      c.fillRect(-S / 14, -3, S / 7, 5); c.restore();
    }
  },
  // crosshatch
  (c, S) => {
    c.lineWidth = 1.4;
    for (let i = -8; i <= 16; i++) {
      const p = i * S / 8;
      c.beginPath(); c.moveTo(p, 0); c.lineTo(p + S, S); c.stroke();
      c.beginPath(); c.moveTo(p, S); c.lineTo(p + S, 0); c.stroke();
    }
  },
  // hexagons
  (c, S) => {
    c.lineWidth = 2.5; const r = S / 8;
    for (let j = -1; j < 6; j++) for (let i = -1; i < 5; i++) {
      const x = i * r * 3 + (j % 2 ? r * 1.5 : 0), y = j * r * 0.87;
      wrap9(c, () => {
        c.beginPath();
        for (let k = 0; k < 6; k++) c.lineTo(x + r * Math.cos(k * Math.PI / 3), y + r * Math.sin(k * Math.PI / 3));
        c.closePath(); c.stroke();
      });
    }
  },
  // waves
  (c, S) => {
    c.lineWidth = 3;
    for (let y = 0; y < S; y += S / 7) {
      c.beginPath();
      for (let x = 0; x <= S; x += 4) c.lineTo(x, y + Math.sin(x / S * Math.PI * 2) * S / 22);
      c.stroke();
    }
  },
  // starburst rosettes
  (c, S) => {
    for (let j = 0; j < 3; j++) for (let i = 0; i < 3; i++) {
      const x = i * S / 3 + S / 6, y = j * S / 3 + S / 6;
      wrap9(c, () => {
        c.lineWidth = 2;
        for (let k = 0; k < 12; k++) {
          c.beginPath(); c.moveTo(x, y);
          c.lineTo(x + Math.cos(k * Math.PI / 6) * S / 9, y + Math.sin(k * Math.PI / 6) * S / 9);
          c.stroke();
        }
      });
    }
  },
];

const paperCache = new Map();
function wallpaper(hue, idx) {
  const key = `${hue}:${idx % PAPERS.length}`;
  if (paperCache.has(key)) return paperCache.get(key);
  const cv = document.createElement('canvas');
  cv.width = cv.height = PAPER;
  const c = cv.getContext('2d');
  const accent = new THREE.Color(hue);
  const dark = new THREE.Color(0x05070b);
  c.fillStyle = '#' + accent.clone().lerp(dark, 0.88).getHexString();
  c.fillRect(0, 0, PAPER, PAPER);
  const ink = '#' + accent.clone().lerp(dark, 0.6).getHexString();
  c.fillStyle = ink; c.strokeStyle = ink;
  PAPERS[idx % PAPERS.length](c, PAPER);
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  paperCache.set(key, t);
  return t;
}

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x07090d);
// Fog sells the enclosure while walking, but it would bury the palace from
// overhead — so it's swapped out with the mode, not left on.
const walkFog = new THREE.Fog(0x07090d, 18, 78);
scene.fog = walkFog;

// Far plane has to clear the overhead camera altitude (~410), not just the room.
const camera = new THREE.PerspectiveCamera(72, innerWidth / innerHeight, 0.1, 1400);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.getElementById('stage').appendChild(renderer.domElement);

scene.add(new THREE.HemisphereLight(0x8899bb, 0x201a14, 0.45));
const ambient = new THREE.AmbientLight(0xffffff, 0.32);
scene.add(ambient);
const headLamp = new THREE.PointLight(0xfff2dd, 22, 34, 1.7);
scene.add(headLamp);
// Lights the whole palace from above in the overview. Kept in the scene at zero
// intensity while walking so the light count — and the shaders — never change.
const sun = new THREE.DirectionalLight(0xfff2e0, 0);
sun.position.set(0.4, 1, 0.25);
scene.add(sun);
// Fixed pool, re-aimed at the nearest rooms each frame so the light count
// never changes and the shaders never recompile mid-walk.
const POOL = Array.from({ length: 4 }, () => {
  const l = new THREE.PointLight(0xffffff, 0, 46, 1.5);
  scene.add(l);
  return l;
});

function numberSign(n, twice) {
  const c = document.createElement('canvas');
  c.width = 512; c.height = 256;
  const x = c.getContext('2d');
  x.fillStyle = '#0b0e14'; x.fillRect(0, 0, 512, 256);
  x.fillStyle = '#e8c98a';
  x.font = 'bold 190px Georgia, serif';
  x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(String(n), 256, 132);
  if (twice) {
    x.fillStyle = '#7f8c9e'; x.font = 'italic 40px Georgia, serif';
    x.fillText('· twice ·', 256, 232);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const rooms = [];     // { group, cx, cz, ri, prop }
const walkRects = []; // { x0, x1, z0, z1 }
const roofs = [];     // hidden while looking down at the palace

// World-space texture tiling: rescale the box UVs by the face's real size and
// offset them by its position, so the paper runs continuously across the wall
// spans either side of a doorway instead of restarting at each segment.
const TILE = 4.5;
function papered(w, h, d, material, uOff, vOff) {
  const g = new THREE.BoxGeometry(w, h, d);
  const uv = g.attributes.uv;
  const su = Math.max(w, d) / TILE, sv = h / TILE;
  for (let i = 0; i < uv.count; i++) {
    uv.setXY(i, uv.getX(i) * su + uOff / TILE, uv.getY(i) * sv + vOff / TILE);
  }
  uv.needsUpdate = true;
  return new THREE.Mesh(g, material);
}

function addWall(group, len, horizontal, offset, doors, wallMat, skirtHex) {
  // Build a wall as spans so doorways are real holes, no CSG needed.
  const cuts = doors.slice().sort((a, b) => a - b);
  const edges = [-len / 2];
  for (const c of cuts) { edges.push(c - DOOR_W / 2, c + DOOR_W / 2); }
  edges.push(len / 2);
  for (let i = 0; i < edges.length; i += 2) {
    const a = edges[i], b = edges[i + 1];
    if (b - a < 0.01) continue;
    const w = b - a, mid = (a + b) / 2;
    const m = papered(horizontal ? w : WALL, HEIGHT, horizontal ? WALL : w, wallMat, a + len / 2, 0);
    m.position.set(horizontal ? mid : offset, HEIGHT / 2, horizontal ? offset : mid);
    group.add(m);
    // Skirting board, split at the doorways for free by reusing these spans.
    const s = K.box(horizontal ? w : WALL * 1.7, 0.95, horizontal ? WALL * 1.7 : w, skirtHex, { r: 0.7 });
    s.position.set(horizontal ? mid : offset, 0.475, horizontal ? offset : mid);
    group.add(s);
  }
  for (const c of cuts) { // lintel over each doorway
    const m = papered(horizontal ? DOOR_W : WALL, HEIGHT - DOOR_H, horizontal ? WALL : DOOR_W,
      wallMat, c - DOOR_W / 2 + len / 2, DOOR_H);
    m.position.set(horizontal ? c : offset, DOOR_H + (HEIGHT - DOOR_H) / 2, horizontal ? offset : c);
    group.add(m);
  }
}

PRESIDENTS.forEach((p, ri) => {
  const { x: cx, z: cz } = CENTRE[ri];
  const group = new THREE.Group();
  group.position.set(cx, 0, cz);
  scene.add(group);

  const accent = new THREE.Color(p.hue);
  const floorTint = accent.clone().lerp(new THREE.Color(0x0d1017), 0.82);

  group.add(K.at(K.box(ROOM, 0.4, ROOM, floorTint.getHex(), { r: 0.9 }), 0, -0.2, 0));
  // Roof and light panel lift away in the overhead view, so it reads as a plan.
  const roof = K.at(K.box(ROOM + WALL * 2, 0.4, ROOM + WALL * 2, 0x0a0d13, { r: 1 }), 0, HEIGHT + 0.2, 0);
  const panel = K.at(K.box(ROOM * 0.55, 0.12, ROOM * 0.55, accent.getHex(), { e: p.hue, ei: 0.85 }), 0, HEIGHT - 0.12, 0);
  group.add(roof, panel);
  roofs.push(roof, panel);

  // Which walls need doorways
  const doors = { n: [], s: [], e: [], w: [] };
  for (const [a, b] of LINKS) {
    if (a !== ri && b !== ri) continue;
    const other = CENTRE[a === ri ? b : a];
    if (other.x > cx) doors.e.push(0);
    else if (other.x < cx) doors.w.push(0);
    else if (other.z > cz) doors.s.push(0);
    else doors.n.push(0);
  }
  const paperMat = new THREE.MeshStandardMaterial({
    map: wallpaper(p.hue, ri), roughness: 0.96, metalness: 0,
  });
  const skirtHex = accent.clone().lerp(new THREE.Color(0x05070b), 0.66).getHex();
  addWall(group, ROOM, true, -ROOM / 2, doors.n, paperMat, skirtHex);
  addWall(group, ROOM, true, ROOM / 2, doors.s, paperMat, skirtHex);
  addWall(group, ROOM, false, ROOM / 2, doors.e, paperMat, skirtHex);
  addWall(group, ROOM, false, -ROOM / 2, doors.w, paperMat, skirtHex);

  // A plinth. The props don't share a common "front" and the approach
  // direction differs room to room, so each turns slowly on a base — which
  // also reads as deliberate museum display rather than an object adrift.
  const PLINTH = 0.55;
  group.add(K.at(K.cyl(5.2, 5.6, PLINTH, floorTint.clone().lerp(accent, 0.12).getHex(), { r: 0.85 }), 0, PLINTH / 2, 0));
  group.add(K.rot(K.at(K.tor(5.3, 0.045, accent.getHex(), { e: p.hue, ei: 0.09 }), 0, PLINTH, 0), Math.PI / 2, 0, 0));

  const prop = p.make(K);
  prop.position.set(0, PLINTH, 0);
  group.add(prop);

  // Ordinal above the doorway, so you can always count where you are.
  for (const term of p.t) {
    const sign = new THREE.Mesh(new THREE.PlaneGeometry(3.2, 1.6),
      new THREE.MeshBasicMaterial({ map: numberSign(term, p.twice) }));
    const idx = p.t.indexOf(term);
    sign.position.set(-6 + idx * 12, 8.2, -ROOM / 2 + WALL);
    group.add(sign);
  }

  const light = new THREE.Vector3(cx, 7, cz);
  rooms.push({ group, cx, cz, light, ri, prop });
  walkRects.push({ x0: cx - ROOM / 2 + 0.7, x1: cx + ROOM / 2 - 0.7, z0: cz - ROOM / 2 + 0.7, z1: cz + ROOM / 2 - 0.7 });
});

// Corridors joining each linked pair
const corridorMat = mat(0x141922, { r: 0.95 });
for (const [a, b] of LINKS) {
  const A = CENTRE[a], B = CENTRE[b];
  const horizontal = A.x !== B.x;
  const mx = (A.x + B.x) / 2, mz = (A.z + B.z) / 2;
  const span = (horizontal ? Math.abs(A.x - B.x) : Math.abs(A.z - B.z)) - ROOM + 1.0;
  const w = horizontal ? span : DOOR_W, d = horizontal ? DOOR_W : span;
  const c = new THREE.Group();
  c.position.set(mx, 0, mz);
  c.add(K.at(K.box(w, 0.4, d, 0x11151d, { r: 0.95 }), 0, -0.2, 0));
  const ceil = new THREE.Mesh(new THREE.BoxGeometry(w, 0.4, d), corridorMat);
  ceil.position.set(0, DOOR_H, 0);
  c.add(ceil);
  roofs.push(ceil);
  for (const s of [-1, 1]) {
    const side = new THREE.Mesh(
      new THREE.BoxGeometry(horizontal ? w : WALL, DOOR_H, horizontal ? WALL : d), corridorMat);
    side.position.set(horizontal ? 0 : s * (DOOR_W / 2), DOOR_H / 2, horizontal ? s * (DOOR_W / 2) : 0);
    c.add(side);
  }
  scene.add(c);
  // Collision volume runs 4 units PAST the geometry at each end so it overlaps
  // the room rects — otherwise there's a hairline gap and you jam in the door.
  const over = 4;
  walkRects.push({
    x0: mx - (horizontal ? w / 2 + over : DOOR_W / 2 - 0.5),
    x1: mx + (horizontal ? w / 2 + over : DOOR_W / 2 - 0.5),
    z0: mz - (horizontal ? DOOR_W / 2 - 0.5 : d / 2 + over),
    z1: mz + (horizontal ? DOOR_W / 2 - 0.5 : d / 2 + over),
  });
}

// The route, drawn on the floor as 46 thin slabs. Segment i joins stop i to
// i+1, so the Cleveland and Trump doubling-back is visible as a spur.
const routeSegs = [];
for (let i = 0; i < STOPS.length - 1; i++) {
  const A = CENTRE[STOPS[i].roomIndex], B = CENTRE[STOPS[i + 1].roomIndex];
  const len = Math.hypot(B.x - A.x, B.z - A.z);
  if (len < 0.5) continue;
  const seg = new THREE.Mesh(
    new THREE.BoxGeometry(len, 0.06, 1.1),
    new THREE.MeshBasicMaterial({ color: 0x4a5364 }));
  seg.position.set((A.x + B.x) / 2, 0.5, (A.z + B.z) / 2);
  seg.rotation.y = -Math.atan2(B.z - A.z, B.x - A.x);
  seg.visible = false;
  seg.userData.stop = i;
  scene.add(seg);
  routeSegs.push(seg);
}

// ---------------------------------------------------------------------------
// Walking
// ---------------------------------------------------------------------------

// The plinth is solid, so you walk *around* each object instead of through it.
// That leaves a ~3.5-unit ambulatory between the plinth and the walls.
const PLINTH_R2 = 5.9 ** 2;
const blockers = rooms.map(r => ({ x: r.cx, z: r.cz }));

const walkable = (x, z) =>
  walkRects.some(r => x > r.x0 && x < r.x1 && z > r.z0 && z < r.z1) &&
  !blockers.some(b => (x - b.x) ** 2 + (z - b.z) ** 2 < PLINTH_R2);

const player = new THREE.Vector3();
let yaw = 0, pitch = 0;
const keys = new Set();
const vel = new THREE.Vector3();

const stage = document.getElementById('stage');
const clampPitch = p => Math.max(-1.35, Math.min(1.35, p));
const isLocked = () => document.pointerLockElement === renderer.domElement;

// Pointer lock is the nice path, but it is REJECTED outright inside a sandboxed
// iframe — which is where this page lives when published. So it's an
// enhancement only: drag-to-look and arrow-key turning always work.
function tryLock() {
  if (!renderer.domElement.requestPointerLock) return;
  try {
    const p = renderer.domElement.requestPointerLock();
    if (p && typeof p.catch === 'function') p.catch(() => {});
  } catch { /* no lock available; drag-to-look covers it */ }
}

let dragging = false, lastMX = 0, lastMY = 0;
stage.addEventListener('mousedown', e => {
  if (mode !== 'walk' || menuOpen) return;
  dragging = true; lastMX = e.clientX; lastMY = e.clientY;
  document.body.classList.add('grabbing');
});
addEventListener('mouseup', () => {
  dragging = false;
  document.body.classList.remove('grabbing');
});
stage.addEventListener('click', () => {
  if (!menuOpen && mode === 'walk') tryLock();
});
addEventListener('mousemove', e => {
  if (mode !== 'walk') return;
  if (isLocked()) {
    yaw -= e.movementX * 0.0022;
    pitch = clampPitch(pitch - e.movementY * 0.0022);
  } else if (dragging) {
    yaw -= (e.clientX - lastMX) * 0.005;
    pitch = clampPitch(pitch - (e.clientY - lastMY) * 0.005);
    lastMX = e.clientX; lastMY = e.clientY;
  }
});
addEventListener('keydown', e => {
  if (e.code === 'Tab' || e.code === 'KeyM') { e.preventDefault(); toggleMenu(); return; }
  if (e.code === 'KeyO') { e.preventDefault(); if (mode === 'walk') enterOverview(); return; }
  if (e.code === 'KeyQ') { quiz = !quiz; refreshHud(); return; }
  if (e.code === 'Space' && quiz) { e.preventDefault(); revealed = true; refreshHud(); return; }
  keys.add(e.code);
});
addEventListener('keyup', e => keys.delete(e.code));
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  if (mode === 'overview') {
    const fit = overheadFit();
    camera.position.set(fit.x, fit.y, MID.z);
    layoutPins();
  }
});

// ---------------------------------------------------------------------------
// Progress along the 47 stops
// ---------------------------------------------------------------------------

let stopIdx = 0;
let quiz = false, revealed = false, menuOpen = false;
const visited = new Set(JSON.parse(localStorage.getItem('palace.visited') || '[]'));

// Drop the player on the near side of a room, facing the prop with the exit
// beyond it — so arriving always frames the object you came to remember.
function placeAt(i) {
  const here = CENTRE[STOPS[i].roomIndex];
  const nxt = STOPS[i + 1] ? CENTRE[STOPS[i + 1].roomIndex] : null;
  const prv = STOPS[i - 1] ? CENTRE[STOPS[i - 1].roomIndex] : null;
  let dx = 0, dz = -1;
  if (nxt && (nxt.x !== here.x || nxt.z !== here.z)) { dx = nxt.x - here.x; dz = nxt.z - here.z; }
  else if (prv) { dx = here.x - prv.x; dz = here.z - prv.z; }
  const len = Math.hypot(dx, dz) || 1;
  dx /= len; dz /= len;
  player.set(here.x - dx * 7, EYE, here.z - dz * 7);
  yaw = Math.atan2(-dx, -dz);
  pitch = 0;
}

function currentRoom() {
  let best = 0, bd = Infinity;
  for (const r of rooms) {
    const d = (r.cx - player.x) ** 2 + (r.cz - player.z) ** 2;
    if (d < bd) { bd = d; best = r.ri; }
  }
  return best;
}

function updateProgress() {
  const ri = currentRoom();
  // Advance or retreat only to an adjacent stop, so a room entered twice
  // reads as two different moments in the sequence.
  if (stopIdx + 1 < STOPS.length && STOPS[stopIdx + 1].roomIndex === ri) stopIdx++;
  else if (stopIdx > 0 && STOPS[stopIdx - 1].roomIndex === ri) stopIdx--;
  else if (STOPS[stopIdx].roomIndex !== ri) {
    const jump = STOPS.findIndex(s => s.roomIndex === ri);
    if (jump >= 0) stopIdx = jump;
  }
  if (!visited.has(stopIdx)) {
    visited.add(stopIdx);
    localStorage.setItem('palace.visited', JSON.stringify([...visited]));
  }
}

const $ = id => document.getElementById(id);

function refreshHud() {
  const s = STOPS[stopIdx];
  const show = !quiz || revealed;
  $('ord').textContent = s.term;
  $('name').textContent = show ? s.p.name : '— — —';
  $('years').textContent = show ? s.p.years : '';
  $('peg').textContent = show ? s.p.peg : (quiz ? 'name the president' : '');
  $('why').textContent = show ? s.p.why : '';
  $('hud').classList.toggle('hidden-answer', !show);
  $('twice').style.display = s.p.twice ? '' : 'none';
  $('progress').textContent = `${visited.size} / ${STOPS.length} visited`;
  $('bar').style.width = `${(visited.size / STOPS.length) * 100}%`;
  $('quizflag').style.display = quiz ? '' : 'none';
}

function toggleMenu() {
  menuOpen = !menuOpen;
  // Must be an explicit value: `#menu { display:none }` out-specifies the
  // .scrim grid rule, so clearing the inline style would re-hide the panel.
  $('menu').style.display = menuOpen ? 'grid' : 'none';
  if (menuOpen) document.exitPointerLock();
}

function buildMenu() {
  const list = $('list');
  STOPS.forEach((s, i) => {
    const el = document.createElement('button');
    el.className = 'row' + (s.p.twice ? ' twice' : '');
    el.innerHTML = `<span class="n">${s.term}</span><span class="nm">${s.p.name}</span><span class="pg">${s.p.peg}</span>`;
    el.onclick = () => {
      stopIdx = i;
      placeAt(i);
      revealed = false;
      toggleMenu();
      refreshHud();
    };
    list.appendChild(el);
  });
}

// ---------------------------------------------------------------------------
// Overhead view
//
// The same camera, flown up and pointed down, rather than a separate 2D map —
// so descending into a room is one continuous move and you keep the mapping
// between the plan and the walk.
// ---------------------------------------------------------------------------

const OVER_FOV = 34;
const bounds = CENTRE.reduce((b, c) => ({
  x0: Math.min(b.x0, c.x - ROOM), x1: Math.max(b.x1, c.x + ROOM),
  z0: Math.min(b.z0, c.z - ROOM), z1: Math.max(b.z1, c.z + ROOM),
}), { x0: Infinity, x1: -Infinity, z0: Infinity, z1: -Infinity });
const MID = { x: (bounds.x0 + bounds.x1) / 2, z: (bounds.z0 + bounds.z1) / 2 };

// Fit the palace into the viewport MINUS the reading panel on the left, then
// shift the camera so it centres in what's actually left over.
function overheadFit() {
  const gutter = innerWidth < 760 ? 0 : 400;
  const halfV = Math.tan((OVER_FOV / 2) * Math.PI / 180);
  const usableAspect = Math.max(0.3, (innerWidth - gutter) / innerHeight);
  const needZ = (bounds.z1 - bounds.z0) / 2 / halfV;
  const needX = (bounds.x1 - bounds.x0) / 2 / (halfV * usableAspect);
  const y = Math.max(needZ, needX) * 1.06;
  const worldW = 2 * y * halfV * camera.aspect;
  return { y, x: MID.x - (gutter / innerWidth) * worldW / 2 };
}

// Screen-up is -Z, so the palace reads with stop 1 at the top-left.
const overQuat = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0, 'YXZ'));

let mode = 'overview';
let tween = null;
const pins = [];

function applyMode(m) {
  const over = m !== 'walk';
  scene.fog = over ? null : walkFog;
  roofs.forEach(r => { r.visible = !over; });
  routeSegs.forEach(s => { s.visible = over; });
  sun.intensity = over ? 2.1 : 0;
  ambient.intensity = over ? 0.62 : 0.32;
  headLamp.intensity = over ? 0 : 22;
  POOL.forEach(l => { l.intensity = over ? 0 : 19; });
  if (over) rooms.forEach(r => { r.group.visible = true; });
  $('map').style.display = m === 'overview' ? '' : 'none';
  $('overhud').style.display = m === 'overview' ? '' : 'none';
  $('hud').style.display = m === 'walk' ? '' : 'none';
  $('legend').style.display = m === 'walk' ? '' : 'none';
  document.body.classList.toggle('overview', m === 'overview');
  document.body.classList.toggle('walking', m === 'walk');
}

function enterOverview() {
  mode = 'overview';
  tween = null;
  document.exitPointerLock();
  camera.fov = OVER_FOV;
  const fit = overheadFit();
  camera.position.set(fit.x, fit.y, MID.z);
  camera.quaternion.copy(overQuat);
  camera.updateProjectionMatrix();
  applyMode('overview');
  routeSegs.forEach(s => s.material.color.set(visited.has(s.userData.stop + 1) ? 0xe8c98a : 0x5b6880));
  layoutPins();
}

function descend(i) {
  stopIdx = i;
  placeAt(i);
  const to = player.clone();
  const toQuat = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, yaw, 0, 'YXZ'));
  tween = {
    t: 0,
    fromPos: camera.position.clone(), toPos: to,
    fromQuat: camera.quaternion.clone(), toQuat,
  };
  mode = 'descend';
  applyMode('descend');
  revealed = false;
  refreshHud();
  tryLock(); // must fire on the click itself — a request after the tween is too late

}

function layoutPins() {
  // project() reads matrixWorldInverse, which only the renderer refreshes — so
  // after moving the camera by hand it must be brought up to date explicitly.
  camera.updateMatrixWorld(true);
  const v = new THREE.Vector3();
  pins.forEach((pin, i) => {
    const c = CENTRE[STOPS[i].roomIndex];
    // Nudge the two doubled stops apart so both pins stay clickable.
    const dup = STOPS[i].p.twice ? (STOPS.findIndex(s => s.p === STOPS[i].p) === i ? -4.5 : 4.5) : 0;
    v.set(c.x + dup, 0, c.z + dup).project(camera);
    pin.style.left = `${(v.x * 0.5 + 0.5) * innerWidth}px`;
    pin.style.top = `${(-v.y * 0.5 + 0.5) * innerHeight}px`;
    pin.classList.toggle('done', visited.has(i));
  });
}

function buildPins() {
  const map = $('map');
  STOPS.forEach((s, i) => {
    const pin = document.createElement('button');
    pin.className = 'pin' + (s.p.twice ? ' twice' : '');
    pin.textContent = s.term;
    pin.onclick = () => descend(i);
    pin.onmouseenter = () => {
      $('hovname').textContent = s.p.name;
      $('hovpeg').textContent = s.p.peg;
      $('hovwhy').textContent = s.p.why;
    };
    map.appendChild(pin);
    pins.push(pin);
  });
}

// ---------------------------------------------------------------------------
// Loop
// ---------------------------------------------------------------------------

const clock = new THREE.Clock();
let lastRoom = -1;

function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);

  if (mode === 'overview') { renderer.render(scene, camera); return; }

  if (mode === 'descend') {
    tween.t = Math.min(1, tween.t + dt / 1.35);
    const t = tween.t;
    const e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    camera.position.lerpVectors(tween.fromPos, tween.toPos, e);
    camera.quaternion.slerpQuaternions(tween.fromQuat, tween.toQuat, e);
    camera.fov = OVER_FOV + (72 - OVER_FOV) * e;
    camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    if (tween.t >= 1) {
      mode = 'walk';
      tween = null;
      pitch = 0;
      lastRoom = -1;
      applyMode('walk');
    }
    return;
  }

  const speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 15 : 6.5;
  const fwd = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
  const str = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0);
  // Left/right arrows TURN rather than strafe, so the palace is fully walkable
  // with the keyboard alone even where no mouse-look is available.
  yaw -= ((keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0)) * dt * 1.9;

  const want = new THREE.Vector3(
    Math.sin(yaw) * -fwd + Math.cos(yaw) * str, 0,
    Math.cos(yaw) * -fwd - Math.sin(yaw) * str);
  if (want.lengthSq() > 0) want.normalize().multiplyScalar(speed);
  vel.lerp(want, 1 - Math.pow(0.0008, dt));

  // Axis-separated so you slide along walls instead of sticking.
  const nx = player.x + vel.x * dt;
  if (walkable(nx, player.z)) player.x = nx; else vel.x = 0;
  const nz = player.z + vel.z * dt;
  if (walkable(player.x, nz)) player.z = nz; else vel.z = 0;

  camera.position.copy(player);
  camera.rotation.set(pitch, yaw, 0, 'YXZ');
  headLamp.position.copy(player);

  // Aim the light pool at the nearest rooms; hide everything far away.
  const near = rooms
    .map(r => ({ r, d: (r.cx - player.x) ** 2 + (r.cz - player.z) ** 2 }))
    .sort((a, b) => a.d - b.d);
  near.forEach(({ r, d }, i) => { r.group.visible = i < 7; if (r.prop) r.prop.rotation.y += dt * 0.12; });
  POOL.forEach((l, i) => {
    const t = near[i];
    l.position.set(t.r.cx, 7.5, t.r.cz);
    // Tint, don't flood — a fully saturated room light blows the floor out.
    l.color.set(PRESIDENTS[t.r.ri].hue).lerp(new THREE.Color(0xfff4e2), 0.55);
    l.intensity = 19;
  });

  updateProgress();
  const r = currentRoom();
  if (r !== lastRoom) { lastRoom = r; revealed = false; refreshHud(); }

  renderer.render(scene, camera);
}

// Debug handle: lets a headless flood-fill prove every room is reachable.
window.__palace = { walkable, CENTRE, STOPS, PRESIDENTS, ROOM, player, cam: camera };

buildMenu();
buildPins();
placeAt(0);
refreshHud();
enterOverview();
frame();

// The intro sits over the overhead view, so the palace is already behind it.
$('begin').onclick = () => { $('intro').style.display = 'none'; };
$('startwalk').onclick = () => descend(0);
$('closemenu').onclick = toggleMenu;
