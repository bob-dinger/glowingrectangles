import * as THREE from 'three';
import { BLOCKS, ALL } from './places.js';

// ===========================================================================
// THE SPEC — feet throughout.
// ===========================================================================
const WALKWAY  = 14;   // ft — the path you walk. No roadway; this is a promenade.
const DEPTH    = 34;   // ft — how deep the buildings run back from the frontage
const EDGE     = 3;    // ft — the low wall on your right
const CROSS    = 24;   // ft — gap between blocks. These ARE the chunk markers.
const EYE      = 5.6;
const SPEED    = 18;   // ft/s — whole palace in ~75 s
// ===========================================================================

const $ = id => document.getElementById(id);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const mix = (a, b, t) => a + (b - a) * t;

// --- lay the route out --------------------------------------------------------
// One leg per block, turning at each cross street so the whole palace fits a
// screen in plan. Turns are stronger memory markers than straight cross streets.
const DIRS = { '+x': [1, 0], '+z': [0, 1], '-x': [-1, 0], '-z': [0, -1] };
// left of travel, in plan: rotate the heading -90 degrees
const LEFT = { '+x': [0, -1], '+z': [1, 0], '-x': [0, 1], '-z': [-1, 0] };

let cx = 0, cz = 0;
const SEGMENTS = [];   // per place: centre of frontage, heading, left normal
BLOCKS.forEach((blk, bi) => {
  const [dx, dz] = DIRS[blk.dir];
  const [lx, lz] = LEFT[blk.dir];
  blk.start = [cx, cz];
  blk.heading = blk.dir;
  blk.places.forEach(p => {
    const midT = p.w / 2;
    SEGMENTS.push({
      p, blk,
      // frontage centre, on the building line
      fx: cx + dx * midT, fz: cz + dz * midT,
      dx, dz, lx, lz,
      // Rotation that maps local +Z onto the walkway side — i.e. the OPPOSITE
      // of "left", since the buildings sit on the left and the walk is beside
      // them. Getting this from the travel direction instead points the depth
      // down the street and you end up inside a facade.
      face: Math.atan2(-lx, -lz),
    });
    cx += dx * p.w; cz += dz * p.w;
  });
  blk.end = [cx, cz];
  blk.len = Math.hypot(blk.end[0] - blk.start[0], blk.end[1] - blk.start[1]);
  if (bi < BLOCKS.length - 1) { cx += dx * CROSS; cz += dz * CROSS; }
});
const ROUTE_LEN = BLOCKS.reduce((a, b) => a + b.len, 0) + CROSS * (BLOCKS.length - 1);

// --- scene --------------------------------------------------------------------
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xa8c0d4);
const baseFog = new THREE.Fog(0xa8c0d4, 300, 900);
scene.fog = baseFog;

const camera = new THREE.PerspectiveCamera(64, innerWidth / innerHeight, 0.4, 4000);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
$('stage').appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.62));
scene.add(new THREE.HemisphereLight(0xd0e2f2, 0x4a4636, 0.8));
const sun = new THREE.DirectionalLight(0xfff4e4, 1.6);
sun.position.set(-200, 340, 160);
scene.add(sun);

const world = new THREE.Group();
scene.add(world);

const M = new Map();
const mat = (c, r = 0.94) => {
  const k = `${c}|${r}`;
  if (!M.has(k)) M.set(k, new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: 0 }));
  return M.get(k);
};
const bx = (g, w, h, d, c, x, y, z, r) => {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(c, r));
  m.position.set(x, y, z); g.add(m); return m;
};
const cy = (g, rt, rb, h, c, x, y, z, seg = 12) => {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), mat(c));
  m.position.set(x, y, z); g.add(m); return m;
};

// ---------------------------------------------------------------------------
// Massing. Local space: +Z faces the walkway, origin on the frontage line at
// ground. Each form exists to produce a DIFFERENT OUTLINE.
// ---------------------------------------------------------------------------
const ROOF = 0x59554e, DARK = 0x3f3b36, GLASS = 0x9fc4d8;

function massing(p) {
  const g = new THREE.Group();
  const w = p.w - 2, h = p.h, d = DEPTH, c = p.c;
  const body = (hh = h) => bx(g, w, hh, d, c, 0, hh / 2, -d / 2);

  switch (p.form) {
    case 'flat': body(); bx(g, w + 1.5, 1.6, d + 1.5, ROOF, 0, h + 0.8, -d / 2); break;
    case 'pole': body(); bx(g, w + 1.5, 1.4, d + 1.5, ROOF, 0, h + 0.7, -d / 2);
      cy(g, 1.1, 1.1, 9, 0xe8e4dc, w / 2 - 1.5, 9, 1.2, 8); break;
    case 'canopy': body(h * 0.8);
      bx(g, w + 6, 1, 10, 0xb8483a, 0, h * 0.8, 4); break;
    case 'stepped': body(h * 0.72);
      bx(g, w * 0.74, h * 0.16, d, c, 0, h * 0.8, -d / 2);
      bx(g, w * 0.46, h * 0.16, d, c, 0, h * 0.94, -d / 2); break;
    case 'marquee': body();
      bx(g, w + 4, 4, 12, 0xf0d060, 0, h * 0.42, 5);
      bx(g, 6, h * 0.7, 3, 0xf0d060, 0, h * 0.95, 3); break;
    case 'gable': body(h * 0.62);
      for (let i = 0; i < 9; i++) {
        const t = i / 8, ww = w * (1 - t);
        bx(g, ww, h * 0.05, d, ROOF, 0, h * 0.62 + t * h * 0.38, -d / 2);
      } break;
    case 'glass': body(h * 0.35);
      for (let i = 0; i < 8; i++) {
        const t = i / 7;
        bx(g, w * (1 - t * 0.55), h * 0.09, d, GLASS, 0, h * 0.35 + t * h * 0.62, -d / 2);
      } break;
    case 'corner': body();
      cy(g, w * 0.3, w * 0.3, h * 0.45, c, w / 2 - w * 0.28, h + h * 0.2, 0.5, 10);
      cy(g, w * 0.34, 0.1, 6, ROOF, w / 2 - w * 0.28, h + h * 0.45 + 3, 0.5, 10); break;
    case 'spire': body(h * 0.62);
      bx(g, w * 0.34, h * 0.5, w * 0.34, c, -w * 0.26, h * 0.85, 2);
      cy(g, 0.4, w * 0.2, h * 0.7, ROOF, -w * 0.26, h * 1.45, 2, 6); break;
    case 'belfry': body();
      bx(g, w * 0.22, 7, w * 0.22, c, 0, h + 3.5, -3);
      cy(g, 0.3, w * 0.16, 6, ROOF, 0, h + 9, -3, 6); break;
    case 'portico': body();
      for (let i = 0; i < 5; i++) cy(g, 1.4, 1.4, h * 0.8, 0xe4dfd2, -w / 2 + 3 + i * (w - 6) / 4, h * 0.4, 3.5, 10);
      bx(g, w + 3, 2.4, 9, 0xe4dfd2, 0, h * 0.86, 2); break;
    case 'columns': body();
      for (let i = 0; i < 4; i++) cy(g, 1.8, 1.8, h * 0.9, 0xd8d2c2, -w / 2 + 4 + i * (w - 8) / 3, h * 0.45, 3, 12);
      bx(g, w + 2, 3.5, 8, 0xd8d2c2, 0, h * 0.95 + 1, 2); break;
    case 'flagpole': body(); bx(g, w + 1.5, 1.4, d + 1.5, ROOF, 0, h + 0.7, -d / 2);
      cy(g, 0.35, 0.35, 22, 0xe8e4dc, 0, h + 11, 2, 6);
      bx(g, 7, 4.5, 0.2, 0xb8483a, 3.6, h + 19, 2); break;
    case 'dome': body(h * 0.66);
      cy(g, w * 0.32, w * 0.38, h * 0.1, c, 0, h * 0.7, -d / 2, 16);
      const dm = new THREE.Mesh(new THREE.SphereGeometry(w * 0.34, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(0xcfd4d0));
      dm.position.set(0, h * 0.75, -d / 2); g.add(dm);
      cy(g, 0.3, 0.3, h * 0.16, ROOF, 0, h * 0.75 + w * 0.34 + h * 0.08, -d / 2, 6); break;
    case 'clock': body();
      bx(g, w * 0.3, h * 0.55, w * 0.3, c, w * 0.22, h + h * 0.27, -4);
      cy(g, w * 0.11, w * 0.11, 0.6, 0xf4f0e4, w * 0.22, h + h * 0.42, -4 + w * 0.16, 14);
      cy(g, 0.2, w * 0.17, 6, ROOF, w * 0.22, h + h * 0.55 + 3, -4, 6); break;
    case 'hosetower': body();
      bx(g, w * 0.24, h * 0.6, w * 0.24, DARK, w / 2 - w * 0.17, h + h * 0.3, -6);
      bx(g, w * 0.66, h * 0.6, 1, DARK, -w * 0.13, h * 0.3, 0.4); break;
    case 'shed': body(h);
      for (let i = 0; i < 8; i++) {
        const t = i / 7;
        bx(g, w, 0.9, d * (1 - t), ROOF, 0, h + t * 5, -d * (1 - t) / 2);
      }
      bx(g, w * 0.6, h * 0.7, 1, DARK, 0, h * 0.35, 0.4); break;
    case 'lattice':
      for (const [a, b] of [[-1, -1], [1, -1], [-1, 1], [1, 1]])
        cy(g, 0.7, 0.7, h * 0.72, 0x8a8a86, a * w * 0.28, h * 0.36, -d / 2 + b * w * 0.28, 6);
      for (let i = 1; i < 5; i++) bx(g, w * 0.62, 0.7, w * 0.62, 0x8a8a86, 0, h * 0.72 * i / 5, -d / 2);
      cy(g, w * 0.42, w * 0.42, h * 0.2, c, 0, h * 0.82, -d / 2, 14);
      cy(g, w * 0.2, w * 0.44, h * 0.1, c, 0, h * 0.95, -d / 2, 14); break;
    case 'sawtooth': body(h * 0.7);
      for (let i = 0; i < 4; i++) {
        const zz = -d + i * (d / 4) + d / 8;
        bx(g, w, h * 0.3, d / 8, ROOF, 0, h * 0.85, zz);
        bx(g, w, h * 0.22, 0.6, GLASS, 0, h * 0.8, zz + d / 8);
      } break;
    case 'silo':
      for (let i = 0; i < 3; i++)
        cy(g, w * 0.16, w * 0.16, h, c, -w * 0.3 + i * w * 0.3, h / 2, -d / 2, 14);
      for (let i = 0; i < 3; i++)
        cy(g, 0.4, w * 0.17, h * 0.12, ROOF, -w * 0.3 + i * w * 0.3, h + h * 0.06, -d / 2, 14); break;
    case 'chimney': body(h * 0.7);
      cy(g, w * 0.1, w * 0.14, h * 0.95, 0x6a5f56, -w * 0.3, h * 0.48 + h * 0.35, -d * 0.75, 10); break;
    case 'longlow': body(h);
      bx(g, w + 8, 1.2, d * 0.55, ROOF, 0, h + 4.5, 2);
      for (const a of [-1, 1]) cy(g, 0.5, 0.5, 4.5, DARK, a * (w / 2 + 2), h + 2.2, 2, 6); break;
    case 'drum':
      cy(g, w * 0.42, w * 0.42, h, c, 0, h / 2, -d / 2, 18);
      for (let i = 0; i < 3; i++) {
        const t = new THREE.Mesh(new THREE.TorusGeometry(w * 0.43, 0.5, 6, 20), mat(0x4a5252));
        t.rotation.x = Math.PI / 2; t.position.set(0, h * (i + 1) / 4, -d / 2); g.add(t);
      } break;
    case 'conveyor': body(h * 0.5);
      const cv = bx(g, w * 0.9, 1.4, 26, 0x5f5a54, 0, h * 0.72, -d * 0.4);
      cv.rotation.x = -0.42;
      bx(g, w * 0.5, h * 0.35, w * 0.5, DARK, 0, h * 0.66, -d * 0.85); break;
    case 'arch':
      for (const a of [-1, 1]) bx(g, w * 0.16, h, w * 0.3, c, a * w * 0.38, h / 2, -4);
      bx(g, w * 0.9, h * 0.16, w * 0.3, c, 0, h + h * 0.08, -4);
      for (const a of [-1, 1]) cy(g, 0.2, w * 0.09, h * 0.2, ROOF, a * w * 0.38, h + h * 0.2, -4, 6); break;
    case 'pavilion':
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2;
        cy(g, 0.7, 0.7, h * 0.6, 0xe0d8c0, Math.cos(a) * w * 0.34, h * 0.3, -d / 2 + Math.sin(a) * w * 0.34, 8);
      }
      cy(g, w * 0.05, w * 0.46, h * 0.4, c, 0, h * 0.8, -d / 2, 14);
      bx(g, w * 0.8, 0.7, w * 0.8, 0xc0b49a, 0, 0.35, -d / 2); break;
    case 'fountain':
      cy(g, w * 0.46, w * 0.48, 2, 0xb0aca2, 0, 1, -d / 2, 18);
      cy(g, w * 0.4, w * 0.4, 0.5, 0x5f9ac0, 0, 2.1, -d / 2, 18);
      cy(g, w * 0.1, w * 0.14, h * 0.7, c, 0, h * 0.35 + 2, -d / 2, 12);
      cy(g, w * 0.24, 0.2, 1.4, 0xc0bcb2, 0, h * 0.72 + 2, -d / 2, 14); break;
    case 'frame':
      for (const a of [-1, 1]) for (const b of [-1, 1])
        cy(g, 0.5, 0.5, h, c, a * w * 0.36, h / 2, -d / 2 + b * 7, 6);
      bx(g, w * 0.8, 0.8, 0.8, c, 0, h, -d / 2 - 7);
      bx(g, w * 0.8, 0.8, 0.8, c, 0, h, -d / 2 + 7);
      bx(g, 0.8, 0.8, 15, c, -w * 0.36, h, -d / 2);
      bx(g, w * 0.5, 0.8, 8, 0xf0c060, w * 0.12, h * 0.45, -d / 2); break;
    case 'cage':
      for (let i = 0; i < 10; i++) {
        const a = (i / 10) * Math.PI * 2;
        cy(g, 0.32, 0.32, h, c, Math.cos(a) * w * 0.4, h / 2, -d / 2 + Math.sin(a) * w * 0.4, 5);
      }
      const cg = new THREE.Mesh(new THREE.SphereGeometry(w * 0.4, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2), mat(c));
      cg.position.set(0, h, -d / 2); g.add(cg); break;
    case 'pond':
      cy(g, w * 0.48, w * 0.48, 1.4, 0x6a6458, 0, 0.7, -d / 2, 20);
      cy(g, w * 0.44, w * 0.44, 0.5, 0x4f8fb4, 0, 1.5, -d / 2, 20);
      bx(g, 0.4, 8, 0.4, 0xd8d4cc, -w * 0.1, 5.5, -d / 2 + 3);
      bx(g, 4.5, 5, 0.2, 0xf0ece4, -w * 0.1 + 2, 6.5, -d / 2 + 3); break;
    case 'arcade':
      for (let i = 0; i < 5; i++) {
        const zz = -d + 4 + i * 7;
        for (const a of [-1, 1]) cy(g, 0.45, 0.45, h, c, a * w * 0.32, h / 2, zz, 6);
        bx(g, w * 0.7, 0.6, 1.2, c, 0, h, zz);
      } break;
    case 'archspan':
      for (let i = 0; i < 11; i++) {
        const t = i / 10, a = Math.sin(t * Math.PI);
        bx(g, w / 11, 1.6, 12, c, -w / 2 + w * t + w / 22, 2 + a * h * 0.7, -d / 2);
      }
      for (const s of [-1, 1]) bx(g, 2, 6, 12, c, s * w * 0.46, 3, -d / 2); break;
    case 'crane':
      cy(g, w * 0.2, w * 0.26, h * 0.18, c, 0, h * 0.09, -d / 2, 10);
      for (const a of [-1, 1]) for (const b of [-1, 1])
        cy(g, 0.55, 0.55, h * 0.7, c, a * w * 0.16, h * 0.45, -d / 2 + b * w * 0.16, 5);
      const jib = bx(g, w * 1.5, 1.6, 2.4, c, w * 0.3, h * 0.82, -d / 2);
      jib.rotation.z = 0.22;
      cy(g, 0.25, 0.25, h * 0.34, 0x3f3b36, w * 0.86, h * 0.66, -d / 2, 6); break;
    case 'dock':
      bx(g, w, 2, d, 0x5f5a54, 0, 1, -d / 2);
      bx(g, w * 0.7, h, d * 0.8, 0x4a4642, 0, -h / 2 + 1.6, -d / 2);
      for (const a of [-1, 1]) bx(g, 1.6, 5, d, 0x6f6a62, a * w * 0.46, 4.5, -d / 2); break;
    case 'taper':
      cy(g, w * 0.17, w * 0.34, h * 0.82, c, 0, h * 0.41, -d / 2, 14);
      cy(g, w * 0.24, w * 0.24, h * 0.1, 0x3f3b36, 0, h * 0.87, -d / 2, 14);
      cy(g, w * 0.19, w * 0.19, h * 0.08, 0xffe9a0, 0, h * 0.955, -d / 2, 14);
      cy(g, 0.2, w * 0.2, h * 0.06, 0x3f3b36, 0, h * 1.02, -d / 2, 10);
      bx(g, w * 0.8, 6, w * 0.8, 0xd0ccc4, 0, 3, -d / 2 + w * 0.3); break;
    case 'pier':
      bx(g, w, 1.6, d + 30, 0x7a6a58, 0, h * 0.5, -d / 2 - 8);
      for (let i = 0; i < 7; i++) for (const a of [-1, 1])
        cy(g, 0.55, 0.55, h * 0.5, 0x5f5245, a * w * 0.4, h * 0.25, -d - 12 + i * 8, 6);
      for (let i = 0; i < 6; i++) for (const a of [-1, 1])
        cy(g, 0.3, 0.3, 4, 0xd8d4cc, a * w * 0.4, h * 0.5 + 2, -d - 8 + i * 9, 5);
      break;
    default: body();
  }
  return g;
}

// --- ground, walkway, edge, water --------------------------------------------
const GROUND = 0x6f7f52;
// Rotate the PLANE, not the return of add() — add() hands back the parent.
const ground = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), mat(GROUND, 0.98));
ground.rotation.x = -Math.PI / 2;
ground.userData.backdrop = true;
world.add(ground);

SEGMENTS.forEach(s => {
  const g = new THREE.Group();
  g.position.set(s.fx, 0, s.fz);
  g.rotation.y = s.face;
  // paving under this frontage
  bx(g, s.p.w, 0.5, WALKWAY, 0xb4aea0, 0, 0.25, WALKWAY / 2);
  bx(g, s.p.w, 1.9, EDGE, 0x9a958a, 0, 0.95, WALKWAY + EDGE / 2);
  g.add(massing(s.p));
  world.add(g);
  s.node = g;
});

// cross-street paving between blocks, and water beyond the edge
BLOCKS.forEach((b, i) => {
  if (i >= BLOCKS.length - 1) return;
  const [dx, dz] = DIRS[b.dir];
  const mx = b.end[0] + dx * CROSS / 2, mz = b.end[1] + dz * CROSS / 2;
  const g = new THREE.Group();
  g.position.set(mx, 0, mz);
  g.rotation.y = Math.atan2(-LEFT[b.dir][0], -LEFT[b.dir][1]);
  bx(g, CROSS, 0.42, WALKWAY + DEPTH, 0x4a4844, 0, 0.21, WALKWAY / 2 - DEPTH / 2);
  world.add(g);
});

// Water, but only along the Waterfront block. The route turns, so "water on
// your right" the whole way would need water inside the zigzag too.
{
  const wb = BLOCKS[BLOCKS.length - 1];
  const [wlx, wlz] = LEFT[wb.dir];
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(2200, 1400),
    new THREE.MeshStandardMaterial({ color: 0x3f7fa4, roughness: 0.22, metalness: 0.2 }));
  sea.rotation.x = -Math.PI / 2;
  sea.userData.backdrop = true;
  sea.position.set(
    (wb.start[0] + wb.end[0]) / 2 - wlx * (WALKWAY + EDGE + 700),
    0.3,
    (wb.start[1] + wb.end[1]) / 2 - wlz * (WALKWAY + EDGE + 700));
  world.add(sea);
}

// --- walkable: a corridor along the route ------------------------------------
const walkRects = [];
SEGMENTS.forEach(s => {
  const halfW = s.p.w / 2 + 0.5;
  // rect in world space, axis-aligned because every leg runs along an axis
  const alongX = Math.abs(s.dx) > 0;
  const cxx = s.fx + s.lx * -(WALKWAY / 2), czz = s.fz + s.lz * -(WALKWAY / 2);
  walkRects.push({
    x0: cxx - (alongX ? halfW : WALKWAY / 2 - 0.6),
    x1: cxx + (alongX ? halfW : WALKWAY / 2 - 0.6),
    z0: czz - (alongX ? WALKWAY / 2 - 0.6 : halfW),
    z1: czz + (alongX ? WALKWAY / 2 - 0.6 : halfW),
  });
});
BLOCKS.forEach((b, i) => {
  if (i >= BLOCKS.length - 1) return;
  const [dx, dz] = DIRS[b.dir];
  const [lx, lz] = LEFT[b.dir];
  const mx = b.end[0] + dx * CROSS / 2 - lx * WALKWAY / 2;
  const mz = b.end[1] + dz * CROSS / 2 - lz * WALKWAY / 2;
  walkRects.push({ x0: mx - 22, x1: mx + 22, z0: mz - 22, z1: mz + 22 });
});
const walkable = (x, z) => walkRects.some(r => x > r.x0 && x < r.x1 && z > r.z0 && z < r.z1);

// --- bounds for the plan view -------------------------------------------------
const B = { x0: 1e9, x1: -1e9, z0: 1e9, z1: -1e9 };
SEGMENTS.forEach(s => {
  for (const [px, pz] of [[s.fx, s.fz], [s.fx + s.lx * -(WALKWAY + EDGE), s.fz + s.lz * -(WALKWAY + EDGE)],
                          [s.fx + s.lx * DEPTH, s.fz + s.lz * DEPTH]]) {
    B.x0 = Math.min(B.x0, px - 20); B.x1 = Math.max(B.x1, px + 20);
    B.z0 = Math.min(B.z0, pz - 20); B.z1 = Math.max(B.z1, pz + 20);
  }
});
const MID = { x: (B.x0 + B.x1) / 2, z: (B.z0 + B.z1) / 2 };

// --- camera -------------------------------------------------------------------
const first = SEGMENTS[0];
const player = new THREE.Vector3(
  first.fx - first.dx * 24 + first.lx * -(WALKWAY / 2),
  EYE,
  first.fz - first.dz * 24 + first.lz * -(WALKWAY / 2));
let yaw = Math.atan2(-first.dx, -first.dz), pitch = 0, lift = 1, liftTarget = 1, current = 0;
const keys = new Set();
const vel = new THREE.Vector3();
const look = new THREE.Vector3(), mT = new THREE.Matrix4(), up = new THREE.Vector3(0, 1, 0);

function planHeight() {
  const halfV = Math.tan((camera.fov / 2) * Math.PI / 180);
  return Math.max((B.z1 - B.z0) / 2 / halfV, (B.x1 - B.x0) / 2 / (halfV * camera.aspect)) * 1.04 + 55;
}

function updateCamera() {
  const e = lift * lift * (3 - 2 * lift);
  const cp = Math.cos(pitch);
  camera.position.set(mix(player.x, MID.x, e), mix(player.y, planHeight(), e), mix(player.z, MID.z + 0.01, e));
  look.set(
    mix(player.x - Math.sin(yaw) * cp * 40, MID.x, e),
    mix(player.y + Math.sin(pitch) * 40, 0, e),
    mix(player.z - Math.cos(yaw) * cp * 40, MID.z, e));
  mT.lookAt(camera.position, look, up);
  camera.quaternion.setFromRotationMatrix(mT);
}

// --- pins ---------------------------------------------------------------------
const pins = [];
SEGMENTS.forEach((s, i) => {
  const el = document.createElement('button');
  el.className = `pin b-${s.blk.key}` + (s.p.landmark ? ' lm' : '');
  el.textContent = s.p.n;
  el.title = `${s.p.n} · ${s.p.name} · ${s.blk.name}`;
  el.onclick = () => { goTo(i); };
  $('map').appendChild(el);
  pins.push({ el, s, v: new THREE.Vector3() });
});

function layoutPins() {
  camera.updateMatrixWorld(true);
  const show = lift > 0.16;
  pins.forEach((pn, i) => {
    const s = pn.s;
    pn.v.set(s.fx + s.lx * -(WALKWAY / 2), 2, s.fz + s.lz * -(WALKWAY / 2)).project(camera);
    const on = show && pn.v.z < 1;
    pn.el.style.display = on ? '' : 'none';
    if (!on) return;
    pn.el.style.left = `${(pn.v.x * 0.5 + 0.5) * innerWidth}px`;
    pn.el.style.top = `${(-pn.v.y * 0.5 + 0.5) * innerHeight}px`;
    pn.el.classList.toggle('here', i === current);
  });
}

function goTo(i) {
  const s = SEGMENTS[i];
  player.set(s.fx + s.lx * -(WALKWAY / 2) - s.dx * 6, EYE, s.fz + s.lz * -(WALKWAY / 2) - s.dz * 6);
  yaw = Math.atan2(-s.dx, -s.dz);
  pitch = 0.06;
  current = i; liftTarget = 0; refresh();
}

function refresh() {
  const s = SEGMENTS[current];
  $('p-n').textContent = s.p.n;
  $('p-name').textContent = s.p.name;
  $('p-block').textContent = `${s.blk.name} · ${s.blk.character}`;
  $('p-form').textContent = `${s.p.form} · ${s.p.w}×${s.p.h} ft`;
  $('hud').style.borderLeftColor = '#' + s.blk.tint.toString(16).padStart(6, '0');
}

// --- input --------------------------------------------------------------------
const stage = $('stage');
let drag = false, lx = 0, ly = 0;
stage.addEventListener('pointerdown', e => {
  drag = true; lx = e.clientX; ly = e.clientY; stage.setPointerCapture(e.pointerId);
  document.body.classList.add('grabbing');
});
addEventListener('pointerup', () => { drag = false; document.body.classList.remove('grabbing'); });
addEventListener('pointermove', e => {
  if (!drag) return;
  if (lift < 0.5) {
    yaw -= (e.clientX - lx) * 0.005;
    pitch = clamp(pitch - (e.clientY - ly) * 0.005, -1.1, 1.1);
  }
  lx = e.clientX; ly = e.clientY;
});
stage.addEventListener('wheel', e => {
  e.preventDefault(); liftTarget = clamp(liftTarget + Math.sign(e.deltaY) * 0.18, 0, 1);
}, { passive: false });
const MOVE_KEYS = new Set(['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight']);
addEventListener('keydown', e => {
  if (e.code === 'KeyM') { liftTarget = liftTarget > 0.5 ? 0 : 1; return; }
  if (e.code === 'KeyO') { outline = !outline; setOutline(); return; }
  // Pressing a movement key while hovering means "let me walk" — drop to the
  // ground rather than silently ignoring it.
  if (MOVE_KEYS.has(e.code) && liftTarget > 0.5) liftTarget = 0;
  keys.add(e.code);
});
addEventListener('keyup', e => keys.delete(e.code));
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; renderer.setSize(innerWidth, innerHeight);
});

// --- silhouette mode: the production test, one keystroke ---------------------
let outline = false;
const flatMat = new THREE.MeshBasicMaterial({ color: 0x11151b });
const paleMat = new THREE.MeshBasicMaterial({ color: 0xdfe6ee });
function setOutline() {
  world.traverse(o => {
    if (!o.isMesh) return;
    o.userData.m = o.userData.m || o.material;
    // Ground and water go PALE, not black — flatten everything and the
    // silhouettes vanish into a black field and the test shows you nothing.
    if (outline) o.material = o.userData.backdrop ? paleMat : flatMat;
    else o.material = o.userData.m;
  });
  scene.background = new THREE.Color(outline ? 0xdfe6ee : 0xa8c0d4);
  // Fog has to go entirely — at plan-view altitude everything is past `near`,
  // so silhouettes get washed to background grey and the test tells you nothing.
  scene.fog = outline ? null : baseFog;
  $('t-out').classList.toggle('on', outline);
}

$('to-plan').onclick = () => { liftTarget = 1; };
$('to-ground').onclick = () => { liftTarget = 0; };
$('t-out').onclick = () => { outline = !outline; setOutline(); };
$('enter').onclick = () => { $('intro').style.display = 'none'; goTo(0); };
// Step buttons: the whole palace is usable by tapping, with no keyboard.
$('prev').onclick = () => goTo(Math.max(0, current - 1));
$('next').onclick = () => goTo(Math.min(SEGMENTS.length - 1, current + 1));

// --- loop ---------------------------------------------------------------------
const clock = new THREE.Clock();
function nearestSeg() {
  let bi = 0, bd = Infinity;
  SEGMENTS.forEach((s, i) => {
    const d = (s.fx - player.x) ** 2 + (s.fz - player.z) ** 2;
    if (d < bd) { bd = d; bi = i; }
  });
  return bi;
}
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  lift += (liftTarget - lift) * (1 - Math.pow(0.003, dt));

  if (lift < 0.35) {
    const sp = keys.has('ShiftLeft') || keys.has('ShiftRight') ? SPEED * 2.2 : SPEED;
    const fwd = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
    const str = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0);
    yaw -= ((keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0)) * dt * 1.9;
    const w = new THREE.Vector3(
      Math.sin(yaw) * -fwd + Math.cos(yaw) * str, 0,
      Math.cos(yaw) * -fwd - Math.sin(yaw) * str);
    if (w.lengthSq() > 0) w.normalize().multiplyScalar(sp);
    vel.lerp(w, 1 - Math.pow(0.002, dt));
    const nx = player.x + vel.x * dt;
    if (walkable(nx, player.z)) player.x = nx; else vel.x = 0;
    const nz = player.z + vel.z * dt;
    if (walkable(player.x, nz)) player.z = nz; else vel.z = 0;
    player.y = EYE;
    const ns = nearestSeg();
    if (ns !== current) { current = ns; refresh(); }
  }
  updateCamera(); layoutPins();
  $('hud').classList.toggle('up', lift > 0.55);
  renderer.render(scene, camera);
}

$('spec').textContent =
  `50 places · 5 blocks of 10 · ${Math.round(ROUTE_LEN)} ft ≈ ${Math.round(ROUTE_LEN / SPEED)} s walk`;
refresh();
frame();
window.__prom = { SEGMENTS, BLOCKS, ALL, player, walkable, ROUTE_LEN, get lift() { return lift; }, goTo };
