// ---------------------------------------------------------------------------
// The ten stations of one region — the exemplar every other theme copies.
//
// SCALE IS THE POINT HERE. Everything is in metres and sized against a 1.7 m
// player. Each station carries a "display" surface at roughly waist-to-chest
// height where its peg object sits, so you walk UP to the object and look at
// it — you never circle it and it never becomes architecture.
//
// The ten types are meant to be re-skinnable: a bridge is a bridge whether
// it's timber over a stream or steel over a canyon. Keep the SET fixed and the
// ORDER fixed; change only the dressing.
// ---------------------------------------------------------------------------

export const WOOD = 0x6b4f34;
export const WOOD_D = 0x4a3724;
export const STONE = 0x8d8c85;
export const STONE_D = 0x6a6963;
export const ROOF = 0x53372a;

// Each station: where it sits, how big its clearing is, what it builds, and
// the local point where its peg object stands.
export const STATIONS = [
  {
    n: 1, key: 'gate', name: 'The Gate', at: [-70, 60],
    blurb: 'You have arrived. Two posts and a lintel — nothing else looks like it.',
    clearing: 7, display: [2.4, 0.95, 0], align: true,
    build: K => {
      const g = K.g();
      for (const x of [-2.6, 2.6]) {
        g.add(K.at(K.box(0.42, 3.1, 0.42, WOOD), x, 1.55, 0));
        g.add(K.at(K.box(0.7, 0.22, 0.7, WOOD_D), x, 3.2, 0));
      }
      g.add(K.at(K.box(6.4, 0.4, 0.34, WOOD_D), 0, 3.0, 0));
      g.add(K.at(K.box(5.2, 0.22, 0.26, WOOD), 0, 2.6, 0));
      g.add(K.at(K.sph(0.26, 0xffe9a8, { e: 0xffc24a, ei: 1.3 }), 0, 2.4, 0));
      // display: a low stone marker you set things on
      g.add(K.at(K.cyl(0.46, 0.54, 0.9, STONE), 2.4, 0.45, 0));
      g.add(K.at(K.cyl(0.56, 0.56, 0.1, STONE_D), 2.4, 0.94, 0));
      return g;
    },
  },
  {
    n: 2, key: 'tree', name: 'The Great Tree', at: [-45, 38],
    blurb: 'One tall silhouette, visible from the gate. A cut stump beside it.',
    clearing: 8, display: [2.9, 0.78, 0.6],
    build: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.55, 0.95, 7.0, WOOD_D), 0, 3.5, 0));
      for (const [x, y, z, r] of [[0, 7.6, 0, 3.1], [-1.9, 6.6, 0.7, 2.1], [1.8, 6.9, -0.8, 2.3], [0.5, 9.2, 0.4, 2.0]])
        g.add(K.at(K.sph(r, 0x3c6b3a, { r: 0.95 }), x, y, z));
      for (const [x, z, a] of [[-1.4, 0.5, 0.7], [1.5, -0.4, -0.8]])
        g.add(K.rot(K.at(K.cyl(0.14, 0.24, 2.6, WOOD_D), x, 5.4, z), 0, 0, a));
      g.add(K.at(K.cyl(0.7, 0.78, 0.72, WOOD), 2.9, 0.36, 0.6));
      g.add(K.at(K.cyl(0.72, 0.72, 0.08, 0x8a6a44), 2.9, 0.76, 0.6));
      return g;
    },
  },
  {
    n: 3, key: 'well', name: 'The Well', at: [-22, 20],
    blurb: 'Low, circular, and you look down into it. The rim is the shelf.',
    clearing: 6, display: [0, 1.02, 0],
    build: K => {
      const g = K.g();
      g.add(K.at(K.cyl(1.15, 1.2, 0.95, STONE), 0, 0.48, 0));
      g.add(K.at(K.cyl(1.22, 1.22, 0.12, STONE_D), 0, 1.0, 0));
      g.add(K.at(K.cyl(1.02, 1.02, 0.06, 0x14202a), 0, 0.9, 0));
      for (const x of [-1.05, 1.05]) g.add(K.at(K.box(0.16, 2.3, 0.16, WOOD), x, 2.1, 0));
      g.add(K.rot(K.at(K.box(2.9, 0.14, 1.7, ROOF), 0, 3.35, 0), 0.28, 0, 0));
      g.add(K.rot(K.at(K.box(2.9, 0.14, 1.7, ROOF), 0, 3.35, 0), -0.28, 0, 0));
      g.add(K.rot(K.at(K.cyl(0.1, 0.1, 2.1, WOOD_D), 0, 3.0, 0), 0, 0, Math.PI / 2));
      g.add(K.at(K.cyl(0.26, 0.22, 0.34, WOOD_D), 0.5, 2.3, 0));
      return g;
    },
  },
  {
    n: 4, key: 'bridge', name: 'The Bridge', at: [5, 8],
    blurb: 'You cross water. Station five of ten — crossing means halfway.',
    clearing: 7, display: [0, 1.18, 1.35], align: true,
    build: K => {
      const g = K.g();
      g.add(K.at(K.box(4.2, 0.22, 9.0, WOOD), 0, 0.5, 0));
      for (let i = 0; i < 9; i++) g.add(K.at(K.box(4.3, 0.07, 0.7, WOOD_D), 0, 0.62, -4 + i));
      for (const x of [-2.0, 2.0]) {
        for (const z of [-4, -1.3, 1.3, 4]) g.add(K.at(K.box(0.18, 1.1, 0.18, WOOD_D), x, 1.05, z));
        g.add(K.at(K.box(0.14, 0.16, 8.8, WOOD_D), x, 1.55, 0));
      }
      g.add(K.at(K.box(0.34, 0.34, 0.34, WOOD_D), 0, 1.1, 1.35));
      return g;
    },
  },
  {
    n: 5, key: 'mill', name: 'The Mill', at: [20, -18],
    blurb: 'The wheel turns. Only station with continuous motion.',
    clearing: 9, display: [-2.6, 0.92, 1.9],
    build: K => {
      const g = K.g();
      g.add(K.at(K.box(5.4, 3.4, 4.6, 0x7a6a52), 0, 1.7, 0));
      g.add(K.rot(K.at(K.box(6.4, 0.26, 3.4, ROOF), 0, 4.0, -1.2), 0.5, 0, 0));
      g.add(K.rot(K.at(K.box(6.4, 0.26, 3.4, ROOF), 0, 4.0, 1.2), -0.5, 0, 0));
      g.add(K.at(K.box(1.1, 2.0, 0.16, WOOD_D), 0, 1.0, 2.35));
      const wheel = K.g();
      wheel.add(K.rot(K.at(K.tor(1.9, 0.13, WOOD_D), 0, 0, 0), 0, Math.PI / 2, 0));
      wheel.add(K.rot(K.at(K.tor(1.9, 0.13, WOOD_D), 0, 0, -0.7), 0, Math.PI / 2, 0));
      for (let i = 0; i < 10; i++) {
        const a = (i / 10) * Math.PI * 2;
        wheel.add(K.rot(K.at(K.box(0.16, 0.5, 0.9, WOOD), Math.cos(a) * 1.85, Math.sin(a) * 1.85, -0.35), Math.PI / 2, 0, a));
      }
      wheel.position.set(3.1, 1.7, 0.4);
      wheel.userData.spin = true;
      g.add(wheel);
      g.add(K.at(K.cyl(0.62, 0.62, 0.28, STONE), -2.6, 0.78, 1.9));
      g.add(K.at(K.cyl(0.44, 0.5, 0.65, STONE_D), -2.6, 0.32, 1.9));
      return g;
    },
  },
  {
    n: 6, key: 'cabin', name: 'The Cabin', at: [45, -45],
    blurb: 'You go inside. The only interior at ground level.',
    clearing: 11, display: [0, 0.92, -1.4], enterable: true,
    build: K => {
      const g = K.g();
      const W = 7, D = 6.4, H = 3.0;
      g.add(K.at(K.box(W + 0.6, 0.3, D + 0.6, STONE_D), 0, 0.15, 0));
      // three walls and a doorway wall, so the interior is real
      g.add(K.at(K.box(W, H, 0.3, WOOD), 0, H / 2, -D / 2));
      for (const x of [-W / 2, W / 2]) g.add(K.at(K.box(0.3, H, D, WOOD), x, H / 2, 0));
      for (const s of [-1, 1]) g.add(K.at(K.box(W / 2 - 0.9, H, 0.3, WOOD), s * (W / 4 + 0.45), H / 2, D / 2));
      g.add(K.at(K.box(1.8, H - 2.2, 0.3, WOOD), 0, H - 0.4, D / 2));
      g.add(K.rot(K.at(K.box(W + 1.2, 0.26, D * 0.8, ROOF), 0, H + 0.9, -1.5), 0.55, 0, 0));
      g.add(K.rot(K.at(K.box(W + 1.2, 0.26, D * 0.8, ROOF), 0, H + 0.9, 1.5), -0.55, 0, 0));
      // the table the peg sits on
      g.add(K.at(K.box(1.9, 0.12, 1.0, 0x8a6a44), 0, 0.86, -1.4));
      for (const [x, z] of [[-0.8, -1.0], [0.8, -1.0], [-0.8, -1.8], [0.8, -1.8]])
        g.add(K.at(K.box(0.12, 0.8, 0.12, WOOD_D), x, 0.4, z));
      g.add(K.at(K.sph(0.2, 0xffe0a0, { e: 0xffb84a, ei: 1.2 }), 0, 2.4, 0));
      return g;
    },
  },
  {
    n: 7, key: 'loft', name: 'The Loft', at: [45, -45],
    blurb: 'Up the outside stair. The only station you climb to — height is the cue.',
    clearing: 0, display: [4.9, 3.75, 1.4], upstairs: true,
    pinAt: [49.9, -43.6], pinY: 8.2,
    build: K => {
      const g = K.g();
      // external stair, then a balcony — one height per (x,z), no ambiguity
      for (let i = 0; i < 9; i++)
        g.add(K.at(K.box(1.5, 0.18, 0.55, WOOD_D), 6.6, 0.35 + i * 0.36, -2.6 + i * 0.55));
      g.add(K.at(K.box(3.4, 0.2, 2.6, WOOD), 5.4, 3.5, 1.4));
      for (const [x, z] of [[4.0, 0.2], [6.9, 0.2], [4.0, 2.6], [6.9, 2.6]])
        g.add(K.at(K.box(0.14, 1.0, 0.14, WOOD_D), x, 4.05, z));
      g.add(K.at(K.box(3.4, 0.12, 0.14, WOOD_D), 5.4, 4.5, 0.2));
      g.add(K.at(K.box(0.14, 0.12, 2.6, WOOD_D), 4.0, 4.5, 1.4));
      g.add(K.at(K.box(0.3, 2.0, 1.2, WOOD_D), 3.75, 4.5, 1.4));
      g.add(K.at(K.box(0.62, 0.62, 0.62, 0x8a6a44), 4.9, 3.9, 1.4)); // crate
      return g;
    },
  },
  {
    n: 8, key: 'barn', name: 'The Barn', at: [15, -58],
    blurb: 'Big volume, wide doors. Reads as mass where the cabin reads as shelter.',
    clearing: 10, display: [3.4, 0.98, 2.6],
    build: K => {
      const g = K.g();
      g.add(K.at(K.box(9, 4.4, 7, 0x7c3f34), 0, 2.2, 0));
      g.add(K.rot(K.at(K.box(9.8, 0.28, 4.6, ROOF), 0, 5.4, -1.8), 0.62, 0, 0));
      g.add(K.rot(K.at(K.box(9.8, 0.28, 4.6, ROOF), 0, 5.4, 1.8), -0.62, 0, 0));
      for (const s of [-1, 1]) g.add(K.at(K.box(1.8, 3.4, 0.2, WOOD_D), s * 1.0, 1.7, 3.55));
      g.add(K.at(K.box(4.2, 0.24, 0.22, 0xd8cfae), 0, 3.5, 3.6));
      g.add(K.at(K.cyl(0.55, 0.55, 0.9, 0x9a7a4a), 3.4, 0.45, 2.6));  // barrel
      g.add(K.at(K.cyl(0.58, 0.58, 0.1, 0x7a5f3a), 3.4, 0.95, 2.6));
      for (let i = 0; i < 4; i++)
        g.add(K.at(K.box(1.0, 0.7, 0.9, 0xc9b877), -3.6 + (i % 2) * 1.2, 0.35 + Math.floor(i / 2) * 0.72, 3.2));
      return g;
    },
  },
  {
    n: 9, key: 'shrine', name: 'The Shrine', at: [-25, -50],
    blurb: 'Standing stones and a flat altar. Stop and look — nothing else is still.',
    clearing: 8, display: [0, 1.05, 0],
    build: K => {
      const g = K.g();
      for (let i = 0; i < 5; i++) {
        const a = Math.PI * (0.25 + i * 0.25);
        g.add(K.rot(K.at(K.box(0.7, 2.6 + (i % 2) * 0.8, 0.5, STONE),
          Math.cos(a) * 3.4, 1.3 + (i % 2) * 0.4, Math.sin(a) * 3.4), 0, -a, (i % 2 ? 0.05 : -0.06)));
      }
      g.add(K.at(K.box(1.7, 0.9, 1.2, STONE_D), 0, 0.45, 0));
      g.add(K.at(K.box(2.0, 0.2, 1.5, STONE), 0, 1.0, 0));
      g.add(K.at(K.cyl(2.9, 2.9, 0.12, 0x5e6b4a), 0, 0.06, 0));
      return g;
    },
  },
  {
    n: 10, key: 'overlook', name: 'The Overlook', at: [-58, -18],
    blurb: 'High ground. You see the whole region — and where the next one starts.',
    clearing: 9, display: [-2.2, 1.15, 0],
    build: K => {
      const g = K.g();
      g.add(K.at(K.cyl(4.6, 5.2, 0.6, STONE_D), 0, 0.3, 0));
      g.add(K.at(K.cyl(4.4, 4.4, 0.14, STONE), 0, 0.62, 0));
      for (let i = 0; i < 7; i++) {
        const a = (i / 7) * Math.PI * 2;
        if (a > 1.6 && a < 3.0) continue; // gap you walk through
        g.add(K.at(K.box(0.5, 0.85, 0.5, STONE), Math.cos(a) * 4.1, 1.05, Math.sin(a) * 4.1));
      }
      // cairn — the display surface
      let r = 0.62;
      for (let i = 0; i < 5; i++) {
        g.add(K.at(K.sph(r, STONE, { r: 0.95 }), -2.2, 0.7 + i * 0.22, 0));
        r *= 0.82;
      }
      g.add(K.at(K.box(1.9, 0.14, 0.5, WOOD), 2.4, 1.15, 0));
      for (const z of [-0.15, 0.15]) g.add(K.at(K.box(0.14, 0.55, 0.14, WOOD_D), 2.4, 0.85, z * 4));
      return g;
    },
  },
];

// The walkway visits them in order and returns toward the gate.
export const PATH = STATIONS.map(s => s.at);
