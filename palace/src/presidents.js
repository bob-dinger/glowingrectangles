// ---------------------------------------------------------------------------
// The peg list. 45 people, 47 presidencies.
//
// Two systems are mixed on purpose:
//   soundalike  — Buchanan → cannon, Coolidge → cool fridge, Biden → bidet
//   iconic      — Lincoln → top hat, Nixon → tape recorder, T.R. → teddy bear
// Pure soundalike gets strained; pure iconic fails for the forgettable ones.
//
// Related presidents are handled by ESCALATION of a shared image, so the pair
// is encoded as a pair rather than as two unrelated facts:
//   Adams → atom          J.Q. Adams → atom bomb
//   Harrison → hairy son  B. Harrison → hairy grandson
//   Bush → shrub          G.W. Bush → burning shrub
//
// Cleveland (22, 24) and Trump (45, 47) each have ONE room, entered twice.
// `make` builds the prop from primitives. Base sits at y = 0, ~4–7 units tall.
// ---------------------------------------------------------------------------

export const PRESIDENTS = [
  {
    t: [1], name: 'George Washington', years: '1789–1797', peg: 'Washing machine',
    why: 'WASHING-ton. The drum is churning a load of powdered wigs.',
    hue: 0x4a7fb5,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(3.4, 4, 3.2, 0xf2f4f7), 0, 2, 0));
      g.add(K.rot(K.at(K.cyl(1.25, 1.25, 0.4, 0x2b3648), 0, 2.2, 1.6), Math.PI / 2, 0, 0));
      g.add(K.rot(K.at(K.cyl(1.05, 1.05, 0.3, 0x8fd4ff, { t: 0.45 }), 0, 2.2, 1.75), Math.PI / 2, 0, 0));
      for (let i = 0; i < 5; i++) {
        const a = (i / 5) * Math.PI * 2;
        g.add(K.at(K.sph(0.4, 0xffffff), Math.cos(a) * 0.55, 2.2 + Math.sin(a) * 0.55, 1.7));
      }
      g.add(K.at(K.box(2.6, 0.3, 0.3, 0xc9ced6), 0, 4.15, 0));
      return g;
    },
  },
  {
    t: [2], name: 'John Adams', years: '1797–1801', peg: 'An atom',
    why: 'ADAMS → ATOM. Electrons whipping around a molten core.',
    hue: 0x6ec3c9,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(1.1, 0xffcf5c, { e: 0xff9d2e, ei: 0.7 }), 0, 3.4, 0));
      const ring = (rx, ry, rz) => K.rot(K.at(K.tor(2.4, 0.11, 0x7fe3ea, { e: 0x2a8f96, ei: 0.5 }), 0, 3.4, 0), rx, ry, rz);
      g.add(ring(Math.PI / 2, 0, 0));
      g.add(ring(Math.PI / 2, 0, Math.PI / 3));
      g.add(ring(Math.PI / 2, 0, -Math.PI / 3));
      g.add(K.at(K.cyl(0.18, 0.35, 1.2, 0x556070), 0, 0.6, 0));
      return g;
    },
  },
  {
    t: [3], name: 'Thomas Jefferson', years: '1801–1809', peg: "A chef's son",
    why: "JEFF → CHEF. A small chef on a stepstool, toque taller than he is.",
    hue: 0xd8b26a,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(2.2, 0.7, 2.2, 0x8a7f6b), 0, 0.35, 0));
      g.add(K.at(K.cyl(0.62, 0.7, 1.9, 0xdfe4ea), 0, 1.65, 0));
      g.add(K.at(K.sph(0.62, 0xf0c9a0), 0, 2.85, 0));
      g.add(K.at(K.cyl(0.72, 0.66, 0.28, 0xffffff), 0, 3.45, 0));
      g.add(K.at(K.sph(1.0, 0xffffff), 0, 4.15, 0));
      g.add(K.at(K.sph(0.62, 0xffffff), -0.6, 4.5, 0.2));
      g.add(K.at(K.sph(0.55, 0xffffff), 0.62, 4.45, -0.2));
      g.add(K.rot(K.at(K.cyl(0.07, 0.07, 1.6, 0xb0b7c0), 1.1, 2.0, 0.5), 0, 0, -0.5));
      return g;
    },
  },
  {
    t: [4], name: 'James Madison', years: '1809–1817', peg: 'A maid',
    why: 'MAID-ison. Feather duster the size of a broom, apron everywhere.',
    hue: 0xc98fb8,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cone(1.1, 2.6, 0x3d4457), 0, 1.3, 0));
      g.add(K.at(K.box(1.5, 1.5, 0.12, 0xffffff), 0, 1.6, 0.85));
      g.add(K.at(K.sph(0.55, 0xf0c9a0), 0, 3.0, 0));
      g.add(K.at(K.box(1.0, 0.28, 0.7, 0xffffff), 0, 3.5, 0));
      g.add(K.rot(K.at(K.cyl(0.09, 0.09, 2.2, 0x8a6a4a), 1.2, 2.6, 0.3), 0, 0, -0.35));
      g.add(K.at(K.sph(0.75, 0xffe9a8), 1.55, 3.75, 0.3));
      g.add(K.at(K.sph(0.5, 0xfff3cf), 1.9, 4.2, 0.5));
      return g;
    },
  },
  {
    t: [5], name: 'James Monroe', years: '1817–1825', peg: 'Marilyn Monroe',
    why: 'The name is the whole peg — white dress billowing over a subway grate.',
    hue: 0xe86a8a, anchor: true,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(4.2, 0.25, 4.2, 0x39404d), 0, 0.12, 0));
      for (let i = -1; i <= 1; i++) g.add(K.at(K.box(3.6, 0.1, 0.22, 0x1c212a), 0, 0.26, i * 1.1));
      g.add(K.at(K.cyl(0.28, 1.9, 2.6, 0xffffff), 0, 1.5, 0));
      g.add(K.at(K.cyl(1.9, 2.4, 0.5, 0xf7f7f7), 0, 2.9, 0));
      g.add(K.at(K.cyl(0.34, 0.28, 1.3, 0xffffff), 0, 3.6, 0));
      g.add(K.at(K.sph(0.5, 0xf0c9a0), 0, 4.4, 0));
      g.add(K.at(K.sph(0.62, 0xf0d060), 0, 4.6, -0.12));
      return g;
    },
  },
  {
    t: [6], name: 'John Quincy Adams', years: '1825–1829', peg: 'An atom BOMB',
    why: 'The son escalates the father. Same atom, now a mushroom cloud.',
    hue: 0xe07a4a,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.75, 1.15, 3.2, 0xd9863f, { e: 0x7a3a10, ei: 0.35 }), 0, 1.6, 0));
      g.add(K.at(K.sph(2.0, 0xf0a35a, { e: 0x8a3f10, ei: 0.45 }), 0, 4.4, 0));
      g.add(K.at(K.sph(1.2, 0xffd08a, { e: 0xb05a18, ei: 0.5 }), -1.3, 4.9, 0.4));
      g.add(K.at(K.sph(1.05, 0xffc074, { e: 0xa04f14, ei: 0.5 }), 1.35, 4.7, -0.35));
      g.add(K.rot(K.at(K.tor(2.9, 0.22, 0xffe0b0, { t: 0.5, e: 0x8a4a12, ei: 0.4 }), 0, 3.1, 0), Math.PI / 2, 0, 0));
      return g;
    },
  },
  {
    t: [7], name: 'Andrew Jackson', years: '1829–1837', peg: 'Giant jacks',
    why: 'JACKS-on. Six-foot steel jacks strewn where you have to step over them.',
    hue: 0x9aa6b5,
    make: K => {
      const g = K.g();
      const jack = (x, z, s, ry) => {
        const j = K.g();
        for (const [ax, ay, az] of [[1, 0, 0], [0, 1, 0], [0, 0, 1]]) {
          j.add(K.rot(K.cyl(0.16, 0.16, 2.6, 0xb8c0cc, { m: 0.85, r: 0.25 }), az ? Math.PI / 2 : 0, 0, ax ? Math.PI / 2 : 0));
          j.add(K.at(K.sph(0.34, 0xd6dce6, { m: 0.85, r: 0.25 }), ax * 1.3, ay * 1.3, az * 1.3));
          j.add(K.at(K.sph(0.34, 0xd6dce6, { m: 0.85, r: 0.25 }), -ax * 1.3, -ay * 1.3, -az * 1.3));
        }
        j.scale.setScalar(s); j.position.set(x, 1.3 * s, z); j.rotation.y = ry;
        return j;
      };
      g.add(jack(0, 0, 1.15, 0.4));
      g.add(jack(-2.6, 1.8, 0.7, 1.1));
      g.add(jack(2.4, -1.6, 0.55, -0.7));
      return g;
    },
  },
  {
    t: [8], name: 'Martin Van Buren', years: '1837–1841', peg: 'A burning van',
    why: 'VAN BUREN → VAN BURNIN\'. It is fully involved and nobody is worried.',
    hue: 0xe2542e,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(5.2, 2.2, 2.4, 0x3f6fa8), 0, 1.7, 0));
      g.add(K.at(K.box(2.0, 1.3, 2.3, 0x35619a), 2.4, 2.9, 0));
      g.add(K.at(K.box(1.6, 0.9, 2.35, 0x9fd8ff, { t: 0.55 }), 2.5, 3.1, 0));
      for (const x of [-1.7, 1.9]) for (const z of [-1.25, 1.25])
        g.add(K.rot(K.at(K.cyl(0.62, 0.62, 0.36, 0x21252d), x, 0.62, z), Math.PI / 2, 0, 0));
      const flame = (x, y, z, h, c) => K.at(K.cone(h * 0.42, h, c, { e: c, ei: 0.9 }), x, y + h / 2, z);
      g.add(flame(-1.2, 2.8, 0, 2.6, 0xff6a1e));
      g.add(flame(0.4, 2.8, 0.5, 3.4, 0xffa524));
      g.add(flame(-0.4, 3.0, -0.6, 2.0, 0xffd85e));
      g.add(flame(1.4, 3.4, 0.2, 1.6, 0xff8a2e));
      return g;
    },
  },
  {
    t: [9], name: 'William Henry Harrison', years: '1841', peg: 'A hairy son, soaked',
    why: 'HAIRY-son. Drenched — he gave a two-hour inaugural in the rain and was gone in 31 days.',
    hue: 0x7e8fa0,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.85, 0.95, 2.6, 0x5c4a38), 0, 1.3, 0));
      g.add(K.at(K.sph(0.72, 0xf0c9a0), 0, 3.0, 0));
      for (let i = 0; i < 90; i++) {
        const a = Math.random() * Math.PI * 2, yy = 0.4 + Math.random() * 3.1, r = 0.9 + Math.random() * 0.2;
        g.add(K.rot(K.at(K.cyl(0.05, 0.02, 0.85, 0x6b5340), Math.cos(a) * r, yy, Math.sin(a) * r), Math.random() * 0.6 - 0.3, 0, Math.cos(a) * 1.2));
      }
      for (let i = 0; i < 40; i++)
        g.add(K.at(K.cyl(0.035, 0.035, 0.7, 0x9fd8ff, { t: 0.6, e: 0x3a7fb0, ei: 0.4 }),
          (Math.random() - 0.5) * 6, 1 + Math.random() * 6, (Math.random() - 0.5) * 6));
      return g;
    },
  },
  {
    t: [10], name: 'John Tyler', years: '1841–1845', peg: 'A tiler',
    why: 'TILE-r. A wall of tiles going up, half of them still wet.',
    hue: 0x53b0a8, anchor: true,
    make: K => {
      const g = K.g();
      for (let r = 0; r < 7; r++) for (let c = 0; c < 7; c++) {
        const set = r * 7 + c < 34;
        g.add(K.rot(K.at(K.box(0.78, 0.78, 0.12, set ? 0x49bdb2 : 0x2c3742),
          (c - 3) * 0.86, 0.5 + r * 0.86, -0.4), 0, 0, set ? 0 : (Math.random() - 0.5) * 0.25));
      }
      g.add(K.at(K.box(2.4, 0.3, 1.6, 0x8a7f6b), 0, 0.15, 1.6));
      g.add(K.rot(K.at(K.box(1.1, 0.14, 0.5, 0xc0c6ce), 0.2, 0.4, 1.6), 0, 0.3, 0));
      return g;
    },
  },
  {
    t: [11], name: 'James K. Polk', years: '1845–1849', peg: 'A giant poking finger',
    why: 'POKE. It descends from the ceiling and jabs you in the chest.',
    hue: 0xd98fa0,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.cyl(0.85, 1.0, 5.0, 0xf0c9a0), 0, 4.2, -1.2), 0.45, 0, 0));
      g.add(K.at(K.sph(0.85, 0xf7d4ac), 0, 2.0, 0.05));
      g.add(K.rot(K.at(K.cyl(0.86, 0.86, 0.2, 0xf7dcc0), 0, 2.5, 0.35), 0.45, 0, 0));
      g.add(K.at(K.box(0.75, 0.12, 0.5, 0xe8b8a0), 0, 2.05, 0.72));
      g.add(K.at(K.cyl(1.4, 1.6, 0.5, 0x3a4250), 0, 6.6, -1.9));
      return g;
    },
  },
  {
    t: [12], name: 'Zachary Taylor', years: '1849–1850', peg: 'A tailor',
    why: 'TAYLOR → TAILOR. Shears as tall as a person, tape measure everywhere.',
    hue: 0xb08ad8,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.box(0.35, 4.2, 0.14, 0xd0d6de, { m: 0.8, r: 0.25 }), -0.5, 2.6, 0), 0, 0, 0.16));
      g.add(K.rot(K.at(K.box(0.35, 4.2, 0.14, 0xd0d6de, { m: 0.8, r: 0.25 }), 0.5, 2.6, 0), 0, 0, -0.16));
      g.add(K.rot(K.at(K.tor(0.62, 0.16, 0xe2544a), -0.85, 0.7, 0), 0, Math.PI / 2, 0));
      g.add(K.rot(K.at(K.tor(0.62, 0.16, 0xe2544a), 0.85, 0.7, 0), 0, Math.PI / 2, 0));
      g.add(K.at(K.sph(0.2, 0x9aa2ad, { m: 0.9 }), 0, 2.0, 0));
      for (let i = 0; i < 12; i++)
        g.add(K.rot(K.at(K.box(0.9, 0.06, 0.3, 0xf4e04a), Math.sin(i) * 2.2, 0.1 + i * 0.06, 1.6 + Math.cos(i * 1.4) * 1.2), 0, i * 0.5, 0));
      return g;
    },
  },
  {
    t: [13], name: 'Millard Fillmore', years: '1850–1853', peg: 'A cup filling over',
    why: 'FILL-MORE. Somebody keeps pouring. The floor is a lake.',
    hue: 0x5aa7d8,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(1.6, 1.2, 3.0, 0xf2f4f7), 0, 1.5, 0));
      g.add(K.at(K.cyl(1.55, 1.55, 0.4, 0x8a5a2e), 0, 2.9, 0));
      g.add(K.rot(K.at(K.tor(0.85, 0.2, 0xf2f4f7), 1.75, 1.7, 0), 0, Math.PI / 2, 0));
      for (let i = 0; i < 5; i++) {
        const a = (i / 5) * Math.PI * 2;
        g.add(K.at(K.cyl(0.16, 0.16, 1.5, 0x6ab8e8, { t: 0.7 }), Math.cos(a) * 1.5, 2.4, Math.sin(a) * 1.5));
      }
      g.add(K.at(K.cyl(4.5, 4.5, 0.12, 0x4a9ad0, { t: 0.55, r: 0.15 }), 0, 0.06, 0));
      g.add(K.rot(K.at(K.cyl(0.5, 0.75, 1.8, 0xc0c6ce, { m: 0.7 }), -1.2, 5.2, 0), 0, 0, 0.9));
      return g;
    },
  },
  {
    t: [14], name: 'Franklin Pierce', years: '1853–1857', peg: 'A needle',
    why: 'PIERCE. It has gone straight through the wall and out the other side.',
    hue: 0x8fd4e8,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.cyl(0.14, 0.02, 7.5, 0xdde3ea, { m: 0.9, r: 0.15 }), 0, 3.6, 0), 0, 0, 0.22));
      g.add(K.rot(K.at(K.tor(0.34, 0.09, 0xdde3ea, { m: 0.9, r: 0.15 }), -0.85, 7.0, 0), Math.PI / 2, 0, 0.22));
      for (let i = 0; i < 14; i++)
        g.add(K.at(K.sph(0.13, 0xe2544a), -1.1 - i * 0.28, 7.0 - Math.abs(Math.sin(i * 0.8)) * 1.6, Math.sin(i * 0.55) * 0.5));
      g.add(K.at(K.box(2.2, 0.5, 2.2, 0x3a4250), 0, 0.25, 0));
      return g;
    },
  },
  {
    t: [15], name: 'James Buchanan', years: '1857–1861', peg: 'A cannon',
    why: 'bu-CANNON. Aimed at the door you are about to walk through.',
    hue: 0x6b7280, anchor: true,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.cyl(0.55, 0.75, 5.0, 0x2f3640, { m: 0.8, r: 0.35 }), 0, 2.1, 0.3), -0.22, 0, 0));
      g.add(K.rot(K.at(K.tor(0.6, 0.12, 0x4a525e, { m: 0.8 }), 0, 2.6, 2.6), Math.PI / 2 - 0.22, 0, 0));
      g.add(K.at(K.box(3.4, 0.7, 1.4, 0x6b4a2e), 0, 1.0, -0.6));
      for (const z of [-0.9, 0.9])
        g.add(K.rot(K.at(K.cyl(1.1, 1.1, 0.35, 0x7a5636), 0, 1.1, z - 0.6), Math.PI / 2, 0, 0));
      for (const [x, z] of [[-2.0, 1.6], [-1.5, 2.2], [-2.4, 2.4]])
        g.add(K.at(K.sph(0.42, 0x22262e, { m: 0.9, r: 0.3 }), x, 0.42, z));
      return g;
    },
  },
  {
    t: [16], name: 'Abraham Lincoln', years: '1861–1865', peg: 'A top hat',
    why: 'The hat is the man. Forty feet of it — you walk underneath the brim.',
    hue: 0x2b3140,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(2.6, 2.6, 0.3, 0x14171e, { r: 0.55 }), 0, 0.15, 0));
      g.add(K.at(K.cyl(1.75, 1.8, 4.6, 0x1b1f28, { r: 0.5 }), 0, 2.5, 0));
      g.add(K.at(K.cyl(1.83, 1.83, 0.7, 0x5a3a2a, { r: 0.6 }), 0, 0.85, 0));
      g.add(K.at(K.cyl(1.78, 1.78, 0.12, 0x2a2f3a), 0, 4.78, 0));
      return g;
    },
  },
  {
    t: [17], name: 'Andrew Johnson', years: '1865–1869', peg: 'A toilet',
    why: 'JOHN-son. First president impeached — the peg is not being subtle.',
    hue: 0xa8c4d0,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(1.2, 0.85, 2.2, 0xf4f6f8), 0, 1.1, 0));
      g.add(K.at(K.cyl(1.45, 1.3, 0.8, 0xf4f6f8), 0, 2.5, 0));
      g.add(K.rot(K.at(K.tor(1.25, 0.22, 0xe4e8ec), 0, 2.95, 0), Math.PI / 2, 0, 0));
      g.add(K.at(K.box(2.6, 3.0, 1.0, 0xf4f6f8), 0, 3.5, -1.6));
      g.add(K.at(K.box(2.7, 0.3, 1.2, 0xe4e8ec), 0, 5.1, -1.6));
      g.add(K.rot(K.at(K.cyl(0.1, 0.1, 0.6, 0xc9a24a, { m: 0.9, r: 0.2 }), 1.1, 4.6, -1.2), 0, 0, Math.PI / 2));
      return g;
    },
  },
  {
    t: [18], name: 'Ulysses S. Grant', years: '1869–1877', peg: 'An oversized cheque',
    why: 'A GRANT. Novelty-cheque sized, and he is on the fifty.',
    hue: 0x5fa86b,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(6.0, 2.8, 0.18, 0xf6f8f2), 0, 3.2, 0));
      g.add(K.at(K.box(5.4, 0.22, 0.24, 0x4a7f56), 0, 2.6, 0.05));
      g.add(K.at(K.box(2.0, 0.5, 0.24, 0x2f6b3c), -1.6, 3.9, 0.05));
      g.add(K.at(K.box(1.4, 0.7, 0.24, 0x2f6b3c), 2.0, 3.5, 0.05));
      for (const x of [-2.4, 2.4]) g.add(K.at(K.cyl(0.12, 0.12, 3.2, 0x8a7f6b), x, 1.6, 0));
      for (let i = 0; i < 6; i++)
        g.add(K.rot(K.at(K.box(1.6, 0.12, 0.75, 0x6ea87a), -2.6 + (i % 2) * 5.0, 0.1 + Math.floor(i / 2) * 0.14, 1.4), 0, i * 0.4, 0));
      return g;
    },
  },
  {
    t: [19], name: 'Rutherford B. Hayes', years: '1877–1881', peg: 'Haze',
    why: 'HAYES → HAZE. The room is fogged out. You find the exit by the lamp.',
    hue: 0xb0b8c2,
    make: K => {
      const g = K.g();
      for (let i = 0; i < 22; i++)
        g.add(K.at(K.sph(1.2 + Math.random() * 1.6, 0xd8dee6, { t: 0.13 }),
          (Math.random() - 0.5) * 9, 0.8 + Math.random() * 4.5, (Math.random() - 0.5) * 9));
      g.add(K.at(K.cyl(0.2, 0.2, 3.4, 0x3a4250), 0, 1.7, 0));
      g.add(K.at(K.sph(0.75, 0xfff0b0, { e: 0xffd24a, ei: 1.4 }), 0, 3.8, 0));
      g.add(K.at(K.cyl(0.55, 0.75, 0.5, 0x2f3640), 0, 4.45, 0));
      return g;
    },
  },
  {
    t: [20], name: 'James A. Garfield', years: '1881', peg: 'A fat orange cat',
    why: 'The name does all the work. Asleep on a tower of lasagne.',
    hue: 0xe8973a, anchor: true,
    make: K => {
      const g = K.g();
      for (let i = 0; i < 5; i++)
        g.add(K.at(K.box(3.2, 0.3, 2.4, i % 2 ? 0xe8c27a : 0xc4503a), 0, 0.2 + i * 0.32, 0));
      g.add(K.at(K.sph(1.5, 0xf0913a), 0, 2.6, 0));
      g.add(K.at(K.sph(1.0, 0xf5a24e), 1.4, 3.1, 0));
      g.add(K.at(K.cone(0.32, 0.6, 0xf0913a), 1.1, 3.9, 0.45));
      g.add(K.at(K.cone(0.32, 0.6, 0xf0913a), 1.1, 3.9, -0.45));
      for (const z of [0.3, -0.3]) g.add(K.at(K.sph(0.16, 0x2b2b2b), 2.2, 3.2, z));
      for (let i = 0; i < 4; i++)
        g.add(K.at(K.box(1.4, 0.12, 0.12, 0xd8813a), -0.6 + i * 0.5, 1.8, i % 2 ? 1.3 : -1.3));
      g.add(K.rot(K.at(K.cyl(0.16, 0.08, 2.4, 0xf0913a), -1.9, 2.4, 0), 0, 0, 0.9));
      return g;
    },
  },
  {
    t: [21], name: 'Chester A. Arthur', years: '1881–1885', peg: 'Sword in the stone',
    why: 'ARTHUR. Nobody in the room can pull it out, least of all him.',
    hue: 0x7f8ea8,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(3.0, 1.8, 3.0, 0x6b7280, { r: 0.9 }), 0, 0.9, 0));
      g.add(K.at(K.box(2.6, 0.4, 2.6, 0x808894, { r: 0.9 }), 0, 1.95, 0));
      g.add(K.at(K.box(0.4, 3.6, 0.12, 0xdfe5ec, { m: 0.95, r: 0.12 }), 0, 3.6, 0));
      g.add(K.at(K.cone(0.22, 0.6, 0xdfe5ec, { m: 0.95, r: 0.12 }), 0, 5.6, 0));
      g.add(K.at(K.box(1.7, 0.26, 0.3, 0xc9a24a, { m: 0.9, r: 0.25 }), 0, 5.0, 0));
      g.add(K.at(K.cyl(0.16, 0.16, 0.9, 0x5a3a2a), 0, 5.5, 0));
      g.add(K.at(K.sph(0.28, 0xc9a24a, { m: 0.9, r: 0.25 }), 0, 6.0, 0));
      return g;
    },
  },
  {
    t: [22, 24], name: 'Grover Cleveland', years: '1885–1889, 1893–1897', peg: 'A meat cleaver',
    why: 'CLEAVE-land. You will be back here — he is the only president to serve two non-consecutive terms.',
    hue: 0xc0524a, twice: true,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.box(3.6, 2.6, 0.22, 0xe4e9ef, { m: 0.92, r: 0.15 }), 0.6, 3.6, 0), 0, 0, -0.12));
      g.add(K.rot(K.at(K.box(3.6, 0.3, 0.26, 0xf8fbff, { m: 0.98, r: 0.05 }), 0.6, 2.4, 0), 0, 0, -0.12));
      g.add(K.rot(K.at(K.cyl(0.28, 0.32, 2.6, 0x5a3a2a), -1.9, 2.2, 0), 0, 0, -0.12));
      g.add(K.at(K.sph(0.3, 0x8a5a3a), -2.2, 0.95, 0));
      g.add(K.at(K.cyl(1.9, 1.9, 0.5, 0x6b4a2e), 0, 0.25, 0.6));
      g.add(K.rot(K.at(K.box(1.6, 0.1, 0.3, 0x9a3a30), 0.4, 0.55, 1.0), 0, 0.4, 0));
      return g;
    },
  },
  {
    t: [23], name: 'Benjamin Harrison', years: '1889–1893', peg: 'A hairy GRANDson',
    why: 'The same hairy son, one generation on — he was #9\'s grandson. Smaller, drier, with a cane.',
    hue: 0x8a7a68,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.7, 0.8, 2.0, 0x4a5a48), 0, 1.0, 0));
      g.add(K.at(K.sph(0.6, 0xf0c9a0), 0, 2.4, 0));
      for (let i = 0; i < 60; i++) {
        const a = Math.random() * Math.PI * 2, yy = 0.4 + Math.random() * 2.4, r = 0.75 + Math.random() * 0.18;
        g.add(K.rot(K.at(K.cyl(0.045, 0.02, 0.6, 0xd8d2c8), Math.cos(a) * r, yy, Math.sin(a) * r), 0, 0, Math.cos(a) * 1.2));
      }
      g.add(K.at(K.sph(0.55, 0xe8e4dc), 0, 2.1, 0.45));
      g.add(K.rot(K.at(K.cyl(0.08, 0.08, 2.2, 0x5a3a2a), 1.0, 1.1, 0.2), 0, 0, 0.12));
      g.add(K.rot(K.at(K.tor(0.22, 0.07, 0x5a3a2a), 1.12, 2.2, 0.2), Math.PI / 2, 0, 0));
      return g;
    },
  },
  {
    t: [25], name: 'William McKinley', years: '1897–1901', peg: 'A mountain',
    why: 'Denali carried his name for a century. A snow-capped peak indoors.',
    hue: 0x6f93b5, anchor: true,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cone(3.4, 6.2, 0x5a6b7d, { r: 0.95 }), 0, 3.1, 0));
      g.add(K.at(K.cone(1.35, 2.2, 0xf4f8fb, { r: 0.7 }), 0, 5.3, 0));
      g.add(K.at(K.cone(1.6, 2.8, 0x647486, { r: 0.95 }), -3.0, 1.4, 1.4));
      g.add(K.at(K.cone(0.6, 0.95, 0xf4f8fb), -3.0, 2.55, 1.4));
      g.add(K.at(K.cone(1.2, 2.0, 0x647486, { r: 0.95 }), 2.9, 1.0, -1.5));
      return g;
    },
  },
  {
    t: [26], name: 'Theodore Roosevelt', years: '1901–1909', peg: 'A teddy bear',
    why: 'The bear is literally named after him. Give it the glasses too.',
    hue: 0xa5713f,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(1.7, 0xa5713f), 0, 2.0, 0));
      g.add(K.at(K.sph(1.15, 0xb07f4a), 0, 4.2, 0));
      for (const x of [-0.85, 0.85]) g.add(K.at(K.sph(0.42, 0xa5713f), x, 5.1, 0));
      for (const x of [-1.7, 1.7]) g.add(K.rot(K.at(K.cyl(0.42, 0.34, 1.7, 0xa5713f), x, 2.3, 0), 0, 0, x > 0 ? -0.5 : 0.5));
      for (const x of [-0.8, 0.8]) g.add(K.at(K.cyl(0.5, 0.42, 1.3, 0xa5713f), x, 0.65, 0.2));
      g.add(K.at(K.sph(0.42, 0xc99a6a), 0, 3.95, 0.95));
      g.add(K.at(K.sph(0.16, 0x2b2b2b), 0, 4.05, 1.3));
      for (const x of [-0.42, 0.42]) g.add(K.rot(K.at(K.tor(0.36, 0.055, 0x2b2b2b), x, 4.45, 0.95), 0, 0, 0));
      g.add(K.at(K.box(0.35, 0.05, 0.05, 0x2b2b2b), 0, 4.45, 0.95));
      return g;
    },
  },
  {
    t: [27], name: 'William Howard Taft', years: '1909–1913', peg: 'Stuck in a bathtub',
    why: 'The story may be apocryphal. It is also unforgettable, which is the point.',
    hue: 0x86c3d8,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(2.4, 2.1, 2.2, 0xf4f8fb), 0, 1.1, 0));
      g.add(K.rot(K.at(K.tor(2.4, 0.2, 0xffffff), 0, 2.2, 0), Math.PI / 2, 0, 0));
      g.add(K.at(K.cyl(2.2, 2.2, 0.15, 0x6ab8e8, { t: 0.75 }), 0, 1.95, 0));
      g.add(K.at(K.sph(0.72, 0xf0c9a0), 0, 2.9, 0));
      g.add(K.at(K.sph(0.5, 0xe8e4dc), 0, 2.7, 0.55));
      for (let i = 0; i < 9; i++)
        g.add(K.at(K.sph(0.28 + Math.random() * 0.3, 0xffffff, { t: 0.5 }),
          (Math.random() - 0.5) * 3.6, 2.0 + Math.random() * 0.8, (Math.random() - 0.5) * 3.6));
      for (const [x, z] of [[-1.5, -1.5], [1.5, -1.5], [-1.5, 1.5], [1.5, 1.5]])
        g.add(K.at(K.cyl(0.16, 0.2, 0.5, 0xc9a24a, { m: 0.9 }), x, 0.25, z));
      return g;
    },
  },
  {
    t: [28], name: 'Woodrow Wilson', years: '1913–1921', peg: 'A volleyball with a face',
    why: 'WILSON. Castaway did the mnemonic work for you decades ago.',
    hue: 0xe0e4e8,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(2.4, 0xf4f6f8), 0, 3.0, 0));
      g.add(K.at(K.sph(2.42, 0xc4483a, { t: 0.9 }), 0, 3.0, 0.6));
      for (const x of [-0.75, 0.75]) g.add(K.at(K.sph(0.26, 0x7a2a20), x, 3.5, 2.2));
      g.add(K.at(K.box(0.16, 0.7, 0.16, 0x7a2a20), 0, 3.0, 2.35));
      for (let i = 0; i < 7; i++)
        g.add(K.at(K.sph(0.17, 0x7a2a20), -0.9 + i * 0.3, 2.1 + Math.abs(Math.sin(i * 0.9)) * 0.28, 2.25));
      g.add(K.at(K.cyl(1.4, 1.6, 0.4, 0x8a7f6b), 0, 0.2, 0));
      g.add(K.at(K.cyl(0.3, 0.3, 0.6, 0x8a7f6b), 0, 0.6, 0));
      return g;
    },
  },
  {
    t: [29], name: 'Warren G. Harding', years: '1921–1923', peg: 'A hard hat',
    why: 'HARD-ing. Big enough to shelter under, which his administration needed.',
    hue: 0xe8b93a,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(2.6, 0xf0bf3a, { r: 0.4 }), 0, 1.4, 0));
      g.add(K.at(K.box(6.6, 0.4, 6.6, 0x1b1f28), 0, 1.4, 0));
      g.add(K.at(K.cyl(2.9, 2.9, 0.4, 0xf0bf3a, { r: 0.4 }), 0, 1.2, 0));
      g.add(K.at(K.box(2.2, 0.35, 1.1, 0xffd45e), 0, 1.05, 2.5));
      g.add(K.at(K.box(0.6, 1.8, 0.3, 0xd8a72e), 0, 2.8, 0));
      for (const z of [-0.9, 0.9]) g.add(K.at(K.box(0.35, 1.5, 0.25, 0xd8a72e), 0, 2.7, z));
      return g;
    },
  },
  {
    t: [30], name: 'Calvin Coolidge', years: '1923–1929', peg: 'A cool fridge',
    why: 'COOL-idge. Door hanging open, freezing the room. Silent Cal.',
    hue: 0x62c8d8, anchor: true,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(3.2, 6.0, 2.6, 0xdfe6ec, { m: 0.55, r: 0.35 }), 0, 3.0, 0));
      g.add(K.at(K.box(2.9, 5.6, 0.2, 0x9fe8f4, { e: 0x2a8fa8, ei: 0.7, t: 0.75 }), 0, 3.0, 1.3));
      g.add(K.rot(K.at(K.box(2.8, 5.5, 0.25, 0xf0f6fa, { m: 0.6 }), 2.3, 3.0, 1.9), 0, -1.15, 0));
      g.add(K.at(K.cyl(0.09, 0.09, 1.6, 0xb0b7c0, { m: 0.9 }), 3.6, 3.0, 2.6));
      for (let i = 0; i < 10; i++)
        g.add(K.at(K.cone(0.14, 0.6 + Math.random() * 0.7, 0xcdeff8, { t: 0.7, e: 0x4aa8c0, ei: 0.4 }),
          -1.2 + Math.random() * 2.4, 5.6, 1.2));
      for (let i = 0; i < 14; i++)
        g.add(K.at(K.sph(0.3, 0xdff4fa, { t: 0.14 }), (Math.random() - 0.5) * 4, 0.4 + Math.random() * 2, 1.4 + Math.random() * 2));
      return g;
    },
  },
  {
    t: [31], name: 'Herbert Hoover', years: '1929–1933', peg: 'A vacuum cleaner',
    why: 'HOOVER is a vacuum in half the English-speaking world. It is sucking up the economy.',
    hue: 0x9a5ad0,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(1.1, 1.3, 3.6, 0x8a4ac0, { m: 0.4 }), 0, 1.8, 0));
      g.add(K.at(K.box(3.0, 0.6, 2.0, 0x2f3640), 0, 0.3, 0.6));
      g.add(K.rot(K.at(K.cyl(0.1, 0.1, 3.4, 0xb0b7c0, { m: 0.9 }), 0, 4.4, -0.6), 0.25, 0, 0));
      g.add(K.rot(K.at(K.cyl(0.16, 0.16, 1.0, 0x2f3640), 0, 6.0, -1.1), 0.25, 0, 0));
      for (let i = 0; i < 8; i++)
        g.add(K.rot(K.at(K.tor(0.42, 0.14, 0x4a525e), 1.4, 1.2 + i * 0.42, 0.4), Math.PI / 2, 0, 0.4));
      g.add(K.at(K.cyl(0.75, 0.75, 0.4, 0xd8d2c8, { t: 0.5 }), 0, 3.9, 0));
      for (let i = 0; i < 7; i++)
        g.add(K.at(K.box(0.35, 0.35, 0.05, 0x6ea87a), -1.6 + Math.random() * 3, 0.7 + Math.random() * 1.4, 1.6 + Math.random()));
      return g;
    },
  },
  {
    t: [32], name: 'Franklin D. Roosevelt', years: '1933–1945', peg: 'A wheelchair',
    why: 'True, and it separates him from the other Roosevelt cleanly.',
    hue: 0x4a7fa8,
    make: K => {
      const g = K.g();
      for (const x of [-1.5, 1.5]) {
        g.add(K.rot(K.at(K.tor(1.7, 0.14, 0x2f3640, { m: 0.8 }), x, 1.7, 0), 0, Math.PI / 2, 0));
        for (let i = 0; i < 10; i++)
          g.add(K.rot(K.at(K.cyl(0.035, 0.035, 3.3, 0xb0b7c0, { m: 0.9 }), x, 1.7, 0), 0, Math.PI / 2, i * Math.PI / 10));
      }
      g.add(K.at(K.box(3.0, 0.25, 2.4, 0x6b3a3a), 0, 2.2, 0));
      g.add(K.at(K.box(3.0, 2.6, 0.25, 0x6b3a3a), 0, 3.4, -1.1));
      for (const x of [-1.4, 1.4]) g.add(K.at(K.box(0.16, 0.16, 2.2, 0x9aa2ad, { m: 0.85 }), x, 2.7, 0.2));
      for (const x of [-1.0, 1.0]) g.add(K.rot(K.at(K.cyl(0.5, 0.5, 0.2, 0x2f3640), x, 0.5, 1.6), 0, Math.PI / 2, 0));
      g.add(K.at(K.box(1.8, 0.16, 0.9, 0x9aa2ad, { m: 0.85 }), 0, 0.9, 1.5));
      return g;
    },
  },
  {
    t: [33], name: 'Harry S. Truman', years: '1945–1953', peg: 'A painted-sky dome',
    why: 'TRUMAN. A studio dome with a door cut into the horizon — is any of this real?',
    hue: 0x5aa8e0,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(6.0, 0x7fc4f0, { t: 0.3, e: 0x3a8fd0, ei: 0.3, side: 2 }), 0, 0, 0));
      for (let i = 0; i < 9; i++) {
        const a = Math.random() * Math.PI * 2, r = 3.5 + Math.random() * 2;
        g.add(K.at(K.sph(0.7 + Math.random() * 0.6, 0xffffff, { t: 0.55 }), Math.cos(a) * r, 3.4 + Math.random() * 1.8, Math.sin(a) * r));
      }
      g.add(K.at(K.box(1.6, 3.4, 0.18, 0x2b3140), 0, 1.7, -5.6));
      g.add(K.at(K.box(1.3, 3.1, 0.22, 0x14171e, { e: 0x14171e, ei: 0.2 }), 0, 1.65, -5.5));
      g.add(K.at(K.sph(0.12, 0xc9a24a, { m: 0.9 }), 0.45, 1.6, -5.3));
      return g;
    },
  },
  {
    t: [34], name: 'Dwight D. Eisenhower', years: '1953–1961', peg: 'An icy shower',
    why: 'EISEN-HOWER → ICE SHOWER. Icicles instead of water, still running.',
    hue: 0x9fd8f0,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.14, 0.14, 6.4, 0xc0c6ce, { m: 0.9 }), 1.6, 3.2, 0));
      g.add(K.rot(K.at(K.cyl(0.14, 0.14, 1.8, 0xc0c6ce, { m: 0.9 }), 0.75, 6.3, 0), 0, 0, Math.PI / 2));
      g.add(K.rot(K.at(K.cyl(1.15, 0.5, 0.6, 0xdfe6ec, { m: 0.85 }), 0, 5.9, 0), Math.PI, 0, 0));
      for (let i = 0; i < 26; i++) {
        const a = Math.random() * Math.PI * 2, r = Math.random() * 1.0;
        g.add(K.at(K.cone(0.11, 0.7 + Math.random() * 1.5, 0xd6f2fb, { t: 0.72, e: 0x54b0d0, ei: 0.5 }),
          Math.cos(a) * r, 0.6 + Math.random() * 4.6, Math.sin(a) * r));
      }
      g.add(K.at(K.cyl(2.4, 2.4, 0.25, 0xe4e9ef), 0, 0.12, 0));
      for (let i = 0; i < 10; i++)
        g.add(K.at(K.box(0.4, 0.4, 0.4, 0xe8f6fc, { t: 0.65 }), (Math.random() - 0.5) * 3.4, 0.4, (Math.random() - 0.5) * 3.4));
      return g;
    },
  },
  {
    t: [35], name: 'John F. Kennedy', years: '1961–1963', peg: 'The Moon',
    why: '"We choose to go to the Moon." A cratered moon resting on the floor.',
    hue: 0xd8d8d0, anchor: true,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(3.0, 0xd0d0c8, { r: 0.95 }), 0, 3.2, 0));
      for (let i = 0; i < 16; i++) {
        const a = Math.random() * Math.PI * 2, b = Math.acos(2 * Math.random() - 1), r = 2.95;
        g.add(K.at(K.sph(0.25 + Math.random() * 0.55, 0xa8a8a0, { r: 1.0 }),
          Math.sin(b) * Math.cos(a) * r, 3.2 + Math.cos(b) * r, Math.sin(b) * Math.sin(a) * r));
      }
      g.add(K.at(K.cyl(1.2, 1.6, 0.4, 0x3a4250), 0, 0.2, 0));
      g.add(K.at(K.box(0.06, 1.2, 0.06, 0xc0c6ce, { m: 0.9 }), 2.2, 5.6, 1.4));
      g.add(K.at(K.box(0.6, 0.4, 0.03, 0xc4483a), 2.5, 6.0, 1.4));
      return g;
    },
  },
  {
    t: [36], name: 'Lyndon B. Johnson', years: '1963–1969', peg: 'A jaybird in a Stetson',
    why: 'L-B-JAY. Blue jay, ten-gallon hat, unmistakably Texan.',
    hue: 0x4a8fd0,
    make: K => {
      const g = K.g();
      g.add(K.at(K.sph(1.5, 0x3a7fd0), 0, 2.2, 0));
      g.add(K.at(K.sph(0.95, 0x4a8fe0), 0, 3.6, 0.5));
      g.add(K.at(K.cone(0.34, 1.0, 0xe8b93a), 0, 3.5, 1.5));
      for (const z of [0.35, -0.35]) g.add(K.at(K.sph(0.14, 0x1b1f28), 0.75, 3.9, z + 0.5));
      g.add(K.rot(K.at(K.box(2.2, 0.2, 1.0, 0x2f6fb8), -1.2, 2.4, 0.9), 0, 0.3, 0.3));
      g.add(K.rot(K.at(K.box(2.2, 0.2, 1.0, 0x2f6fb8), -1.2, 2.4, -0.9), 0, -0.3, 0.3));
      g.add(K.rot(K.at(K.cone(0.5, 2.4, 0x2f6fb8), -1.9, 1.8, 0), 0, 0, Math.PI / 2 + 0.3));
      g.add(K.at(K.cyl(1.5, 1.4, 0.14, 0x8a6a3a), 0, 4.3, 0.5));
      g.add(K.at(K.cyl(0.72, 0.8, 0.8, 0x9a7a4a), 0, 4.7, 0.5));
      for (const x of [-0.35, 0.35]) g.add(K.at(K.cyl(0.1, 0.1, 0.7, 0xe8a83a), x, 1.0, 0.2));
      return g;
    },
  },
  {
    t: [37], name: 'Richard Nixon', years: '1969–1974', peg: 'A reel-to-reel recorder',
    why: 'The tapes ended him. Both reels turning, nobody at the controls.',
    hue: 0x8a7f6b,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(5.4, 4.0, 1.2, 0x4a4238, { r: 0.6 }), 0, 3.0, 0));
      g.add(K.at(K.box(5.8, 0.5, 1.6, 0x2f2b24), 0, 0.8, 0));
      for (const x of [-1.4, 1.4]) {
        g.add(K.rot(K.at(K.tor(1.15, 0.16, 0xdfe6ec, { m: 0.6 }), x, 3.9, 0.7), 0, 0, 0));
        g.add(K.at(K.cyl(0.9, 0.9, 0.28, 0x2b2b2b), x, 3.9, 0.7));
        g.add(K.at(K.cyl(0.22, 0.22, 0.45, 0xc0c6ce, { m: 0.9 }), x, 3.9, 0.85));
      }
      g.add(K.at(K.box(2.6, 0.06, 0.2, 0x3a3630), 0, 2.9, 0.8));
      for (let i = 0; i < 5; i++) g.add(K.at(K.box(0.4, 0.22, 0.3, i === 2 ? 0xc4483a : 0xb0b7c0), -0.9 + i * 0.45, 1.5, 0.7));
      for (const x of [-2.0, 2.0]) g.add(K.rot(K.at(K.cyl(0.35, 0.35, 0.12, 0x8a8070, { m: 0.8 }), x, 1.6, 0.7), Math.PI / 2, 0, 0));
      return g;
    },
  },
  {
    t: [38], name: 'Gerald Ford', years: '1974–1977', peg: 'A Model T',
    why: 'FORD. Any car works, but the Model T is the one nobody mistakes for another peg.',
    hue: 0x2b2b2b,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(4.6, 1.1, 2.0, 0x1b1f28, { r: 0.5 }), 0, 1.4, 0));
      g.add(K.at(K.box(2.0, 1.5, 1.9, 0x22262e), -0.6, 2.6, 0));
      g.add(K.at(K.box(1.7, 1.0, 1.95, 0x9fd8ff, { t: 0.4 }), -0.6, 2.7, 0));
      g.add(K.at(K.box(1.6, 0.9, 1.7, 0x14171e), 1.8, 2.2, 0));
      for (const x of [-1.6, 1.7]) for (const z of [-1.15, 1.15]) {
        g.add(K.rot(K.at(K.tor(0.85, 0.24, 0x14171e), x, 0.9, z), 0, Math.PI / 2, 0));
        for (let i = 0; i < 8; i++)
          g.add(K.rot(K.at(K.cyl(0.03, 0.03, 1.6, 0xc9c0a0), x, 0.9, z), 0, Math.PI / 2, i * Math.PI / 8));
      }
      for (const z of [-0.7, 0.7]) g.add(K.at(K.sph(0.32, 0xffeeb0, { e: 0xffd24a, ei: 1.1 }), 2.6, 2.4, z));
      return g;
    },
  },
  {
    t: [39], name: 'Jimmy Carter', years: '1977–1981', peg: 'A cart of peanuts',
    why: 'CART-er, and he was a peanut farmer. Two hooks on one image.',
    hue: 0xd8a24a,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(3.4, 0.14, 2.2, 0xb0b7c0, { m: 0.85 }), 0, 1.4, 0));
      for (const s of [[0, 2.6, -1.1], [0, 2.6, 1.1]])
        g.add(K.at(K.box(3.4, 2.4, 0.12, 0xb0b7c0, { m: 0.85 }), s[0], s[1] - 1.0, s[2]));
      g.add(K.at(K.box(0.12, 2.4, 2.2, 0xb0b7c0, { m: 0.85 }), -1.7, 1.6, 0));
      g.add(K.at(K.box(0.12, 2.0, 2.2, 0xb0b7c0, { m: 0.85 }), 1.7, 1.4, 0));
      g.add(K.rot(K.at(K.cyl(0.09, 0.09, 2.2, 0xc4483a), 2.0, 3.0, 0), Math.PI / 2, 0, 0));
      for (const [x, z] of [[-1.4, -0.9], [1.4, -0.9], [-1.4, 0.9], [1.4, 0.9]])
        g.add(K.rot(K.at(K.cyl(0.34, 0.34, 0.16, 0x2f3640), x, 0.34, z), Math.PI / 2, 0, 0));
      for (let i = 0; i < 40; i++) {
        const p = K.g(), yy = 1.6 + Math.random() * 1.4;
        p.add(K.at(K.sph(0.26, 0xd8a86a, { r: 0.9 }), -0.16, 0, 0));
        p.add(K.at(K.sph(0.3, 0xd8a86a, { r: 0.9 }), 0.18, 0, 0));
        p.position.set((Math.random() - 0.5) * 3, yy, (Math.random() - 0.5) * 1.9);
        p.rotation.set(Math.random() * 3, Math.random() * 3, Math.random() * 3);
        g.add(p);
      }
      return g;
    },
  },
  {
    t: [40], name: 'Ronald Reagan', years: '1981–1989', peg: 'A ray gun',
    why: 'RAY-GUN. Chrome, finned, pointed at the sky. Star Wars, the programme.',
    hue: 0xe0503a, anchor: true,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.cyl(0.85, 0.7, 4.2, 0xdfe6ec, { m: 0.95, r: 0.12 }), 0, 3.4, 0.6), -0.35, 0, 0));
      g.add(K.rot(K.at(K.cyl(1.1, 0.85, 1.2, 0xc4483a, { m: 0.7 }), 0, 4.5, 2.2), -0.35, 0, 0));
      g.add(K.at(K.sph(0.8, 0x8fffd0, { e: 0x2ad898, ei: 1.6 }), 0, 4.9, 2.9));
      g.add(K.rot(K.at(K.box(1.0, 2.4, 0.4, 0xb0b7c0, { m: 0.9 }), 0, 1.6, -0.9), 0.25, 0, 0));
      for (let i = 0; i < 3; i++)
        g.add(K.rot(K.at(K.tor(0.95 + i * 0.12, 0.11, 0xe8b93a, { m: 0.85, e: 0x8a6a10, ei: 0.3 }), 0, 3.9 + i * 0.35, 1.4 + i * 0.9), Math.PI / 2 - 0.35, 0, 0));
      g.add(K.at(K.sph(1.0, 0xf0d060, { e: 0xd0a020, ei: 0.9 }), 0, 2.2, -0.2));
      return g;
    },
  },
  {
    t: [41], name: 'George H. W. Bush', years: '1989–1993', peg: 'A shrub',
    why: 'A perfectly ordinary, well-trimmed bush. Keep it dull — the son escalates it.',
    hue: 0x4a8a4a,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.4, 0.5, 1.2, 0x5a3a2a), 0, 0.6, 0));
      g.add(K.at(K.sph(2.2, 0x4a9a4a, { r: 0.95 }), 0, 3.0, 0));
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        g.add(K.at(K.sph(1.0 + Math.random() * 0.5, 0x56a856, { r: 0.95 }),
          Math.cos(a) * 1.7, 2.4 + Math.random() * 1.6, Math.sin(a) * 1.7));
      }
      g.add(K.at(K.cyl(2.9, 3.1, 0.9, 0xb08a5a, { r: 0.9 }), 0, 0.45, 0));
      return g;
    },
  },
  {
    t: [42], name: 'Bill Clinton', years: '1993–2001', peg: 'A saxophone',
    why: 'The Arsenio moment. A brass tenor sax, taller than you are.',
    hue: 0xd8a83a,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.42, 0.5, 3.6, 0xd8a83a, { m: 0.9, r: 0.2 }), 0, 3.0, 0));
      g.add(K.rot(K.at(K.tor(0.85, 0.45, 0xd8a83a, { m: 0.9, r: 0.2 }), 0, 1.3, 0.6), Math.PI / 2, 0, 0));
      g.add(K.rot(K.at(K.cyl(1.5, 0.62, 1.9, 0xe8bb4a, { m: 0.9, r: 0.2 }), 0.1, 1.5, 1.9), -0.7, 0, 0));
      g.add(K.rot(K.at(K.cyl(0.3, 0.36, 1.4, 0xd8a83a, { m: 0.9 }), 0, 5.2, -0.4), 0.5, 0, 0));
      g.add(K.rot(K.at(K.cyl(0.28, 0.2, 0.7, 0x1b1f28), 0, 5.9, -0.9), 0.5, 0, 0));
      for (let i = 0; i < 9; i++)
        g.add(K.rot(K.at(K.cyl(0.2, 0.2, 0.1, 0xf0d878, { m: 0.95 }), 0.42, 1.9 + i * 0.34, 0.15), Math.PI / 2, 0, 0.4));
      return g;
    },
  },
  {
    t: [43], name: 'George W. Bush', years: '2001–2009', peg: 'The BURNING bush',
    why: 'Same shrub as his father, now fully alight. Escalation encodes the pair.',
    hue: 0xe07a2e,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(0.4, 0.5, 1.2, 0x3a2a1a), 0, 0.6, 0));
      g.add(K.at(K.sph(2.2, 0x3a5a2a, { r: 0.95 }), 0, 3.0, 0));
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        g.add(K.at(K.sph(1.0, 0x44662e, { r: 0.95 }), Math.cos(a) * 1.7, 2.4 + Math.random() * 1.4, Math.sin(a) * 1.7));
      }
      for (let i = 0; i < 16; i++) {
        const a = Math.random() * Math.PI * 2, r = Math.random() * 2.1, h = 1.2 + Math.random() * 2.6;
        g.add(K.at(K.cone(h * 0.32, h, [0xff6a1e, 0xffa524, 0xffd85e][i % 3], { e: 0xff7a1e, ei: 1.0 }),
          Math.cos(a) * r, 3.4 + Math.random() * 1.6 + h / 2, Math.sin(a) * r));
      }
      g.add(K.at(K.cyl(2.9, 3.1, 0.9, 0x7a5a3a, { r: 0.9 }), 0, 0.45, 0));
      return g;
    },
  },
  {
    t: [44], name: 'Barack Obama', years: '2009–2017', peg: 'A llama',
    why: 'o-BAMA / LLAMA. It rhymes, it is absurd, and it will not leave your head.',
    hue: 0xc9a882,
    make: K => {
      const g = K.g();
      g.add(K.at(K.box(2.8, 1.8, 1.5, 0xd8bb92, { r: 0.95 }), 0, 2.6, 0));
      g.add(K.rot(K.at(K.cyl(0.5, 0.62, 2.6, 0xd8bb92, { r: 0.95 }), 1.1, 4.2, 0), 0, 0, -0.35));
      g.add(K.rot(K.at(K.box(0.9, 0.8, 1.0, 0xe4cba4), 1.9, 5.4, 0), 0, 0, -0.35));
      g.add(K.at(K.box(0.7, 0.5, 0.85, 0xc9a882), 2.4, 5.4, 0));
      for (const z of [-0.3, 0.3]) g.add(K.at(K.cone(0.16, 0.7, 0xe4cba4), 1.6, 6.0, z));
      for (const z of [-0.35, 0.35]) g.add(K.at(K.sph(0.13, 0x2b2b2b), 2.3, 5.7, z));
      for (const x of [-0.9, 0.9]) for (const z of [-0.5, 0.5])
        g.add(K.at(K.cyl(0.22, 0.2, 1.8, 0xc9a882), x, 0.9, z));
      g.add(K.rot(K.at(K.cyl(0.16, 0.1, 1.0, 0xd8bb92), -1.5, 3.0, 0), 0, 0, 0.7));
      g.add(K.at(K.box(1.9, 0.25, 1.6, 0xc4483a), 0, 3.6, 0));
      return g;
    },
  },
  {
    t: [45, 47], name: 'Donald Trump', years: '2017–2021, 2025–', peg: 'A trumpet',
    why: 'TRUMP-et. Like Cleveland, you will pass through here twice.',
    hue: 0xe8c04a, twice: true,
    make: K => {
      const g = K.g();
      g.add(K.rot(K.at(K.cyl(0.34, 0.34, 4.4, 0xe8c04a, { m: 0.95, r: 0.15 }), 0, 3.0, 0), 0, 0, Math.PI / 2));
      g.add(K.rot(K.at(K.cyl(1.7, 0.4, 2.0, 0xf0cf6a, { m: 0.95, r: 0.15 }), 3.2, 3.0, 0), 0, 0, -Math.PI / 2));
      g.add(K.rot(K.at(K.tor(1.7, 0.14, 0xf6dd8a, { m: 0.95 }), 4.2, 3.0, 0), 0, Math.PI / 2, 0));
      g.add(K.rot(K.at(K.cyl(0.26, 0.4, 0.7, 0xd8b03a, { m: 0.95 }), -2.5, 3.0, 0), 0, 0, Math.PI / 2));
      for (let i = 0; i < 3; i++) {
        g.add(K.at(K.cyl(0.26, 0.26, 1.0, 0xd8b03a, { m: 0.95 }), -0.6 + i * 0.7, 3.7, 0));
        g.add(K.at(K.cyl(0.3, 0.3, 0.2, 0xf6dd8a, { m: 0.95 }), -0.6 + i * 0.7, 4.3, 0));
      }
      g.add(K.rot(K.at(K.tor(0.9, 0.16, 0xe8c04a, { m: 0.95 }), -1.4, 2.2, 0), 0, Math.PI / 2, 0));
      return g;
    },
  },
  {
    t: [46], name: 'Joseph R. Biden', years: '2021–2025', peg: 'A bidet',
    why: 'BIDEN → BIDET. One consonant apart. Aviators optional.',
    hue: 0x6ab8d8,
    make: K => {
      const g = K.g();
      g.add(K.at(K.cyl(1.5, 1.0, 2.4, 0xf4f8fb), 0, 1.2, 0));
      g.add(K.at(K.cyl(1.7, 1.7, 0.4, 0xffffff), 0, 2.5, 0));
      g.add(K.rot(K.at(K.tor(1.5, 0.22, 0xe8eef4), 0, 2.6, 0), Math.PI / 2, 0, 0));
      g.add(K.at(K.cyl(1.3, 1.3, 0.2, 0x6ab8e8, { t: 0.7 }), 0, 2.4, 0));
      g.add(K.rot(K.at(K.cyl(0.16, 0.16, 1.1, 0xc0c6ce, { m: 0.92 }), 0, 3.1, -1.3), 0.5, 0, 0));
      for (let i = 0; i < 16; i++) {
        const p = i / 16;
        g.add(K.at(K.sph(0.16, 0x8fd8f4, { t: 0.65, e: 0x3a8fc0, ei: 0.5 }),
          0, 3.6 + Math.sin(p * Math.PI) * 2.2, -1.0 + p * 1.9));
      }
      g.add(K.at(K.box(1.4, 0.3, 0.5, 0x1b1f28), 0, 3.4, 1.8));
      for (const x of [-0.4, 0.4]) g.add(K.at(K.cyl(0.32, 0.32, 0.08, 0x2b3140, { t: 0.7 }), x, 3.4, 1.85));
      return g;
    },
  },
];

// The walk: 47 stops in order, two of which revisit a room already seen.
export const STOPS = PRESIDENTS
  .flatMap((p, roomIndex) => p.t.map(term => ({ term, roomIndex, p })))
  .sort((a, b) => a.term - b.term);
