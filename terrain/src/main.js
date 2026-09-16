import * as THREE from 'three';
import {
  BIOMES, SIZE, RES, WATER_Y, REGION_KEYS, REGION_COUNTS,
  generate, placeSites, scatterProps, heightAt, biomeAtWorld,
} from './world.js';

const $ = id => document.getElementById(id);

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0b0e14);
scene.fog = new THREE.Fog(0x0b0e14, 420, 900);

const camera = new THREE.PerspectiveCamera(42, innerWidth / innerHeight, 1, 2200);
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
$('stage').appendChild(renderer.domElement);

scene.add(new THREE.AmbientLight(0xffffff, 0.5));
scene.add(new THREE.HemisphereLight(0x9fb4d8, 0x2a2620, 0.75));
const sun = new THREE.DirectionalLight(0xfff0d8, 2.3);
sun.position.set(-0.5, 1.05, 0.42).multiplyScalar(300);
scene.add(sun);

// ---------------------------------------------------------------------------
// Build
// ---------------------------------------------------------------------------

let world = null, siteData = null;
const built = new THREE.Group();
scene.add(built);

const geoFor = p => {
  switch (p.kind) {
    case 'cone': return new THREE.ConeGeometry(p.a, p.c, 7);
    case 'cyl': return new THREE.CylinderGeometry(p.a, p.b ?? p.a, p.c, 7);
    case 'box': return new THREE.BoxGeometry(p.a, p.b, p.c);
    case 'sph': return new THREE.SphereGeometry(p.a, 8, 6);
    default: return new THREE.IcosahedronGeometry(p.a, p.detail ?? 0);
  }
};

function disposeAll(obj) {
  obj.traverse(o => {
    if (o.geometry) o.geometry.dispose();
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose());
  });
  obj.clear();
}

const layers = { props: true, water: true, sites: true, wire: false };
let terrainMesh = null, propGroup = null, waterGroup = null, markerGroup = null;

function build(seed) {
  disposeAll(built);
  const t0 = performance.now();
  world = generate(seed);
  siteData = placeSites(world);

  // --- terrain ---
  const n = world.n;
  const geo = new THREE.PlaneGeometry(SIZE, SIZE, RES, RES);
  geo.rotateX(-Math.PI / 2);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i++) pos.setY(i, world.height[i]);
  geo.setAttribute('color', new THREE.BufferAttribute(world.color, 3));
  geo.computeVertexNormals();
  terrainMesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
    vertexColors: true, roughness: 0.95, metalness: 0, flatShading: false,
  }));
  built.add(terrainMesh);

  // --- water: lake disc + river ribbon ---
  waterGroup = new THREE.Group();
  const waterMat = new THREE.MeshStandardMaterial({
    color: 0x2e7fbe, roughness: 0.22, metalness: 0.18,
    transparent: true, opacity: 0.82,
    side: THREE.DoubleSide, // the river ribbon's winding follows the spline's turns
  });
  // Standing water is a FLOOD of the heightfield, not a disc: emit a quad for
  // every cell with a corner below the waterline. That fits the lake basin
  // exactly instead of a circle spilling over ground that rises past it.
  {
    const nn = world.n, st = world.step, hf = world.half;
    const wv = [], wi = [], seen = new Int32Array(nn * nn).fill(-1);
    const corner = (i, j) => {
      const k = j * nn + i;
      if (seen[k] < 0) { seen[k] = wv.length / 3; wv.push(-hf + i * st, WATER_Y, -hf + j * st); }
      return seen[k];
    };
    for (let j = 0; j < nn - 1; j++) {
      for (let i = 0; i < nn - 1; i++) {
        const h = world.height;
        if (Math.min(h[j * nn + i], h[j * nn + i + 1], h[(j + 1) * nn + i], h[(j + 1) * nn + i + 1]) >= WATER_Y) continue;
        const a = corner(i, j), b = corner(i + 1, j), c = corner(i, j + 1), d = corner(i + 1, j + 1);
        wi.push(a, c, b, b, c, d);
      }
    }
    if (wv.length) {
      const wg = new THREE.BufferGeometry();
      wg.setAttribute('position', new THREE.Float32BufferAttribute(wv, 3));
      const nrm = new Float32Array(wv.length);
      for (let i = 1; i < nrm.length; i += 3) nrm[i] = 1;   // flat water, straight up
      wg.setAttribute('normal', new THREE.BufferAttribute(nrm, 3));
      wg.setIndex(wi);
      waterGroup.add(new THREE.Mesh(wg, waterMat));
    }
  }

  // Ribbon: two vertices per spline sample, offset perpendicular to flow.
  const R = world.river;
  const verts = [], idx = [];
  for (let i = 0; i < R.length; i++) {
    const a = R[Math.max(0, i - 1)], b = R[Math.min(R.length - 1, i + 1)];
    const dx = b.x - a.x, dz = b.z - a.z;
    const L = Math.hypot(dx, dz) || 1;
    // Half the channel width — the carve only reaches full depth well inside
    // `w`, so a full-width ribbon would ride up onto the banks.
    const px = -dz / L * R[i].w * 0.5, pz = dx / L * R[i].w * 0.5;
    const y = Math.max(WATER_Y + 0.05, R[i].bed + 1.7);
    verts.push(R[i].x + px, y, R[i].z + pz, R[i].x - px, y, R[i].z - pz);
    if (i < R.length - 1) {
      const k = i * 2;
      idx.push(k, k + 1, k + 2, k + 1, k + 3, k + 2);
    }
  }
  const rg = new THREE.BufferGeometry();
  rg.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  rg.setIndex(idx);
  // Force normals straight up rather than deriving them — a spline that curves
  // back on itself flips triangle winding, which flips the derived normal.
  const rn = new Float32Array(verts.length);
  for (let i = 1; i < rn.length; i += 3) rn[i] = 1;
  rg.setAttribute('normal', new THREE.BufferAttribute(rn, 3));
  waterGroup.add(new THREE.Mesh(rg, waterMat));
  built.add(waterGroup);

  // --- props, one InstancedMesh per part of each prop type ---
  propGroup = new THREE.Group();
  const scattered = scatterProps(world);
  let instances = 0;
  const m = new THREE.Matrix4(), local = new THREE.Matrix4();
  const q = new THREE.Quaternion(), e = new THREE.Euler();
  const v = new THREE.Vector3(), s3 = new THREE.Vector3();
  for (const group of scattered) {
    for (const part of group.parts) {
      const im = new THREE.InstancedMesh(
        geoFor(part),
        new THREE.MeshStandardMaterial({
          color: part.color, roughness: 0.88, metalness: 0,
          emissive: part.e ?? 0x000000, emissiveIntensity: part.e ? 0.9 : 0,
          flatShading: true,
        }),
        group.placements.length);
      const pr = part.r ?? [0, 0, 0];
      local.compose(
        v.set(part.p[0], part.p[1], part.p[2]),
        q.setFromEuler(e.set(pr[0], pr[1], pr[2])),
        s3.set(1, 1, 1));
      group.placements.forEach((p, i) => {
        m.compose(
          v.set(p.x, p.y, p.z),
          q.setFromEuler(e.set(0, p.rot, 0)),
          s3.set(p.scale, p.scale, p.scale));
        im.setMatrixAt(i, m.multiply(local));
      });
      im.instanceMatrix.needsUpdate = true;
      im.frustumCulled = false;
      propGroup.add(im);
      instances += group.placements.length;
    }
  }
  built.add(propGroup);

  // --- site markers ---
  markerGroup = new THREE.Group();
  const postGeo = new THREE.CylinderGeometry(0.5, 0.5, 11, 6);
  const capGeo = new THREE.OctahedronGeometry(2.1, 0);
  siteData.sites.forEach(site => {
    const hue = REGION_TINT[site.region];
    const g = new THREE.Group();
    g.add(new THREE.Mesh(postGeo, new THREE.MeshStandardMaterial({ color: 0x1a1f28, roughness: 0.7 })));
    const cap = new THREE.Mesh(capGeo, new THREE.MeshStandardMaterial({
      color: hue, emissive: hue, emissiveIntensity: 0.85, roughness: 0.4,
    }));
    cap.position.y = 7.2;
    g.add(cap);
    g.position.set(site.x, site.y + 5.5, site.z);
    markerGroup.add(g);
  });
  built.add(markerGroup);

  applyLayers();
  buildLegend();
  buildPins();
  $('stat-time').textContent = `${Math.round(performance.now() - t0)} ms`;
  $('stat-inst').textContent = instances.toLocaleString();
  $('stat-verts').textContent = (n * n).toLocaleString();
  $('seedval').textContent = seed;
}

const REGION_TINT = {
  alpine: 0x9fb6d4, forest: 0x5cc46a, winter: 0xa8e6ff,
  desert: 0xf0c05a, future: 0xff6ba8,
};

function applyLayers() {
  propGroup.visible = layers.props;
  waterGroup.visible = layers.water;
  markerGroup.visible = layers.sites;
  terrainMesh.material.wireframe = layers.wire;
  $('map').style.display = layers.sites ? '' : 'none';
}

// ---------------------------------------------------------------------------
// Camera: orbit, pitched by default
// ---------------------------------------------------------------------------

const RAIL = 306;
const orbit = { radius: 620, theta: -0.7, phi: 0.95, target: new THREE.Vector3(0, 6, 0) };

// Reserve the rail's width by shifting the projection frustum rather than the
// target — a world-space offset would swing around as you orbit, this doesn't.
function applyViewOffset() {
  const gutter = innerWidth < 820 ? 0 : RAIL;
  camera.setViewOffset(innerWidth, innerHeight, -gutter / 2, 0, innerWidth, innerHeight);
}

// Distance at which the whole map fits the viewport minus the rail.
function fitRadius(pad = 1.12) {
  const gutter = innerWidth < 820 ? 0 : RAIL;
  const halfV = Math.tan((camera.fov / 2) * Math.PI / 180);
  const usable = Math.max(0.35, (innerWidth - gutter) / innerHeight);
  return Math.max(SIZE * pad / (2 * halfV), SIZE * pad / (2 * halfV * usable));
}

function applyCamera() {
  const { radius, theta, phi } = orbit;
  camera.position.set(
    orbit.target.x + radius * Math.sin(phi) * Math.cos(theta),
    orbit.target.y + radius * Math.cos(phi),
    orbit.target.z + radius * Math.sin(phi) * Math.sin(theta));
  camera.lookAt(orbit.target);
}

const stage = $('stage');
let drag = false, lx = 0, ly = 0;
stage.addEventListener('pointerdown', e => { drag = true; lx = e.clientX; ly = e.clientY; stage.setPointerCapture(e.pointerId); });
stage.addEventListener('pointerup', e => { drag = false; stage.releasePointerCapture(e.pointerId); });
stage.addEventListener('pointermove', e => {
  if (drag) {
    orbit.theta -= (e.clientX - lx) * 0.005;
    orbit.phi = Math.max(0.06, Math.min(1.45, orbit.phi - (e.clientY - ly) * 0.005));
    lx = e.clientX; ly = e.clientY;
  }
  hover(e.clientX, e.clientY);
});
stage.addEventListener('wheel', e => {
  e.preventDefault();
  orbit.radius = Math.max(90, Math.min(900, orbit.radius * (1 + Math.sign(e.deltaY) * 0.09)));
}, { passive: false });

function setView(phi, radius) {
  const t0 = performance.now(), fromPhi = orbit.phi, fromR = orbit.radius;
  (function step() {
    const k = Math.min(1, (performance.now() - t0) / 700);
    const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
    orbit.phi = fromPhi + (phi - fromPhi) * e;
    orbit.radius = fromR + (radius - fromR) * e;
    if (k < 1) requestAnimationFrame(step);
  })();
}

// ---------------------------------------------------------------------------
// Readout + site pins
// ---------------------------------------------------------------------------

const ray = new THREE.Raycaster();
const ndc = new THREE.Vector2();
let lastHover = 0;

function hover(cx, cy) {
  if (performance.now() - lastHover < 60 || !terrainMesh) return;
  lastHover = performance.now();
  ndc.set((cx / innerWidth) * 2 - 1, -(cy / innerHeight) * 2 + 1);
  ray.setFromCamera(ndc, camera);
  const hit = ray.intersectObject(terrainMesh, false)[0];
  if (!hit) { $('read-biome').textContent = '—'; $('read-elev').textContent = '—'; $('read-pos').textContent = '—'; return; }
  const b = biomeAtWorld(world, hit.point.x, hit.point.z);
  $('read-biome').textContent = b.name;
  $('read-elev').textContent = `${hit.point.y.toFixed(1)} m`;
  $('read-pos').textContent = `${hit.point.x.toFixed(0)}, ${hit.point.z.toFixed(0)}`;
}

const pins = [];
function buildPins() {
  const map = $('map');
  map.innerHTML = '';
  pins.length = 0;
  siteData.sites.forEach(site => {
    const el = document.createElement('div');
    el.className = `pin r-${site.region}`;
    el.textContent = site.n;
    el.title = `${site.n} · ${BIOMES.find(b => b.key === site.region).name}`;
    map.appendChild(el);
    pins.push({ el, site, v: new THREE.Vector3() });
  });
}

function layoutPins() {
  camera.updateMatrixWorld(true);
  for (const p of pins) {
    p.v.set(p.site.x, p.site.y + 13, p.site.z).project(camera);
    const on = p.v.z < 1;
    p.el.style.display = on ? '' : 'none';
    if (!on) continue;
    p.el.style.left = `${(p.v.x * 0.5 + 0.5) * innerWidth}px`;
    p.el.style.top = `${(-p.v.y * 0.5 + 0.5) * innerHeight}px`;
  }
}

function buildLegend() {
  const rl = $('regions');
  rl.innerHTML = '';
  let from = 1;
  siteData.route.forEach((key, i) => {
    const b = BIOMES.find(x => x.key === key);
    const to = from + REGION_COUNTS[i] - 1;
    const row = document.createElement('div');
    row.className = 'reg';
    row.innerHTML =
      `<span class="sw" style="background:#${REGION_TINT[key].toString(16).padStart(6, '0')}"></span>` +
      `<span class="rn">${b.name}</span>` +
      `<span class="rr">${from}–${to}</span>`;
    row.title = b.note;
    rl.appendChild(row);
    from = to + 1;
  });

  const wl = $('wilds');
  wl.innerHTML = '';
  BIOMES.filter(b => !REGION_KEYS.includes(b.key)).forEach(b => {
    const row = document.createElement('div');
    row.className = 'wild';
    row.innerHTML =
      `<span class="sw" style="background:#${b.color.toString(16).padStart(6, '0')}"></span>` +
      `<span class="rn">${b.name}</span>` +
      `<span class="rr">${((world.coverage[b.key] || 0) * 100).toFixed(0)}%</span>`;
    row.title = b.note;
    wl.appendChild(row);
  });
}

// ---------------------------------------------------------------------------

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  applyViewOffset();
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

function frame() {
  requestAnimationFrame(frame);
  applyCamera();
  if (layers.sites) layoutPins();
  renderer.render(scene, camera);
}

$('regen').onclick = () => build(Math.floor(Math.random() * 100000));
$('v-plan').onclick = () => setView(0.08, fitRadius(1.12));
$('v-pitch').onclick = () => setView(0.95, fitRadius(1.18));
$('v-low').onclick = () => setView(1.36, fitRadius(0.62));
for (const k of ['props', 'water', 'sites', 'wire']) {
  $(`t-${k}`).onclick = ev => {
    layers[k] = !layers[k];
    ev.currentTarget.classList.toggle('off', !layers[k]);
    applyLayers();
  };
}

applyViewOffset();
orbit.radius = fitRadius(1.18);
build(7);
frame();

window.__terrain = { get world() { return world; }, get sites() { return siteData; }, orbit, camera, BIOMES };
