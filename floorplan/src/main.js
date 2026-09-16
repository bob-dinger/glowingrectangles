import * as THREE from 'three';
import { PLANS, ROOM_TINTS } from './plans.js';

const $ = id => document.getElementById(id);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const mix = (a, b, t) => a + (b - a) * t;

const CELL = 0.75;      // metres per character
const WALL_H = 2.9;
const EYE = 1.62;

// ---------------------------------------------------------------------------
// Parse
// ---------------------------------------------------------------------------

function parse(lines) {
  const h = lines.length;
  const w = Math.max(...lines.map(l => l.length));
  const at = (x, y) => (lines[y] || '')[x] || '#';
  const isRoom = c => /[a-z]/.test(c);
  const walk = (x, y) => { const c = at(x, y); return isRoom(c) || c === '+'; };

  const letters = [...new Set(lines.join('').split('').filter(isRoom))];
  const cells = {};
  for (const L of letters) cells[L] = [];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const c = at(x, y);
      if (isRoom(c)) cells[c].push([x, y]);
    }
  }
  // Room centre = centroid of its cells, nudged to a cell that's actually
  // inside it (an L-shaped room's centroid can land in a wall).
  const centres = {};
  for (const L of letters) {
    const cs = cells[L];
    const cx = cs.reduce((a, p) => a + p[0], 0) / cs.length;
    const cy = cs.reduce((a, p) => a + p[1], 0) / cs.length;
    let best = cs[0], bd = Infinity;
    for (const p of cs) {
      const d = (p[0] - cx) ** 2 + (p[1] - cy) ** 2;
      if (d < bd) { bd = d; best = p; }
    }
    centres[L] = best;
  }
  return { lines, w, h, at, isRoom, walk, letters, cells, centres };
}

// World <-> grid. Grid origin is centred so the building sits around 0,0.
const gx = (p, x) => (x - p.w / 2 + 0.5) * CELL;
const gz = (p, y) => (y - p.h / 2 + 0.5) * CELL;
const toCellX = (p, X) => Math.floor(X / CELL + p.w / 2);
const toCellY = (p, Z) => Math.floor(Z / CELL + p.h / 2);

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x151922);

const camera = new THREE.PerspectiveCamera(66, innerWidth / innerHeight, 0.05, 400);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
$('stage').appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.55));
scene.add(new THREE.HemisphereLight(0xbcd0e8, 0x2a2622, 0.7));
const sun = new THREE.DirectionalLight(0xfff2e0, 1.5);
sun.position.set(-18, 40, 22);
scene.add(sun);
const lamp = new THREE.PointLight(0xffe8c8, 14, 16, 1.6);
scene.add(lamp);

const built = new THREE.Group();
scene.add(built);

let plan = null, roofs = [], roomOrder = [], planKey = 'museum';

function dispose(o) {
  o.traverse(c => {
    if (c.geometry) c.geometry.dispose();
    if (c.material) (Array.isArray(c.material) ? c.material : [c.material]).forEach(m => m.dispose());
  });
  o.clear();
}

function build(lines) {
  dispose(built);
  roofs = [];
  plan = parse(lines);
  const p = plan;

  const tintFor = L => ROOM_TINTS[p.letters.indexOf(L) % ROOM_TINTS.length];

  // --- floors, one merged box per cell (cheap and exact) ---
  const floorMat = new Map();
  for (const L of p.letters) {
    const col = new THREE.Color(tintFor(L));
    floorMat.set(L, new THREE.MeshStandardMaterial({
      color: col.lerp(new THREE.Color(0x0d1016), 0.24), roughness: 0.95,
    }));
  }
  const doorMat = new THREE.MeshStandardMaterial({ color: 0x2e3440, roughness: 0.9 });
  const floorGeo = new THREE.BoxGeometry(CELL, 0.12, CELL);
  const counts = {};
  for (const L of p.letters) counts[L] = p.cells[L].length;
  const doorCells = [];
  for (let y = 0; y < p.h; y++) for (let x = 0; x < p.w; x++) if (p.at(x, y) === '+') doorCells.push([x, y]);

  for (const L of p.letters) {
    const im = new THREE.InstancedMesh(floorGeo, floorMat.get(L), counts[L]);
    p.cells[L].forEach(([x, y], i) => {
      im.setMatrixAt(i, new THREE.Matrix4().makeTranslation(gx(p, x), -0.06, gz(p, y)));
    });
    im.instanceMatrix.needsUpdate = true;
    built.add(im);
  }
  if (doorCells.length) {
    const im = new THREE.InstancedMesh(floorGeo, doorMat, doorCells.length);
    doorCells.forEach(([x, y], i) => {
      im.setMatrixAt(i, new THREE.Matrix4().makeTranslation(gx(p, x), -0.06, gz(p, y)));
    });
    im.instanceMatrix.needsUpdate = true;
    built.add(im);
  }

  // --- walls: only the '#' cells that actually touch walkable space, so the
  // solid mass outside the building isn't drawn at all ---
  const wallCells = [];
  for (let y = 0; y < p.h; y++) {
    for (let x = 0; x < p.w; x++) {
      if (p.at(x, y) !== '#') continue;
      let touches = false;
      for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
        if (p.walk(x + dx, y + dy)) { touches = true; break; }
      }
      if (touches) wallCells.push([x, y]);
    }
  }
  const wallGeo = new THREE.BoxGeometry(CELL, WALL_H, CELL);
  const wallMat = new THREE.MeshStandardMaterial({ color: 0xd9d2c4, roughness: 0.92 });
  const wim = new THREE.InstancedMesh(wallGeo, wallMat, wallCells.length);
  wallCells.forEach(([x, y], i) => {
    wim.setMatrixAt(i, new THREE.Matrix4().makeTranslation(gx(p, x), WALL_H / 2, gz(p, y)));
  });
  wim.instanceMatrix.needsUpdate = true;
  built.add(wim);

  // --- door frames, so an opening reads as a doorway from inside ---
  const frameMat = new THREE.MeshStandardMaterial({ color: 0x6b4f34, roughness: 0.85 });
  for (const [x, y] of doorCells) {
    const acrossX = p.at(x - 1, y) === '#' && p.at(x + 1, y) === '#';
    const g = new THREE.Mesh(
      new THREE.BoxGeometry(acrossX ? CELL * 1.15 : CELL * 0.22, 0.22, acrossX ? CELL * 0.22 : CELL * 1.15),
      frameMat);
    g.position.set(gx(p, x), 2.15, gz(p, y));
    built.add(g);
  }

  // --- ceilings, tinted per room and hidden when you rise into the plan view.
  // Walls are shared between two rooms so they can't carry room identity; the
  // ceiling can, and it gives you a "which room am I in" cue from inside. ---
  for (const L of p.letters) {
    const ceilMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(tintFor(L)).lerp(new THREE.Color(0x222831), 0.55), roughness: 1,
    });
    const im = new THREE.InstancedMesh(floorGeo, ceilMat, counts[L]);
    p.cells[L].forEach(([x, y], i) => {
      im.setMatrixAt(i, new THREE.Matrix4().makeTranslation(gx(p, x), WALL_H - 0.06, gz(p, y)));
    });
    im.instanceMatrix.needsUpdate = true;
    built.add(im);
    roofs.push(im);
  }

  const meta = PLANS[planKey];
  roomOrder = (meta?.order || p.letters.join('')).split('').filter(L => p.letters.includes(L));
  for (const L of p.letters) if (!roomOrder.includes(L)) roomOrder.push(L);

  buildPins();
  const area = (p.letters.reduce((a, L) => a + counts[L], 0) + doorCells.length) * CELL * CELL;
  $('stat-rooms').textContent = p.letters.length;
  $('stat-size').textContent = `${(p.w * CELL).toFixed(1)} × ${(p.h * CELL).toFixed(1)} m`;
  $('stat-area').textContent = `${Math.round(area)} m²`;
}

// ---------------------------------------------------------------------------
// Movement
// ---------------------------------------------------------------------------

const player = new THREE.Vector3();
let yaw = 0, pitch = 0, lift = 1, liftTarget = 1, current = 0;
const keys = new Set();
const vel = new THREE.Vector3();

function walkableAt(X, Z) {
  const p = plan;
  const r = 0.22;
  for (const [ox, oz] of [[r, r], [-r, r], [r, -r], [-r, -r]]) {
    if (!p.walk(toCellX(p, X + ox), toCellY(p, Z + oz))) return false;
  }
  return true;
}

function standIn(L, face) {
  const p = plan;
  const [cx, cy] = p.centres[L];
  player.set(gx(p, cx), EYE, gz(p, cy));
  if (face) {
    const [fx, fy] = p.centres[face];
    const dx = gx(p, fx) - player.x, dz = gz(p, fy) - player.z;
    yaw = Math.atan2(-dx, -dz);
    // Back off along the approach so you see the room you're standing in,
    // not just the far wall two metres from your nose.
    const len = Math.hypot(dx, dz) || 1;
    for (const back of [1.7, 1.1, 0.6, 0]) {
      const nx = player.x - dx / len * back, nz = player.z - dz / len * back;
      if (walkableAt(nx, nz)) { player.set(nx, EYE, nz); break; }
    }
  }
  pitch = 0;
}

// ---------------------------------------------------------------------------
// Camera — one continuous parameter from standing inside to the plan overhead
// ---------------------------------------------------------------------------

const look = new THREE.Vector3(), mTmp = new THREE.Matrix4(), up = new THREE.Vector3(0, 1, 0);

function updateCamera() {
  const e = lift * lift * (3 - 2 * lift);
  const p = plan;
  const halfV = Math.tan((camera.fov / 2) * Math.PI / 180);
  // Fit to the WALL TOPS, not the floor. They sit WALL_H closer to the camera,
  // so fitting the floor plane crops the building's outer walls out of frame.
  const fit = Math.max(p.h * CELL / 2 / halfV, p.w * CELL / 2 / (halfV * camera.aspect)) * 1.1;
  const need = fit + WALL_H;

  const cp = Math.cos(pitch);
  camera.position.set(
    mix(player.x, 0, e),
    mix(player.y, need, e),
    mix(player.z, 0.0001, e));
  look.set(
    mix(player.x - Math.sin(yaw) * cp * 8, 0, e),
    mix(player.y + Math.sin(pitch) * 8, 0, e),
    mix(player.z - Math.cos(yaw) * cp * 8, 0.0001, e));
  mTmp.lookAt(camera.position, look, up);
  camera.quaternion.setFromRotationMatrix(mTmp);
  roofs.forEach(r => { r.visible = e < 0.12; });
  lamp.position.copy(player);
  lamp.intensity = (1 - e) * 14;
}

// ---------------------------------------------------------------------------
// Pins
// ---------------------------------------------------------------------------

const pins = [];
function buildPins() {
  const map = $('map');
  map.innerHTML = '';
  pins.length = 0;
  roomOrder.forEach((L, i) => {
    const meta = PLANS[planKey];
    const isCorridor = meta?.corridor === L;
    const el = document.createElement('button');
    el.className = 'pin' + (isCorridor ? ' corridor' : '');
    el.textContent = isCorridor ? '·' : String(i + 1);
    el.title = meta?.rooms?.[L] || L;
    el.onclick = () => {
      current = i;
      standIn(L, roomOrder[i + 1]);
      liftTarget = 0;
      refresh();
    };
    map.appendChild(el);
    pins.push({ el, L, v: new THREE.Vector3() });
  });
}

function layoutPins() {
  camera.updateMatrixWorld(true);
  const p = plan;
  pins.forEach(pin => {
    const [cx, cy] = p.centres[pin.L];
    pin.v.set(gx(p, cx), 1.2, gz(p, cy)).project(camera);
    const on = pin.v.z < 1 && lift > 0.15;
    pin.el.style.display = on ? '' : 'none';
    if (!on) return;
    pin.el.style.left = `${(pin.v.x * 0.5 + 0.5) * innerWidth}px`;
    pin.el.style.top = `${(-pin.v.y * 0.5 + 0.5) * innerHeight}px`;
    pin.el.classList.toggle('here', pin.L === roomOrder[current]);
  });
}

function refresh() {
  const meta = PLANS[planKey];
  const L = roomOrder[current];
  const isCorridor = meta?.corridor === L;
  $('r-n').textContent = isCorridor ? '·' : current + 1;
  $('r-name').textContent = meta?.rooms?.[L] || `Room ${L}`;
  $('r-of').textContent = isCorridor ? 'circulation' : `room ${current + 1} of ${roomOrder.length}`;
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

const stage = $('stage');
let drag = false, lx = 0, ly = 0;
stage.addEventListener('pointerdown', e => {
  drag = true; lx = e.clientX; ly = e.clientY; stage.setPointerCapture(e.pointerId);
});
addEventListener('pointerup', () => { drag = false; });
addEventListener('pointermove', e => {
  if (!drag || lift > 0.5) { if (drag) { lx = e.clientX; ly = e.clientY; } return; }
  yaw -= (e.clientX - lx) * 0.005;
  pitch = clamp(pitch - (e.clientY - ly) * 0.005, -1.1, 1.1);
  lx = e.clientX; ly = e.clientY;
});
stage.addEventListener('wheel', e => {
  e.preventDefault();
  liftTarget = clamp(liftTarget + Math.sign(e.deltaY) * 0.18, 0, 1);
}, { passive: false });
addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA') return;
  if (e.code === 'KeyM') { liftTarget = liftTarget > 0.5 ? 0 : 1; return; }
  keys.add(e.code);
});
addEventListener('keyup', e => keys.delete(e.code));
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  renderer.setSize(innerWidth, innerHeight);
});

// ---------------------------------------------------------------------------
// The text editor — this is the point of the whole page
// ---------------------------------------------------------------------------

const ta = $('src');
let rebuildTimer = null;

function loadPlan(key) {
  planKey = key;
  const meta = PLANS[key];
  ta.value = meta.grid.join('\n');
  build(meta.grid);
  current = 0;
  standIn(roomOrder[0], roomOrder[1]);
  liftTarget = 1; lift = 1;
  refresh();
  $('p-name').textContent = meta.name;
  $('p-note').textContent = meta.note;
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.dataset.plan === key));
}

ta.addEventListener('input', () => {
  clearTimeout(rebuildTimer);
  rebuildTimer = setTimeout(() => {
    const lines = ta.value.split('\n').filter(l => l.length);
    if (!lines.length) return;
    try {
      const before = roomOrder[current];
      build(lines);
      const keep = roomOrder.indexOf(before);
      current = keep >= 0 ? keep : 0;
      if (!walkableAt(player.x, player.z)) standIn(roomOrder[current], roomOrder[current + 1]);
      refresh();
      $('err').textContent = '';
    } catch (err) {
      $('err').textContent = String(err.message || err);
    }
  }, 180);
});

for (const t of document.querySelectorAll('.tab')) t.onclick = () => loadPlan(t.dataset.plan);
$('to-plan').onclick = () => { liftTarget = 1; };
$('to-floor').onclick = () => { liftTarget = 0; };
$('enter').onclick = () => { $('intro').style.display = 'none'; };
$('toggle-src').onclick = () => {
  const open = $('editor').classList.toggle('open');
  $('toggle-src').textContent = open ? 'Hide plan text' : 'Edit plan text';
};

// ---------------------------------------------------------------------------

const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  lift += (liftTarget - lift) * (1 - Math.pow(0.003, dt));

  if (lift < 0.35) {
    const speed = keys.has('ShiftLeft') ? 6.5 : 3.1;
    const fwd = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
    const str = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0);
    yaw -= ((keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0)) * dt * 1.9;
    const want = new THREE.Vector3(
      Math.sin(yaw) * -fwd + Math.cos(yaw) * str, 0,
      Math.cos(yaw) * -fwd - Math.sin(yaw) * str);
    if (want.lengthSq() > 0) want.normalize().multiplyScalar(speed);
    vel.lerp(want, 1 - Math.pow(0.002, dt));
    const nx = player.x + vel.x * dt;
    if (walkableAt(nx, player.z)) player.x = nx; else vel.x = 0;
    const nz = player.z + vel.z * dt;
    if (walkableAt(player.x, nz)) player.z = nz; else vel.z = 0;
    player.y = EYE;

    const c = plan.at(toCellX(plan, player.x), toCellY(plan, player.z));
    const idx = roomOrder.indexOf(c);
    if (idx >= 0 && idx !== current) { current = idx; refresh(); }
  }

  updateCamera();
  layoutPins();
  $('hud').classList.toggle('up', lift > 0.55);
  renderer.render(scene, camera);
}

loadPlan('museum');
frame();
window.__fp = { get plan() { return plan; }, player, walkableAt, get lift() { return lift; }, loadPlan };
