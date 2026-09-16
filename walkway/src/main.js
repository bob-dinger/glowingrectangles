import * as THREE from 'three';
import { STATIONS } from './stations.js';
import { PRESIDENTS } from '../../palace/src/presidents.js';

const $ = id => document.getElementById(id);
const clamp = (v, a, b) => v < a ? a : v > b ? b : v;
const mix = (a, b, t) => a + (b - a) * t;
const smooth = (a, b, t) => { const x = clamp((t - a) / (b - a), 0, 1); return x * x * (3 - 2 * x); };

// ---------------------------------------------------------------------------
// Toolkit — same shape the palace props were authored against, so the peg
// builders in presidents.js can be reused unchanged.
// ---------------------------------------------------------------------------

const geoCache = new Map();
const cached = (k, f) => { let g = geoCache.get(k); if (!g) { g = f(); geoCache.set(k, g); } return g; };
const mat = (c, o = {}) => new THREE.MeshStandardMaterial({
  color: c, roughness: o.r ?? 0.85, metalness: o.m ?? 0.02,
  emissive: o.e ?? 0x000000, emissiveIntensity: o.ei ?? 1,
  transparent: o.t !== undefined, opacity: o.t ?? 1,
  side: o.side === 2 ? THREE.DoubleSide : THREE.FrontSide,
});
const K = {
  g: () => new THREE.Group(),
  box: (w, h, d, c, o) => new THREE.Mesh(cached(`b${w},${h},${d}`, () => new THREE.BoxGeometry(w, h, d)), mat(c, o)),
  cyl: (rt, rb, h, c, o) => new THREE.Mesh(cached(`c${rt},${rb},${h}`, () => new THREE.CylinderGeometry(rt, rb, h, 16)), mat(c, o)),
  sph: (r, c, o) => new THREE.Mesh(cached(`s${r}`, () => new THREE.SphereGeometry(r, 16, 11)), mat(c, o)),
  cone: (r, h, c, o) => new THREE.Mesh(cached(`n${r},${h}`, () => new THREE.ConeGeometry(r, h, 14)), mat(c, o)),
  tor: (r, t, c, o) => new THREE.Mesh(cached(`t${r},${t}`, () => new THREE.TorusGeometry(r, t, 8, 20)), mat(c, o)),
  at: (m, x, y, z) => { m.position.set(x, y, z); return m; },
  rot: (m, x, y, z) => { m.rotation.set(x, y, z); return m; },
};

// ---------------------------------------------------------------------------
// Ground
// ---------------------------------------------------------------------------

const SIZE = 210, RES = 168, STEP = SIZE / RES, HALF = SIZE / 2;
const WATER_Y = -1.1;
const EYE = 1.7;

const h2 = (x, y) => {
  let h = Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
};
const vn = (x, y) => {
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  return (h2(xi, yi) * (1 - u) + h2(xi + 1, yi) * u) * (1 - v)
    + (h2(xi, yi + 1) * (1 - u) + h2(xi + 1, yi + 1) * u) * v;
};
const fbm = (x, y) => vn(x, y) * 0.6 + vn(x * 2.1, y * 2.1) * 0.26 + vn(x * 4.3, y * 4.3) * 0.14;

// Stream runs north to south; the bridge crosses it, the pond catches it.
const STREAM = [[26, 96], [18, 62], [11, 34], [5, 8], [1, -14], [8, -30], [20, -34]];
const POND = { x: 30, z: -30, r: 15 };

function sampleSpline(pts, n) {
  const out = [];
  const g = i => pts[clamp(i, 0, pts.length - 1)];
  const cr = (a, b, c, d, t) => {
    const t2 = t * t, t3 = t2 * t;
    return 0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
  };
  for (let i = 0; i < n; i++) {
    const u = (i / (n - 1)) * (pts.length - 1);
    const k = Math.min(pts.length - 2, Math.floor(u)), t = u - k;
    out.push([
      cr(g(k - 1)[0], g(k)[0], g(k + 1)[0], g(k + 2)[0], t),
      cr(g(k - 1)[1], g(k)[1], g(k + 1)[1], g(k + 2)[1], t),
    ]);
  }
  return out;
}

const streamPts = sampleSpline(STREAM, 150);
// The walkway visits the ten stations in order. The cabin and loft share a
// footprint, so the path passes the cabin once.
const walkPts = sampleSpline(STATIONS.filter(s => !s.upstairs).map(s => s.at), 260);

const nearest = (pts, x, z) => {
  let bd = Infinity, bi = 0;
  for (let i = 0; i < pts.length; i++) {
    const d = (pts[i][0] - x) ** 2 + (pts[i][1] - z) ** 2;
    if (d < bd) { bd = d; bi = i; }
  }
  return { d: Math.sqrt(bd), i: bi };
};

// Base landform, before the walkway is levelled into it.
function landform(x, z) {
  let h = fbm(x * 0.021, z * 0.021) * 7 - 1.4;
  // a rise under the overlook so station 10 genuinely looks down on the valley
  const ov = STATIONS[9].at;
  h += 9.5 * Math.exp(-((x - ov[0]) ** 2 + (z - ov[1]) ** 2) / 900);
  const st = nearest(streamPts, x, z);
  h = mix(h, WATER_Y - 1.5, smooth(9, 2.6, st.d));       // stream channel
  const pd = Math.hypot(x - POND.x, z - POND.z);
  h = mix(h, WATER_Y - 2.6, smooth(POND.r * 1.25, POND.r * 0.5, pd));
  return h;
}

// The walkway's own grade: sample the landform along it, then smooth so the
// path never jerks — the ground gets levelled to THIS, not the other way round.
const BRIDGE_AT = STATIONS[3].at;
const nearBridge = (x, z) => Math.hypot(x - BRIDGE_AT[0], z - BRIDGE_AT[1]);

const walkY = walkPts.map(([x, z]) => landform(x, z));
for (let pass = 0; pass < 26; pass++) {
  for (let i = 1; i < walkY.length - 1; i++) walkY[i] = (walkY[i - 1] + walkY[i] * 2 + walkY[i + 1]) / 4;
  // Hold the deck above the waterline at the crossing — smoothing alone drags
  // it down into the channel, and the walkway disappears under the stream.
  for (let i = 0; i < walkY.length; i++) {
    if (nearBridge(walkPts[i][0], walkPts[i][1]) < 13) walkY[i] = Math.max(walkY[i], WATER_Y + 0.9);
  }
}
const PATH_W = 2.2;   // half-width of the walkway surface

function groundHeight(x, z) {
  let h = landform(x, z);
  const w = nearest(walkPts, x, z);
  // Level a shelf under the walkway, feathering out over a few metres — but
  // NOT at the crossing, or the shelf dams the stream. There the deck spans
  // open water, which is the entire point of having a bridge.
  const span = smooth(6, 13.5, nearBridge(x, z));
  h = mix(h, walkY[w.i], smooth(PATH_W + 5.5, PATH_W + 0.4, w.d) * span);
  for (const s of STATIONS) {
    if (!s.clearing) continue;
    const d = Math.hypot(x - s.at[0], z - s.at[1]);
    if (d < s.clearing + 5) h = mix(h, s.groundY ?? h, smooth(s.clearing + 4.5, s.clearing * 0.7, d));
  }
  return h;
}

// Station ground heights come from the walkway grade beside them.
for (const s of STATIONS) {
  const w = nearest(walkPts, s.at[0], s.at[1]);
  s.groundY = walkY[w.i];
}

// ---------------------------------------------------------------------------
// Walking surface: terrain, plus the cabin's stair and balcony as overrides.
// One height per (x, z) — no multi-level ambiguity anywhere.
// ---------------------------------------------------------------------------

const cabin = STATIONS[5];
const STAIR = { x0: 5.85, x1: 7.35, z0: -2.9, z1: 2.4 };  // local to the cabin
const DECK = { x0: 3.7, x1: 7.1, z0: 0.1, z1: 2.7 };
const DECK_Y = 3.6;

function localToCabin(x, z) { return [x - cabin.at[0], z - cabin.at[1]]; }

function surfaceY(x, z) {
  const [lx, lz] = localToCabin(x, z);
  if (lx > DECK.x0 && lx < DECK.x1 && lz > DECK.z0 && lz < DECK.z1) return cabin.groundY + DECK_Y;
  if (lx > STAIR.x0 && lx < STAIR.x1 && lz > STAIR.z0 && lz < STAIR.z1) {
    return cabin.groundY + 0.35 + smooth(STAIR.z0, STAIR.z1, lz) * (DECK_Y - 0.35);
  }
  return groundHeight(x, z);
}

function walkable(x, z) {
  if (Math.abs(x) > HALF - 4 || Math.abs(z) > HALF - 4) return false;
  const [lx, lz] = localToCabin(x, z);
  if (lx > DECK.x0 - 0.3 && lx < DECK.x1 + 0.3 && lz > DECK.z0 - 0.3 && lz < DECK.z1 + 0.3) return true;
  if (lx > STAIR.x0 && lx < STAIR.x1 && lz > STAIR.z0 - 0.4 && lz < STAIR.z1 + 0.4) return true;
  if (nearest(walkPts, x, z).d < PATH_W + 1.6) return true;
  for (const s of STATIONS) {
    if (!s.clearing) continue;
    if (Math.hypot(x - s.at[0], z - s.at[1]) < s.clearing) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x8fa8bd);
scene.fog = new THREE.Fog(0x8fa8bd, 90, 260);

const camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.1, 900);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
$('stage').appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.62));
scene.add(new THREE.HemisphereLight(0xbcd4ea, 0x3f4030, 0.85));
const sun = new THREE.DirectionalLight(0xfff3dd, 2.0);
sun.position.set(-60, 90, 40);
scene.add(sun);

// --- terrain mesh ---
{
  const geo = new THREE.PlaneGeometry(SIZE, SIZE, RES, RES);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  const col = new Float32Array(pos.count * 3);
  const grass = new THREE.Color(0x4d6b3c), dry = new THREE.Color(0x6f7a44), mud = new THREE.Color(0x4a4030);
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), z = pos.getZ(i);
    const y = groundHeight(x, z);
    pos.setY(i, y);
    c.copy(grass).lerp(dry, fbm(x * 0.06, z * 0.06));
    c.lerp(mud, smooth(1.6, -1.2, y - WATER_Y));
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  geo.computeVertexNormals();
  scene.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.97 })));
}

// --- water: flood everything under the waterline ---
{
  const n = RES + 1, v = [], idx = [], seen = new Int32Array(n * n).fill(-1);
  const H = [];
  for (let j = 0; j < n; j++) for (let i = 0; i < n; i++) H.push(groundHeight(-HALF + i * STEP, -HALF + j * STEP));
  const corner = (i, j) => {
    const k = j * n + i;
    if (seen[k] < 0) { seen[k] = v.length / 3; v.push(-HALF + i * STEP, WATER_Y, -HALF + j * STEP); }
    return seen[k];
  };
  for (let j = 0; j < n - 1; j++) for (let i = 0; i < n - 1; i++) {
    if (Math.min(H[j * n + i], H[j * n + i + 1], H[(j + 1) * n + i], H[(j + 1) * n + i + 1]) >= WATER_Y) continue;
    const a = corner(i, j), b = corner(i + 1, j), cc = corner(i, j + 1), d = corner(i + 1, j + 1);
    idx.push(a, cc, b, b, cc, d);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
  const nr = new Float32Array(v.length);
  for (let i = 1; i < nr.length; i += 3) nr[i] = 1;
  g.setAttribute('normal', new THREE.BufferAttribute(nr, 3));
  g.setIndex(idx);
  scene.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({
    color: 0x3f7fa8, roughness: 0.15, metalness: 0.3, transparent: true, opacity: 0.85,
    side: THREE.DoubleSide,
  })));
}

// --- the walkway itself ---
{
  const v = [], idx = [], uv = [];
  let run = 0;
  for (let i = 0; i < walkPts.length; i++) {
    const a = walkPts[Math.max(0, i - 1)], b = walkPts[Math.min(walkPts.length - 1, i + 1)];
    const dx = b[0] - a[0], dz = b[1] - a[1], L = Math.hypot(dx, dz) || 1;
    if (i > 0) run += Math.hypot(walkPts[i][0] - walkPts[i - 1][0], walkPts[i][1] - walkPts[i - 1][1]);
    const px = -dz / L * PATH_W, pz = dx / L * PATH_W;
    const y = walkY[i] + 0.07;
    v.push(walkPts[i][0] + px, y, walkPts[i][1] + pz, walkPts[i][0] - px, y, walkPts[i][1] - pz);
    uv.push(0, run / 3, 1, run / 3);
    if (i < walkPts.length - 1) { const k = i * 2; idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(v, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  const nr = new Float32Array(v.length);
  for (let i = 1; i < nr.length; i += 3) nr[i] = 1;
  g.setAttribute('normal', new THREE.BufferAttribute(nr, 3));
  g.setIndex(idx);

  // gravel texture, drawn once
  const cv = document.createElement('canvas');
  cv.width = cv.height = 128;
  const cx = cv.getContext('2d');
  cx.fillStyle = '#b9ac93'; cx.fillRect(0, 0, 128, 128);
  for (let i = 0; i < 900; i++) {
    const t = Math.random();
    cx.fillStyle = t < 0.4 ? '#a2957c' : t < 0.75 ? '#cdc2ab' : '#8d8271';
    cx.beginPath();
    cx.arc(Math.random() * 128, Math.random() * 128, 0.7 + Math.random() * 2.1, 0, 7);
    cx.fill();
  }
  const tex = new THREE.CanvasTexture(cv);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 8;
  scene.add(new THREE.Mesh(g, new THREE.MeshStandardMaterial({ map: tex, roughness: 0.98, side: THREE.DoubleSide })));
}

// --- scatter some trees off the path so the valley reads as wooded ---
{
  const trunk = new THREE.CylinderGeometry(0.18, 0.3, 3.4, 6);
  const leaf = new THREE.ConeGeometry(1.9, 5.2, 7);
  const tm = new THREE.MeshStandardMaterial({ color: 0x4a3826, roughness: 0.95, flatShading: true });
  const lm = new THREE.MeshStandardMaterial({ color: 0x2f5330, roughness: 0.95, flatShading: true });
  const spots = [];
  let guard = 0;
  while (spots.length < 460 && guard++ < 24000) {
    const x = (Math.random() - 0.5) * (SIZE - 16), z = (Math.random() - 0.5) * (SIZE - 16);
    if (nearest(walkPts, x, z).d < 7) continue;
    if (STATIONS.some(s => s.clearing && Math.hypot(x - s.at[0], z - s.at[1]) < s.clearing + 3)) continue;
    const y = groundHeight(x, z);
    if (y < WATER_Y + 0.8) continue;
    spots.push({ x, y, z, s: 0.7 + Math.random() * 0.8, r: Math.random() * 6.3 });
  }
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), v3 = new THREE.Vector3(), s3 = new THREE.Vector3();
  for (const [geo, matl, yOff] of [[trunk, tm, 1.7], [leaf, lm, 4.6]]) {
    const im = new THREE.InstancedMesh(geo, matl, spots.length);
    spots.forEach((p, i) => {
      m4.compose(v3.set(p.x, p.y + yOff * p.s, p.z), q.setFromEuler(e.set(0, p.r, 0)), s3.setScalar(p.s));
      im.setMatrixAt(i, m4);
    });
    im.instanceMatrix.needsUpdate = true;
    scene.add(im);
  }
}

// --- stations, and the peg objects they carry ---
const PEG_H = 1.8;    // every peg normalised to this height. THE scale fix.
const spinners = [];
const stationNodes = [];

STATIONS.forEach((s, i) => {
  const g = new THREE.Group();
  g.position.set(s.at[0], s.groundY, s.at[1]);
  // The gate and the bridge are built along their local Z because you travel
  // THROUGH them — so they have to be turned to face along the walkway, or you
  // cross the bridge sideways and walk past the gate rather than under it.
  if (s.align) {
    const w = nearest(walkPts, s.at[0], s.at[1]);
    const a = walkPts[Math.max(0, w.i - 5)];
    const b = walkPts[Math.min(walkPts.length - 1, w.i + 5)];
    g.rotation.y = Math.atan2(b[0] - a[0], b[1] - a[1]);
  }
  const struct = s.build(K);
  g.add(struct);
  struct.traverse(o => { if (o.userData.spin) spinners.push(o); });

  // Presidents 1-10 ride this region. Reuse the palace's peg builders, then
  // normalise each to human scale and stand it on the station's display shelf.
  const p = PRESIDENTS[i];
  const peg = p.make(K);
  const box = new THREE.Box3().setFromObject(peg);
  const size = new THREE.Vector3();
  box.getSize(size);
  const k = PEG_H / Math.max(size.x, size.y, size.z, 0.001);
  peg.scale.setScalar(k);
  const centre = new THREE.Vector3();
  box.getCenter(centre);
  peg.position.set(
    s.display[0] - centre.x * k,
    s.display[1] - box.min.y * k,
    s.display[2] - centre.z * k);
  g.add(peg);
  scene.add(g);
  stationNodes.push({ station: s, president: p, group: g, peg });
});

// ---------------------------------------------------------------------------
// Camera: ONE continuous parameter from ground to map.
//
// `lift` 0 = standing on the walkway, 1 = looking down at the whole region.
// The scroll wheel drives it directly, so the map isn't a separate mode you
// switch into — you rise out of the valley and settle back into it.
// ---------------------------------------------------------------------------

let lift = 1;
let liftTarget = 1;
const player = new THREE.Vector3(STATIONS[0].at[0], 0, STATIONS[0].at[1] - 4);
let yaw = Math.PI, pitch = 0;
const keys = new Set();
const vel = new THREE.Vector3();

const REGION_MID = new THREE.Vector3(-6, 4, -6);
const camPos = new THREE.Vector3(), camLook = new THREE.Vector3();
const qGround = new THREE.Quaternion(), qMap = new THREE.Quaternion();
const mTmp = new THREE.Matrix4(), upV = new THREE.Vector3(0, 1, 0);

function updateCamera() {
  const e = lift * lift * (3 - 2 * lift);
  player.y = surfaceY(player.x, player.z) + EYE;

  // One path, not two blended cameras. At e=0 the eye sits at the player and
  // looks along their facing — which IS the first-person view — and at e=1 it
  // sits above the valley looking at its centre. Everything between is a
  // straight interpolation, so there is no seam to hide.
  const cp = Math.cos(pitch);
  camPos.set(
    mix(player.x, REGION_MID.x + 30, e),
    mix(player.y, 126, e),
    mix(player.z, REGION_MID.z + 92, e));
  camLook.set(
    mix(player.x - Math.sin(yaw) * cp * 10, REGION_MID.x, e),
    mix(player.y + Math.sin(pitch) * 10, REGION_MID.y, e),
    mix(player.z - Math.cos(yaw) * cp * 10, REGION_MID.z, e));

  camera.position.copy(camPos);
  mTmp.lookAt(camPos, camLook, upV);
  camera.quaternion.setFromRotationMatrix(mTmp);
  camera.fov = mix(62, 46, e);
  camera.updateProjectionMatrix();

  // Atmosphere at ground level, clarity from altitude.
  scene.fog.near = mix(90, 220, e);
  scene.fog.far = mix(260, 940, e);
}

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

const stage = $('stage');
let drag = false, lx = 0, ly = 0;
stage.addEventListener('pointerdown', e => {
  drag = true; lx = e.clientX; ly = e.clientY;
  stage.setPointerCapture(e.pointerId);
  document.body.classList.add('grabbing');
});
addEventListener('pointerup', () => { drag = false; document.body.classList.remove('grabbing'); });
addEventListener('pointermove', e => {
  if (!drag) return;
  if (lift < 0.5) {
    yaw -= (e.clientX - lx) * 0.005;
    pitch = clamp(pitch - (e.clientY - ly) * 0.005, -1.2, 1.2);
  }
  lx = e.clientX; ly = e.clientY;
});
stage.addEventListener('wheel', e => {
  e.preventDefault();
  liftTarget = clamp(liftTarget + Math.sign(e.deltaY) * 0.16, 0, 1);
}, { passive: false });

addEventListener('keydown', e => {
  if (e.code === 'KeyM') { liftTarget = liftTarget > 0.5 ? 0 : 1; return; }
  if (e.code === 'KeyQ') { quiz = !quiz; refresh(); return; }
  if (e.code === 'Space' && quiz) { e.preventDefault(); revealed = true; refresh(); return; }
  keys.add(e.code);
});
addEventListener('keyup', e => keys.delete(e.code));
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  renderer.setSize(innerWidth, innerHeight);
});

// ---------------------------------------------------------------------------
// HUD
// ---------------------------------------------------------------------------

let quiz = false, revealed = false, current = 0;

function nearestStation() {
  let bi = 0, bd = Infinity;
  stationNodes.forEach((sn, i) => {
    const d = Math.hypot(sn.station.at[0] - player.x, sn.station.at[1] - player.z);
    if (d < bd) { bd = d; bi = i; }
  });
  return { i: bi, d: bd };
}

function refresh() {
  const sn = stationNodes[current];
  const show = !quiz || revealed;
  $('st-n').textContent = sn.station.n;
  $('st-name').textContent = sn.station.name;
  $('st-blurb').textContent = sn.station.blurb;
  $('pr-name').textContent = show ? sn.president.name : '— — —';
  $('pr-peg').textContent = show ? sn.president.peg : 'name the president';
  $('pr-why').textContent = show ? sn.president.why : '';
  $('quizflag').style.display = quiz ? '' : 'none';
}

const pins = [];
STATIONS.forEach((s, i) => {
  const el = document.createElement('button');
  el.className = 'pin';
  el.textContent = s.n;
  el.onclick = () => {
    const from = i > 0 ? STATIONS[i - 1].at : [s.at[0], s.at[1] + 6];
    player.set(s.at[0], 0, s.at[1]);
    // stand back along the approach so the station is in front of you
    const dx = s.at[0] - from[0], dz = s.at[1] - from[1], L = Math.hypot(dx, dz) || 1;
    player.x -= dx / L * 6; player.z -= dz / L * 6;
    yaw = Math.atan2(-dx / L, -dz / L);
    pitch = 0;
    current = i; revealed = false;
    liftTarget = 0;
    refresh();
  };
  $('map').appendChild(el);
  pins.push({ el, s, v: new THREE.Vector3() });
});

function layoutPins() {
  camera.updateMatrixWorld(true);
  for (const p of pins) {
    // The loft shares the cabin's footprint, so pin it over its balcony
    // instead — otherwise station 6 hides exactly underneath station 7.
    p.v.set(
      p.s.pinAt ? p.s.pinAt[0] : p.s.at[0],
      (p.s.groundY ?? 0) + (p.s.pinY ?? 5),
      p.s.pinAt ? p.s.pinAt[1] : p.s.at[1]).project(camera);
    const on = p.v.z < 1 && lift > 0.12;
    p.el.style.display = on ? '' : 'none';
    if (!on) continue;
    p.el.style.left = `${(p.v.x * 0.5 + 0.5) * innerWidth}px`;
    p.el.style.top = `${(-p.v.y * 0.5 + 0.5) * innerHeight}px`;
    p.el.classList.toggle('here', p.s.n === stationNodes[current].station.n);
  }
}

// ---------------------------------------------------------------------------
// Minimap — north-up, deliberately. A rotating heading-up map is easier to
// follow in the moment but teaches you nothing; a fixed orientation is what
// builds a stable mental picture, and it matches the lifted view so the two
// reinforce each other.
// ---------------------------------------------------------------------------

const MM = 188;
const mmEl = $('minimap');
const mmCtx = mmEl.getContext('2d');
let mmStatic = null, mmB = null;

function mmPt(x, z) {
  return [(x - mmB.cx) / mmB.span * MM + MM / 2, (z - mmB.cz) / mmB.span * MM + MM / 2];
}

function mmBuild() {
  const dpr = Math.min(devicePixelRatio, 2);
  mmEl.width = MM * dpr; mmEl.height = MM * dpr;
  mmCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
  const add = (x, z) => { x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z); };
  for (const [x, z] of walkPts) add(x, z);
  for (const s of STATIONS) add(s.at[0], s.at[1]);
  mmB = { cx: (x0 + x1) / 2, cz: (z0 + z1) / 2, span: Math.max(x1 - x0, z1 - z0) + 26 };

  mmStatic = document.createElement('canvas');
  mmStatic.width = MM * dpr; mmStatic.height = MM * dpr;
  const c = mmStatic.getContext('2d');
  c.setTransform(dpr, 0, 0, dpr, 0, 0);

  c.fillStyle = '#cbd3b6'; c.fillRect(0, 0, MM, MM);

  c.strokeStyle = '#7fa8c4'; c.lineWidth = 5.5; c.lineCap = 'round'; c.lineJoin = 'round';
  c.beginPath();
  streamPts.forEach(([x, z], i) => { const [a, b] = mmPt(x, z); i ? c.lineTo(a, b) : c.moveTo(a, b); });
  c.stroke();
  const [pxx, pzz] = mmPt(POND.x, POND.z);
  c.fillStyle = '#7fa8c4';
  c.beginPath(); c.arc(pxx, pzz, POND.r / mmB.span * MM, 0, 7); c.fill();

  c.strokeStyle = '#8c7f63'; c.lineWidth = 3.2;
  c.beginPath();
  walkPts.forEach(([x, z], i) => { const [a, b] = mmPt(x, z); i ? c.lineTo(a, b) : c.moveTo(a, b); });
  c.stroke();
}

function mmDraw() {
  const vis = 1 - smooth(0.22, 0.6, lift);
  mmEl.parentElement.style.opacity = vis;
  if (vis < 0.02) return;

  mmCtx.clearRect(0, 0, MM, MM);
  mmCtx.drawImage(mmStatic, 0, 0, MM, MM);

  STATIONS.forEach((s, i) => {
    const [a, b] = mmPt(s.at[0], s.at[1]);
    const here = i === current;
    mmCtx.beginPath();
    mmCtx.arc(a + (s.upstairs ? 5 : 0), b - (s.upstairs ? 4 : 0), here ? 5.5 : 3.6, 0, 7);
    mmCtx.fillStyle = here ? '#8a5a2a' : '#f4efe4';
    mmCtx.fill();
    mmCtx.lineWidth = 1.2; mmCtx.strokeStyle = '#3a3128'; mmCtx.stroke();
    if (here) {
      mmCtx.fillStyle = '#f4efe4';
      mmCtx.font = '600 8px ui-monospace, monospace';
      mmCtx.textAlign = 'center'; mmCtx.textBaseline = 'middle';
      mmCtx.fillText(String(s.n), a, b + 0.5);
    }
  });

  const [px, py] = mmPt(player.x, player.z);
  const ang = Math.atan2(-Math.cos(yaw), -Math.sin(yaw));
  mmCtx.beginPath();
  mmCtx.moveTo(px + Math.cos(ang) * 8.5, py + Math.sin(ang) * 8.5);
  mmCtx.lineTo(px + Math.cos(ang + 2.5) * 6, py + Math.sin(ang + 2.5) * 6);
  mmCtx.lineTo(px + Math.cos(ang - 2.5) * 6, py + Math.sin(ang - 2.5) * 6);
  mmCtx.closePath();
  mmCtx.fillStyle = '#a8462f';
  mmCtx.fill();
  mmCtx.lineWidth = 1.4; mmCtx.strokeStyle = '#f4efe4'; mmCtx.stroke();
}

// ---------------------------------------------------------------------------

const clock = new THREE.Clock();
let lastStation = -1;

function frame() {
  requestAnimationFrame(frame);
  const dt = Math.min(clock.getDelta(), 0.05);
  lift += (liftTarget - lift) * (1 - Math.pow(0.002, dt));

  if (lift < 0.35) {
    const speed = keys.has('ShiftLeft') || keys.has('ShiftRight') ? 17 : 8;
    const fwd = (keys.has('KeyW') || keys.has('ArrowUp') ? 1 : 0) - (keys.has('KeyS') || keys.has('ArrowDown') ? 1 : 0);
    const str = (keys.has('KeyD') ? 1 : 0) - (keys.has('KeyA') ? 1 : 0);
    yaw -= ((keys.has('ArrowRight') ? 1 : 0) - (keys.has('ArrowLeft') ? 1 : 0)) * dt * 1.9;
    const wantV = new THREE.Vector3(
      Math.sin(yaw) * -fwd + Math.cos(yaw) * str, 0,
      Math.cos(yaw) * -fwd - Math.sin(yaw) * str);
    if (wantV.lengthSq() > 0) wantV.normalize().multiplyScalar(speed);
    vel.lerp(wantV, 1 - Math.pow(0.0015, dt));
    const nx = player.x + vel.x * dt;
    if (walkable(nx, player.z)) player.x = nx; else vel.x = 0;
    const nz = player.z + vel.z * dt;
    if (walkable(player.x, nz)) player.z = nz; else vel.z = 0;

    const ns = nearestStation();
    if (ns.d < 11 && ns.i !== lastStation) { lastStation = ns.i; current = ns.i; revealed = false; refresh(); }
  }

  for (const s of spinners) s.rotation.x += dt * 0.55;
  updateCamera();
  layoutPins();
  mmDraw();
  $('hud').classList.toggle('up', lift > 0.55);
  renderer.render(scene, camera);
}

$('enter').onclick = () => { $('intro').style.display = 'none'; };
$('to-map').onclick = () => { liftTarget = 1; };
$('to-ground').onclick = () => { liftTarget = 0; };

mmBuild();
refresh();
frame();
window.__walkway = { STATIONS, player, walkable, surfaceY, get lift() { return lift; } };
