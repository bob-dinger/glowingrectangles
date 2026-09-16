// ---------------------------------------------------------------------------
// World generation. Pure data — no THREE in this file, so it can be reasoned
// about (and tested) on its own. main.js turns the output into meshes.
//
// Pipeline:
//   1. scatter biome seeds on a jittered grid, assign a biome to each
//   2. per vertex, find the two nearest seeds through a WARPED lookup, so
//      region borders are organic rather than straight Voronoi edges
//   3. blend the two biomes' height rules -> elevation
//   4. carve a river from the alpine seed down to the lake, and a lake basin
//   5. colour by biome, then modulate by slope, snowline and shoreline
//   6. scatter props, rejecting water, steep slopes and the river channel
// ---------------------------------------------------------------------------

export const SIZE = 420;     // world units across
export const RES = 200;      // grid segments (RES+1 squared vertices)
export const WATER_Y = 0;    // sea/lake surface height
const BLEND = 26;            // biome border softness, world units

// --- noise -----------------------------------------------------------------

export function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hash2(x, y, seed) {
  let h = Math.imul(x | 0, 374761393) ^ Math.imul(y | 0, 668265263) ^ Math.imul(seed | 0, 1274126177);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

function vnoise(x, y, seed) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash2(xi, yi, seed), b = hash2(xi + 1, yi, seed);
  const c = hash2(xi, yi + 1, seed), d = hash2(xi + 1, yi + 1, seed);
  return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v;
}

export function fbm(x, y, seed, oct = 5) {
  let sum = 0, amp = 1, f = 1, norm = 0;
  for (let i = 0; i < oct; i++) {
    sum += amp * vnoise(x * f, y * f, seed + i * 131);
    norm += amp; amp *= 0.5; f *= 2;
  }
  return sum / norm;
}

function ridged(x, y, seed, oct = 5) {
  let sum = 0, amp = 1, f = 1, norm = 0;
  for (let i = 0; i < oct; i++) {
    const n = 1 - Math.abs(vnoise(x * f, y * f, seed + i * 271) * 2 - 1);
    sum += amp * n * n;
    norm += amp; amp *= 0.5; f *= 2;
  }
  return sum / norm;
}

const clamp01 = v => v < 0 ? 0 : v > 1 ? 1 : v;
const smooth = (a, b, t) => { const x = clamp01((t - a) / (b - a)); return x * x * (3 - 2 * x); };
const mix = (a, b, t) => a + (b - a) * t;

// --- biomes ----------------------------------------------------------------
// base   baseline elevation      amp   noise amplitude
// freq   noise frequency         style how the surface is shaped
// props  scatter rules; parts are shape descriptors main.js turns into geometry

const tree = (trunk, canopy, h, r, layers = 3) => {
  const parts = [{ kind: 'cyl', a: r * 0.16, b: r * 0.22, c: h * 0.42, color: trunk, p: [0, h * 0.21, 0] }];
  for (let i = 0; i < layers; i++) {
    const t = i / layers;
    parts.push({
      kind: 'cone', a: r * (1 - t * 0.45), c: h * 0.52,
      color: canopy, p: [0, h * (0.36 + t * 0.24), 0],
    });
  }
  return parts;
};

const broadleaf = (trunk, canopy, h, r) => [
  { kind: 'cyl', a: r * 0.13, b: r * 0.19, c: h * 0.6, color: trunk, p: [0, h * 0.3, 0] },
  { kind: 'ico', a: r, color: canopy, p: [0, h * 0.78, 0] },
  { kind: 'ico', a: r * 0.68, color: canopy, p: [r * 0.6, h * 0.62, r * 0.2] },
  { kind: 'ico', a: r * 0.6, color: canopy, p: [-r * 0.5, h * 0.66, -r * 0.35] },
];

const rock = (color, s) => [
  { kind: 'ico', a: s, color, p: [0, s * 0.55, 0], r: [0.4, 0.8, 0.2], detail: 0 },
];

export const BIOMES = [
  {
    key: 'alpine', name: 'Alpine Peaks', note: 'Ridged granite above the snowline. The river starts here.',
    color: 0x6d7686, rock: 0x8b93a1, base: 18, amp: 84, freq: 0.010, style: 'ridged',
    props: [
      { parts: tree(0x3a2f26, 0x1f3a2c, 7, 1.7, 3), density: 0.35, maxSlope: 0.55, maxY: 42, scale: [0.7, 1.2] },
      { parts: rock(0x8b93a1, 2.4), density: 0.5, maxSlope: 1, scale: [0.5, 1.8] },
    ],
  },
  {
    key: 'forest', name: 'Boreal Forest', note: 'Dense conifer cover on rolling ground.',
    color: 0x2f4a30, rock: 0x59614f, base: 7, amp: 13, freq: 0.016, style: 'fbm',
    props: [
      { parts: tree(0x3d2f22, 0x24462a, 9, 2.1, 4), density: 2.6, maxSlope: 0.7, scale: [0.75, 1.35] },
      { parts: rock(0x59614f, 1.4), density: 0.3, maxSlope: 1, scale: [0.5, 1.4] },
    ],
  },
  {
    key: 'winter', name: 'Winter Tundra', note: 'Snowpack, frozen pools, skeletal trees.',
    color: 0xd8e2ec, rock: 0xa9b6c4, base: 6, amp: 11, freq: 0.014, style: 'fbm',
    props: [
      { parts: tree(0x4a4a52, 0xdfe8f2, 7.5, 1.8, 3), density: 1.1, maxSlope: 0.7, scale: [0.7, 1.2] },
      {
        parts: [{ kind: 'cone', a: 0.9, c: 3.4, color: 0xbfe4f4, e: 0x2a6a8a, p: [0, 1.7, 0] }],
        density: 0.5, maxSlope: 0.5, scale: [0.5, 1.3],
      },
    ],
  },
  {
    key: 'desert', name: 'Sand Sea', note: 'Wind-built dunes; the only true ergs on the map.',
    color: 0xd9b476, rock: 0xb08b52, base: 3, amp: 9, freq: 0.020, style: 'dunes',
    props: [
      {
        parts: [
          { kind: 'cyl', a: 0.55, b: 0.65, c: 4.4, color: 0x3f6b40, p: [0, 2.2, 0] },
          { kind: 'cyl', a: 0.34, b: 0.34, c: 2.0, color: 0x3f6b40, p: [1.0, 2.6, 0], r: [0, 0, -1.1] },
          { kind: 'cyl', a: 0.34, b: 0.34, c: 1.7, color: 0x3f6b40, p: [-0.9, 3.1, 0], r: [0, 0, 1.1] },
        ],
        density: 0.3, maxSlope: 0.4, scale: [0.7, 1.4],
      },
      { parts: rock(0xb08b52, 1.2), density: 0.35, maxSlope: 1, scale: [0.4, 1.5] },
    ],
  },
  {
    key: 'mesa', name: 'Red Mesa', note: 'Terraced sandstone — height quantised into steps.',
    color: 0xb5623a, rock: 0x8c4526, base: 11, amp: 22, freq: 0.011, style: 'terrace',
    props: [
      {
        parts: [
          { kind: 'cyl', a: 3.0, b: 3.6, c: 7.0, color: 0xa95531, p: [0, 3.5, 0] },
          { kind: 'cyl', a: 3.2, b: 3.0, c: 1.1, color: 0x8c4526, p: [0, 7.4, 0] },
        ],
        density: 0.06, maxSlope: 0.35, scale: [0.7, 2.2],
      },
      { parts: rock(0x8c4526, 1.5), density: 0.5, maxSlope: 1, scale: [0.4, 1.5] },
    ],
  },
  {
    key: 'volcanic', name: 'Volcanic Waste', note: 'Cinder cones and cooling fissures.',
    color: 0x2b2725, rock: 0x4a4340, base: 9, amp: 20, freq: 0.017, style: 'ridged',
    props: [
      {
        parts: [
          { kind: 'cone', a: 4.2, c: 6.0, color: 0x241f1d, p: [0, 3.0, 0] },
          { kind: 'cyl', a: 1.5, b: 2.0, c: 0.8, color: 0xff5a1e, e: 0xff4a10, p: [0, 5.9, 0] },
        ],
        density: 0.14, maxSlope: 0.5, scale: [0.6, 1.8],
      },
      {
        parts: [{ kind: 'ico', a: 1.1, color: 0x7a2a12, e: 0xd83a10, p: [0, 0.5, 0], detail: 0 }],
        density: 0.5, maxSlope: 1, scale: [0.4, 1.2],
      },
    ],
  },
  {
    key: 'steppe', name: 'Golden Steppe', note: 'Open grassland, a few deep-rooted trees.',
    color: 0xb9a45a, rock: 0x8d7c4a, base: 4, amp: 7, freq: 0.013, style: 'fbm',
    props: [
      { parts: broadleaf(0x5a4a32, 0x6f7a3a, 9, 3.2), density: 0.22, maxSlope: 0.5, scale: [0.8, 1.4] },
      {
        parts: [{ kind: 'cone', a: 0.7, c: 1.6, color: 0xa89a58, p: [0, 0.8, 0] }],
        density: 2.2, maxSlope: 0.6, scale: [0.6, 1.4],
      },
    ],
  },
  {
    key: 'wetland', name: 'Marshland', note: 'Barely above the waterline; standing pools and reeds.',
    color: 0x4a5a3a, rock: 0x3d4a34, base: 1.4, amp: 3.2, freq: 0.022, style: 'fbm',
    props: [
      {
        parts: [
          { kind: 'cyl', a: 0.1, b: 0.14, c: 3.2, color: 0x7a8a46, p: [0, 1.6, 0] },
          { kind: 'cyl', a: 0.1, b: 0.14, c: 2.6, color: 0x8a9450, p: [0.5, 1.3, 0.3], r: [0.1, 0, 0.15] },
          { kind: 'cyl', a: 0.1, b: 0.14, c: 2.9, color: 0x6f8040, p: [-0.4, 1.45, 0.4], r: [0, 0, -0.12] },
        ],
        density: 3.4, maxSlope: 0.4, scale: [0.6, 1.4],
      },
      {
        parts: [
          { kind: 'cyl', a: 0.16, b: 0.3, c: 6.0, color: 0x4a4038, p: [0, 3.0, 0] },
          { kind: 'cyl', a: 0.08, b: 0.1, c: 2.2, color: 0x4a4038, p: [0.8, 4.6, 0], r: [0, 0, -0.9] },
        ],
        density: 0.3, maxSlope: 0.5, scale: [0.7, 1.3],
      },
    ],
  },
  {
    key: 'jungle', name: 'Rainforest', note: 'Closed canopy, highest prop density on the map.',
    color: 0x1f4a2a, rock: 0x3a5236, base: 5, amp: 10, freq: 0.024, style: 'fbm',
    props: [
      { parts: broadleaf(0x4a3a28, 0x1e5c30, 13, 3.6), density: 2.0, maxSlope: 0.7, scale: [0.8, 1.5] },
      { parts: broadleaf(0x3f3222, 0x2f7a3e, 7, 2.4), density: 1.6, maxSlope: 0.8, scale: [0.7, 1.2] },
    ],
  },
  {
    key: 'farm', name: 'Farmland', note: 'Flattened and worked — the most human terrain here.',
    color: 0x7f8a46, rock: 0x6b6a3f, base: 3, amp: 3.6, freq: 0.009, style: 'fbm',
    props: [
      {
        parts: [
          { kind: 'box', a: 6, b: 4, c: 9, color: 0x8c3a30, p: [0, 2, 0] },
          { kind: 'box', a: 6.4, b: 1.0, c: 9.4, color: 0xd8d2c4, p: [0, 4.2, 0] },
        ],
        density: 0.05, maxSlope: 0.25, scale: [0.7, 1.2],
      },
      {
        parts: [
          { kind: 'cyl', a: 1.5, b: 1.5, c: 8, color: 0xc9c2b0, p: [0, 4, 0] },
          { kind: 'cone', a: 1.7, c: 2.2, color: 0x8a8578, p: [0, 9.1, 0] },
        ],
        density: 0.05, maxSlope: 0.25, scale: [0.7, 1.3],
      },
    ],
  },
  {
    key: 'ruins', name: 'Ancient Ruins', note: 'Toppled colonnades going back to moss.',
    color: 0x8a8b78, rock: 0x9a9a86, base: 5, amp: 8, freq: 0.015, style: 'fbm',
    props: [
      {
        parts: [
          { kind: 'cyl', a: 0.8, b: 0.9, c: 9, color: 0xb8b6a2, p: [0, 4.5, 0] },
          { kind: 'box', a: 2.4, b: 0.7, c: 2.4, color: 0xc4c2ae, p: [0, 9.2, 0] },
        ],
        density: 0.5, maxSlope: 0.4, scale: [0.5, 1.3],
      },
      {
        parts: [{ kind: 'box', a: 2.0, b: 7.0, c: 1.2, color: 0xa8a692, p: [0, 3.5, 0], r: [0.1, 0.6, 0.28] }],
        density: 0.4, maxSlope: 0.5, scale: [0.6, 1.4],
      },
    ],
  },
  {
    key: 'future', name: 'Arcology', note: 'Levelled ground, lit towers, hard edges.',
    color: 0x33384a, rock: 0x454b5e, base: 3.4, amp: 2.2, freq: 0.010, style: 'flat',
    props: [
      {
        parts: [
          { kind: 'box', a: 4.5, b: 26, c: 4.5, color: 0x2a3040, p: [0, 13, 0] },
          { kind: 'box', a: 4.9, b: 1.0, c: 4.9, color: 0x4ad8f0, e: 0x2ab8d8, p: [0, 20, 0] },
          { kind: 'box', a: 4.9, b: 0.7, c: 4.9, color: 0x4ad8f0, e: 0x2ab8d8, p: [0, 9, 0] },
          { kind: 'box', a: 1.2, b: 5, c: 1.2, color: 0x3a4152, p: [0, 28, 0] },
        ],
        density: 0.16, maxSlope: 0.3, scale: [0.5, 1.9],
      },
      {
        parts: [
          { kind: 'cyl', a: 0.35, b: 0.35, c: 12, color: 0x3a4152, p: [0, 6, 0] },
          { kind: 'sph', a: 0.8, color: 0xff5a8a, e: 0xff3a70, p: [0, 12.4, 0] },
        ],
        density: 0.4, maxSlope: 0.4, scale: [0.6, 1.4],
      },
    ],
  },
];

// --- height rules ----------------------------------------------------------

function shape(b, x, z, seed) {
  const f = b.freq;
  switch (b.style) {
    case 'ridged': return ridged(x * f, z * f, seed);
    case 'terrace': {
      const n = fbm(x * f, z * f, seed);
      return (Math.floor(n * 5) / 5) * 0.82 + n * 0.18;
    }
    case 'dunes': {
      const drift = fbm(x * f * 0.4, z * f * 0.4, seed + 17);
      return 0.5 + 0.5 * Math.sin(x * f * 3.1 + drift * 9);
    }
    case 'flat': return fbm(x * f, z * f, seed) * 0.35;
    default: return fbm(x * f, z * f, seed);
  }
}

// --- the build -------------------------------------------------------------

export function generate(seed) {
  const rand = rng(seed);
  const half = SIZE / 2;

  // 1 · biome seeds on a jittered 4x3 grid
  const cols = 4, rows = 3;
  const seeds = [];
  const order = BIOMES.map((_, i) => i);
  for (let i = order.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const cw = SIZE / cols, ch = SIZE / rows;
      seeds.push({
        x: -half + cw * (c + 0.5) + (rand() - 0.5) * cw * 0.55,
        z: -half + ch * (r + 0.5) + (rand() - 0.5) * ch * 0.55,
        b: order[seeds.length % order.length],
      });
    }
  }

  const biomeAt = i => BIOMES[seeds[i].b];
  const alpineSeed = seeds.findIndex(s => BIOMES[s.b].key === 'alpine');
  const source = seeds[alpineSeed >= 0 ? alpineSeed : 0];

  // 2 · lake goes in the lowest-lying region far from the river source
  const lowKeys = ['wetland', 'farm', 'steppe', 'forest'];
  let lakeSeed = -1, bestScore = -Infinity;
  seeds.forEach((s, i) => {
    if (i === alpineSeed) return;
    const d = Math.hypot(s.x - source.x, s.z - source.z);
    const bonus = lowKeys.includes(BIOMES[s.b].key) ? 160 : 0;
    if (d + bonus > bestScore) { bestScore = d + bonus; lakeSeed = i; }
  });
  const lake = { x: seeds[lakeSeed].x, z: seeds[lakeSeed].z, r: 46 };

  // 3 · river spline: source -> lake, with perpendicular meander
  const ctrl = [];
  const N = 7;
  const dx = lake.x - source.x, dz = lake.z - source.z;
  const len = Math.hypot(dx, dz) || 1;
  const px = -dz / len, pz = dx / len;
  for (let i = 0; i <= N; i++) {
    const t = i / N;
    const wob = i === 0 || i === N ? 0 : (rand() - 0.5) * 92;
    ctrl.push({ x: source.x + dx * t + px * wob, z: source.z + dz * t + pz * wob });
  }
  // Catmull-Rom sampled densely; each sample carries its own descent height.
  const river = [];
  const SAMPLES = 260;
  const cr = (p0, p1, p2, p3, t) => {
    const t2 = t * t, t3 = t2 * t;
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
  };
  for (let i = 0; i < SAMPLES; i++) {
    const u = (i / (SAMPLES - 1)) * (ctrl.length - 1);
    const k = Math.min(ctrl.length - 2, Math.floor(u));
    const t = u - k;
    const g = j => ctrl[Math.max(0, Math.min(ctrl.length - 1, j))];
    const x = cr(g(k - 1).x, g(k).x, g(k + 1).x, g(k + 2).x, t);
    const z = cr(g(k - 1).z, g(k).z, g(k + 1).z, g(k + 2).z, t);
    const s = i / (SAMPLES - 1);
    river.push({
      x, z, t: s,
      bed: mix(34, WATER_Y - 1.2, Math.pow(s, 0.62)),   // monotonic descent
      w: mix(5, 15, s),                                  // widens downstream
    });
  }

  // 4 · rasterise
  const n = RES + 1;
  const height = new Float32Array(n * n);
  const biome = new Uint8Array(n * n);
  const color = new Float32Array(n * n * 3);   // blended ground colour
  const rockCol = new Float32Array(n * n * 3); // blended exposed-rock colour
  const step = SIZE / RES;
  const ch = (hex, sh) => ((hex >> sh) & 255) / 255;

  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const x = -half + i * step, z = -half + j * step;

      // warped nearest-two biome lookup
      const wx = x + (fbm(x * 0.0055, z * 0.0055, seed + 91) - 0.5) * 110;
      const wz = z + (fbm(x * 0.0055 + 31, z * 0.0055 + 17, seed + 77) - 0.5) * 110;
      let i1 = 0, d1 = Infinity, i2 = 0, d2 = Infinity;
      for (let k = 0; k < seeds.length; k++) {
        const d = Math.hypot(seeds[k].x - wx, seeds[k].z - wz);
        if (d < d1) { d2 = d1; i2 = i1; d1 = d; i1 = k; }
        else if (d < d2) { d2 = d; i2 = k; }
      }
      const w1 = 0.5 + 0.5 * smooth(0, BLEND, d2 - d1);
      const b1 = biomeAt(i1), b2 = biomeAt(i2);

      let h = w1 * (b1.base + shape(b1, x, z, seed) * b1.amp)
        + (1 - w1) * (b2.base + shape(b2, x, z, seed) * b2.amp);

      // River first, THEN the lake — the river's bed at the mouth sits above
      // the basin floor, so carving it last would fill the lake back in.
      let bestD = Infinity, bestS = null;
      for (let k = 0; k < SAMPLES; k++) {
        const s = river[k];
        const d = (s.x - x) * (s.x - x) + (s.z - z) * (s.z - z);
        if (d < bestD) { bestD = d; bestS = s; }
      }
      const rd = Math.sqrt(bestD);
      if (rd < bestS.w * 3.4) {
        h = mix(h, bestS.bed + 2.6, smooth(bestS.w * 3.2, bestS.w * 1.15, rd)); // banks
        h = mix(h, bestS.bed, smooth(bestS.w * 1.15, bestS.w * 0.42, rd));      // bed
      }

      const dl = Math.hypot(x - lake.x, z - lake.z);
      if (dl < lake.r * 1.5) {
        h = mix(h, WATER_Y - 8, smooth(lake.r * 1.24, lake.r * 0.4, dl));
      }

      const idx = j * n + i;
      height[idx] = h;
      biome[idx] = seeds[w1 > 0.5 ? i1 : i2].b;
      for (let c = 0; c < 3; c++) {
        const sh = 16 - c * 8;
        color[idx * 3 + c] = mix(ch(b2.color, sh), ch(b1.color, sh), w1);
        rockCol[idx * 3 + c] = mix(ch(b2.rock, sh), ch(b1.rock, sh), w1);
      }
    }
  }

  // Second pass: modulate ground colour by slope, altitude and shoreline. It
  // needs finished heights for the gradient, so it can't fold into the loop.
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const idx = j * n + i;
      const h = height[idx];
      const hx = height[j * n + Math.min(n - 1, i + 1)] - height[j * n + Math.max(0, i - 1)];
      const hz = height[Math.min(n - 1, j + 1) * n + i] - height[Math.max(0, j - 1) * n + i];
      const slope = Math.hypot(hx, hz) / (2 * step);

      const rockT = smooth(0.42, 1.05, slope);        // cliffs shed their soil
      const snowT = smooth(30, 48, h) * (1 - rockT * 0.55); // altitude snowline
      const wetT = smooth(2.6, 0.1, h - WATER_Y);     // damp shoreline band

      for (let c = 0; c < 3; c++) {
        let v = mix(color[idx * 3 + c], rockCol[idx * 3 + c], rockT);
        v = mix(v, [0.93, 0.95, 0.98][c], snowT);
        v = mix(v, v * [0.55, 0.6, 0.72][c], wetT);
        color[idx * 3 + c] = v;
      }
    }
  }

  const coverage = {};
  for (let i = 0; i < biome.length; i++) {
    const k = BIOMES[biome[i]].key;
    coverage[k] = (coverage[k] || 0) + 1;
  }
  for (const k in coverage) coverage[k] = coverage[k] / biome.length;

  return { seed, height, biome, color, river, lake, seeds, coverage, n, step, half };
}

// Bilinear sample of the heightfield in world space.
export function heightAt(world, x, z) {
  const { n, step, half, height } = world;
  const fx = (x + half) / step, fz = (z + half) / step;
  const i = Math.max(0, Math.min(n - 2, Math.floor(fx)));
  const j = Math.max(0, Math.min(n - 2, Math.floor(fz)));
  const tx = clamp01(fx - i), tz = clamp01(fz - j);
  const h00 = height[j * n + i], h10 = height[j * n + i + 1];
  const h01 = height[(j + 1) * n + i], h11 = height[(j + 1) * n + i + 1];
  return mix(mix(h00, h10, tx), mix(h01, h11, tx), tz);
}

export function biomeAtWorld(world, x, z) {
  const { n, step, half, biome } = world;
  const i = Math.max(0, Math.min(n - 1, Math.round((x + half) / step)));
  const j = Math.max(0, Math.min(n - 1, Math.round((z + half) / step)));
  return BIOMES[biome[j * n + i]];
}

export function slopeAt(world, x, z) {
  const d = world.step;
  const hx = heightAt(world, x + d, z) - heightAt(world, x - d, z);
  const hz = heightAt(world, x, z + d) - heightAt(world, x, z - d);
  return Math.hypot(hx, hz) / (2 * d);
}

// Scatter prop instances, rejecting water, steep ground and the river channel.
export function scatterProps(world) {
  const rand = rng(world.seed ^ 0x9e3779b9);
  const out = [];
  BIOMES.forEach((b, bi) => {
    b.props.forEach((rule, ri) => {
      const placements = [];
      const area = (world.coverage[b.key] || 0) * SIZE * SIZE;
      const target = Math.min(1400, Math.floor(area * rule.density / 55));
      let guard = 0;
      while (placements.length < target && guard++ < target * 40) {
        const x = (rand() - 0.5) * SIZE, z = (rand() - 0.5) * SIZE;
        if (biomeAtWorld(world, x, z) !== b) continue;
        const y = heightAt(world, x, z);
        if (y < WATER_Y + 0.8) continue;
        if (rule.maxY !== undefined && y > rule.maxY) continue;
        if (slopeAt(world, x, z) > rule.maxSlope) continue;
        // keep the river channel clear
        let near = Infinity;
        for (const s of world.river) {
          const d = (s.x - x) * (s.x - x) + (s.z - z) * (s.z - z);
          if (d < near) near = d;
        }
        if (Math.sqrt(near) < 13) continue;
        placements.push({
          x, y, z,
          rot: rand() * Math.PI * 2,
          scale: mix(rule.scale[0], rule.scale[1], rand()),
        });
      }
      if (placements.length) out.push({ biome: bi, rule: ri, parts: rule.parts, placements });
    });
  });
  return out;
}

// ---------------------------------------------------------------------------
// Sites
//
// The point of the landscape: five REGIONS, each holding ten numbered sites.
// The region is the coarse index ("that one's in the desert, so 31-40") and
// the site is the fine index. Hierarchical chunking — far easier to hold than
// one flat run of 47, and it makes "which decade?" answerable at a glance.
// ---------------------------------------------------------------------------

export const REGION_KEYS = ['alpine', 'forest', 'winter', 'desert', 'future'];
export const REGION_COUNTS = [10, 10, 10, 10, 7];   // 47 presidencies

export function placeSites(world) {
  const rand = rng(world.seed ^ 0x5bf03635);

  // Order the five regions into a journey: nearest-neighbour chain starting at
  // the alpine seed, so the walk runs downstream with the river.
  const centres = REGION_KEYS.map(k => {
    const s = world.seeds.find(sd => BIOMES[sd.b].key === k);
    return { key: k, x: s.x, z: s.z };
  });
  let cur = centres.find(c => c.key === 'alpine') || centres[0];
  const remaining = centres.filter(c => c !== cur);
  const route = [cur];
  while (remaining.length) {
    let best = 0, bd = Infinity;
    remaining.forEach((c, i) => {
      const d = Math.hypot(c.x - cur.x, c.z - cur.z);
      if (d < bd) { bd = d; best = i; }
    });
    cur = remaining.splice(best, 1)[0];
    route.push(cur);
  }

  const sites = [];
  let ordinal = 1;
  let anchor = { x: route[0].x, z: route[0].z };

  route.forEach((region, ri) => {
    const want = REGION_COUNTS[ri];
    const biome = BIOMES.find(b => b.key === region.key);

    // Valid ground inside this region.
    const pool = [];
    for (let i = 0; i < 9000 && pool.length < 700; i++) {
      const x = (rand() - 0.5) * SIZE, z = (rand() - 0.5) * SIZE;
      if (biomeAtWorld(world, x, z) !== biome) continue;
      const y = heightAt(world, x, z);
      if (y < WATER_Y + 1.2) continue;
      if (slopeAt(world, x, z) > 0.42) continue;
      let near = Infinity;
      for (const s of world.river) {
        const d = (s.x - x) * (s.x - x) + (s.z - z) * (s.z - z);
        if (d < near) near = d;
      }
      if (Math.sqrt(near) < 16) continue;
      pool.push({ x, y, z });
    }
    if (!pool.length) return;

    // Farthest-point sampling so the ten sites spread across the region
    // instead of clumping wherever the sampler got lucky.
    const picked = [pool.reduce((a, p) =>
      Math.hypot(p.x - anchor.x, p.z - anchor.z) < Math.hypot(a.x - anchor.x, a.z - anchor.z) ? p : a)];
    while (picked.length < want && picked.length < pool.length) {
      let best = null, bd = -1;
      for (const p of pool) {
        if (picked.includes(p)) continue;
        let d = Infinity;
        for (const q of picked) d = Math.min(d, Math.hypot(p.x - q.x, p.z - q.z));
        if (d > bd) { bd = d; best = p; }
      }
      if (!best) break;
      picked.push(best);
    }

    // Then chain them into a short walk from the region entrance.
    const ordered = [];
    let from = anchor;
    const left = picked.slice();
    while (left.length) {
      let bi = 0, bd = Infinity;
      left.forEach((p, i) => {
        const d = Math.hypot(p.x - from.x, p.z - from.z);
        if (d < bd) { bd = d; bi = i; }
      });
      from = left.splice(bi, 1)[0];
      ordered.push(from);
    }

    ordered.forEach((p, i) => {
      sites.push({
        n: ordinal++, region: region.key, regionIndex: ri,
        indexInRegion: i + 1, x: p.x, y: p.y, z: p.z,
      });
    });
    anchor = ordered[ordered.length - 1] || anchor;
  });

  return { sites, route: route.map(r => r.key) };
}
