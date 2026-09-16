import * as THREE from 'three';

// ===========================================================================
// THE SPEC. Everything below derives from these numbers — change one and the
// whole block rebuilds. Units are FEET throughout, because that's how the
// site was specified.
// ===========================================================================

const LOT     = 50;   // ft — each lot is LOT x LOT
const STREET  = 20;   // ft — right-of-way between lots
const COLS    = 2;    // lots across
const ROWS    = 2;    // lots down
const WALK    = 4;    // ft — sidewalk strip, taken from the LOT, not the street
const PAD     = 30;   // ft — placeholder building footprint, centred on its lot
const PAD_H   = 22;   // ft — placeholder building height
const EYE     = 5.6;  // ft — eye height (~1.7 m)

// Derived
const SPAN_X = COLS * LOT + (COLS - 1) * STREET;
const SPAN_Z = ROWS * LOT + (ROWS - 1) * STREET;
const HALF_X = SPAN_X / 2, HALF_Z = SPAN_Z / 2;

// Lot rectangles, laid out around the origin. Row-major, numbered 1..n.
const LOTS = [];
for (let r = 0; r < ROWS; r++) {
  for (let c = 0; c < COLS; c++) {
    const x0 = -HALF_X + c * (LOT + STREET);
    const z0 = -HALF_Z + r * (LOT + STREET);
    LOTS.push({
      n: LOTS.length + 1, x0, z0, x1: x0 + LOT, z1: z0 + LOT,
      cx: x0 + LOT / 2, cz: z0 + LOT / 2,
    });
  }
}

// Street centrelines run between each pair of lot columns / rows.
const STREETS_X = [], STREETS_Z = [];
for (let c = 1; c < COLS; c++) STREETS_X.push(-HALF_X + c * LOT + (c - 0.5) * STREET);
for (let r = 1; r < ROWS; r++) STREETS_Z.push(-HALF_Z + r * LOT + (r - 0.5) * STREET);

const LOT_TINT = [0x6f8a4a, 0x8a7a4a, 0x4a7a8a, 0x8a5a6a, 0x6a5a8a, 0x4a8a6a];
const PAD_TINT = [0xc9c0ae, 0xbfa98e, 0xa8b6bf, 0xc2a6ac, 0xb0a8c4, 0xa6c2b2];

const $ = id => document.getElementById(id);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const mix = (a, b, t) => a + (b - a) * t;

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x9fb8cf);
scene.fog = new THREE.Fog(0x9fb8cf, 240, 620);

const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.4, 3000);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
$('stage').appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
scene.add(new THREE.HemisphereLight(0xcfe0f0, 0x4a4636, 0.8));
const sun = new THREE.DirectionalLight(0xfff4e2, 1.7);
sun.position.set(-120, 200, 90);
scene.add(sun);

const world = new THREE.Group();
scene.add(world);

const box = (w, h, d, color, x, y, z, opts = {}) => {
  const m = new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    new THREE.MeshStandardMaterial({ color, roughness: opts.r ?? 0.95, metalness: 0 }));
  m.position.set(x, y, z);
  return m;
};

// --- surrounding ground -----------------------------------------------------
world.add(box(SPAN_X + 420, 1, SPAN_Z + 420, 0x5f7a46, 0, -0.55, 0));

// --- streets: one asphalt strip per centreline, full span, plus the crossing -
const ASPHALT = 0x37393d;
for (const sx of STREETS_X) world.add(box(STREET, 0.3, SPAN_Z + 160, ASPHALT, sx, -0.05, 0));
for (const sz of STREETS_Z) world.add(box(SPAN_X + 160, 0.3, STREET, ASPHALT, 0, -0.05, sz));

// Centre dashes, skipped through the intersection so it reads correctly.
const inIntersection = (x, z) =>
  STREETS_X.some(sx => Math.abs(x - sx) < STREET / 2) &&
  STREETS_Z.some(sz => Math.abs(z - sz) < STREET / 2);
const DASH = 6, GAP = 6;
for (const sx of STREETS_X) {
  for (let z = -HALF_Z - 80; z < HALF_Z + 80; z += DASH + GAP) {
    if (inIntersection(sx, z)) continue;
    world.add(box(0.6, 0.06, DASH, 0xd8cf7a, sx, 0.12, z));
  }
}
for (const sz of STREETS_Z) {
  for (let x = -HALF_X - 80; x < HALF_X + 80; x += DASH + GAP) {
    if (inIntersection(x, sz)) continue;
    world.add(box(DASH, 0.06, 0.6, 0xd8cf7a, x, 0.12, sz));
  }
}

// --- lots: ground, sidewalk skirt, kerb, placeholder building ---------------
const CURB_H = 0.5;
LOTS.forEach((L, i) => {
  world.add(box(LOT, 0.4, LOT, LOT_TINT[i % LOT_TINT.length], L.cx, 0.2, L.cz));

  // Sidewalk taken from the lot, so the street stays exactly STREET wide.
  const SW = 0xb9b4a8;
  world.add(box(LOT, 0.45, WALK, SW, L.cx, 0.42, L.z0 + WALK / 2));
  world.add(box(LOT, 0.45, WALK, SW, L.cx, 0.42, L.z1 - WALK / 2));
  world.add(box(WALK, 0.45, LOT - WALK * 2, SW, L.x0 + WALK / 2, 0.42, L.cz));
  world.add(box(WALK, 0.45, LOT - WALK * 2, SW, L.x1 - WALK / 2, 0.42, L.cz));

  // Kerb along the lot line
  const K = 0x9a958a;
  world.add(box(LOT, CURB_H, 0.7, K, L.cx, CURB_H / 2, L.z0));
  world.add(box(LOT, CURB_H, 0.7, K, L.cx, CURB_H / 2, L.z1));
  world.add(box(0.7, CURB_H, LOT, K, L.x0, CURB_H / 2, L.cz));
  world.add(box(0.7, CURB_H, LOT, K, L.x1, CURB_H / 2, L.cz));

  // Placeholder massing — replace these with real buildings later.
  const g = new THREE.Group();
  g.add(box(PAD, PAD_H, PAD, PAD_TINT[i % PAD_TINT.length], 0, PAD_H / 2, 0, { r: 0.9 }));
  g.add(box(PAD + 1.6, 1.2, PAD + 1.6, 0x8f887c, 0, PAD_H + 0.6, 0));
  g.position.set(L.cx, 0.4, L.cz);
  g.userData.pad = true;
  world.add(g);
  L.pad = g;
});

const pads = LOTS.map(L => L.pad);

// ---------------------------------------------------------------------------
// Where you can walk
// ---------------------------------------------------------------------------

const onBlock = (x, z) => Math.abs(x) < HALF_X + 55 && Math.abs(z) < HALF_Z + 55;
const inPad = (x, z) => LOTS.some(L =>
  Math.abs(x - L.cx) < PAD / 2 + 0.8 && Math.abs(z - L.cz) < PAD / 2 + 0.8);

function walkable(x, z) {
  if (!onBlock(x, z)) return false;
  if (showPads && inPad(x, z)) return false;
  return true;
}

function lotAt(x, z) {
  return LOTS.find(L => x > L.x0 && x < L.x1 && z > L.z0 && z < L.z1) || null;
}

// ---------------------------------------------------------------------------
// Camera: one continuous parameter, ground <-> plan
// ---------------------------------------------------------------------------

// Start on the street centreline south of the site. yaw 0 faces -Z, i.e. up
// the street toward the intersection — walking forward enters the block.
const player = new THREE.Vector3(0, EYE, HALF_Z + 26);
let yaw = 0, pitch = 0, lift = 1, liftTarget = 1;
let showPads = true;
const keys = new Set();
const vel = new THREE.Vector3();
const look = new THREE.Vector3(), mTmp = new THREE.Matrix4(), up = new THREE.Vector3(0, 1, 0);

function planHeight() {
  const halfV = Math.tan((camera.fov / 2) * Math.PI / 180);
  const fit = (w, d, y) => Math.max(d / 2 / halfV, w / 2 / (halfV * camera.aspect)) + y;
  // Two constraints: the site must fit at ground level, and the rooftops —
  // which are nearer the camera but INSET from the lot lines — must also fit.
  // Fitting the full span at roof height (the obvious guess) over-zooms.
  const roofSpanX = SPAN_X - (LOT - PAD), roofSpanZ = SPAN_Z - (LOT - PAD);
  return Math.max(
    fit(SPAN_X + 24, SPAN_Z + 24, 0),
    fit(roofSpanX + 24, roofSpanZ + 24, PAD_H));
}

function updateCamera() {
  const e = lift * lift * (3 - 2 * lift);
  const cp = Math.cos(pitch);
  camera.position.set(
    mix(player.x, 0, e),
    mix(player.y, planHeight(), e),
    mix(player.z, 0.001, e));
  look.set(
    mix(player.x - Math.sin(yaw) * cp * 30, 0, e),
    mix(player.y + Math.sin(pitch) * 30, 0, e),
    mix(player.z - Math.cos(yaw) * cp * 30, 0.001, e));
  mTmp.lookAt(camera.position, look, up);
  camera.quaternion.setFromRotationMatrix(mTmp);
}

// ---------------------------------------------------------------------------
// Overlay labels
// ---------------------------------------------------------------------------

const marks = [];
function buildMarks() {
  const map = $('map');
  map.innerHTML = '';
  marks.length = 0;
  const add = (cls, text, x, z, title) => {
    const el = document.createElement('div');
    el.className = cls;
    el.textContent = text;
    if (title) el.title = title;
    map.appendChild(el);
    marks.push({ el, x, z, v: new THREE.Vector3() });
  };
  LOTS.forEach(L => add('lot', `Lot ${L.n}`, L.cx, L.cz, `${LOT} × ${LOT} ft`));
  // dimension callouts
  const L0 = LOTS[0];
  add('dim', `${LOT} ft`, L0.cx, L0.z0 - 7);
  add('dim vert', `${LOT} ft`, L0.x0 - 7, L0.cz);
  if (STREETS_X.length) add('dim st', `${STREET} ft`, STREETS_X[0], -HALF_Z - 9);
  if (STREETS_Z.length) add('dim st', `${STREET} ft`, -HALF_X - 11, STREETS_Z[0]);
}

function layoutMarks() {
  camera.updateMatrixWorld(true);
  const show = lift > 0.55;
  for (const m of marks) {
    m.v.set(m.x, 0.6, m.z).project(camera);
    const on = show && m.v.z < 1;
    m.el.style.display = on ? '' : 'none';
    if (!on) continue;
    m.el.style.left = `${(m.v.x * 0.5 + 0.5) * innerWidth}px`;
    m.el.style.top = `${(-m.v.y * 0.5 + 0.5) * innerHeight}px`;
  }
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

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
  e.preventDefault();
  liftTarget = clamp(liftTarget + Math.sign(e.deltaY) * 0.18, 0, 1);
}, { passive: false });
addEventListener('keydown', e => {
  if (e.code === 'KeyM') { liftTarget = liftTarget > 0.5 ? 0 : 1; return; }
  keys.add(e.code);
});
addEventListener('keyup', e => keys.delete(e.code));
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  renderer.setSize(innerWidth, innerHeight);
});

$('to-plan').onclick = () => { liftTarget = 1; };
$('to-ground').onclick = () => { liftTarget = 0; };
$('t-pads').onclick = e => {
  showPads = !showPads;
  pads.forEach(p => { p.visible = showPads; });
  e.currentTarget.classList.toggle('off', !showPads);
};
$('enter').onclick = () => { $('intro').style.display = 'none'; };

// ---------------------------------------------------------------------------

const clock = new THREE.Clock();
function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  lift += (liftTarget - lift) * (1 - Math.pow(0.003, dt));

  if (lift < 0.35) {
    const speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 42 : 18; // ft/s
    const fwd = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
    const str = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0);
    yaw -= ((keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0)) * dt * 1.9;
    const want = new THREE.Vector3(
      Math.sin(yaw) * -fwd + Math.cos(yaw) * str, 0,
      Math.cos(yaw) * -fwd - Math.sin(yaw) * str);
    if (want.lengthSq() > 0) want.normalize().multiplyScalar(speed);
    vel.lerp(want, 1 - Math.pow(0.002, dt));
    const nx = player.x + vel.x * dt;
    if (walkable(nx, player.z)) player.x = nx; else vel.x = 0;
    const nz = player.z + vel.z * dt;
    if (walkable(player.x, nz)) player.z = nz; else vel.z = 0;
    player.y = EYE;
  }

  const L = lotAt(player.x, player.z);
  $('where').textContent = lift > 0.55 ? 'Site plan'
    : L ? `Lot ${L.n} · ${LOT} × ${LOT} ft` : 'Street';

  updateCamera();
  layoutMarks();
  renderer.render(scene, camera);
}

$('spec').textContent =
  `${COLS}×${ROWS} lots · ${LOT}×${LOT} ft each · ${STREET} ft streets · site ${SPAN_X}×${SPAN_Z} ft`;
buildMarks();
frame();

window.__block = { LOTS, LOT, STREET, SPAN_X, SPAN_Z, player, walkable, get lift() { return lift; } };
