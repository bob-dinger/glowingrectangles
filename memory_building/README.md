# Memory Building

Notes for the presidential memory palace project. Started August 2026.

**The goal:** be able to name all 47 US presidencies in order, cold, by walking
a place in your head. The software is a means to that — a way to author and
rehearse the palace, not a game for its own sake.

---

## What exists right now

| Thing | Where | State |
|---|---|---|
| **The corridor palace** | `../palace/` | Working. 45 rooms, 47 stops, first-person walk, quiz mode, overhead plan. |
| **The landscape testbed** | `../terrain/` | Working as a *testbed*. Terrain, biomes, river, lake, 47 numbered sites. No presidents on it yet. |
| **The walkway (exemplar)** | `../walkway/` | Working. ONE region built properly: ten stations on a path, presidents 1-10, human-scale pegs, continuous ground↔map. **This is the template the other four regions copy.** |
| **The peg list** | `peg-list.md` | Settled, 45 pegs. Generated from source. |
| **Design reasoning** | `design-notes.md` | Why the palace is shaped the way it is. |
| **Open decisions** | `open-questions.md` | What still has to be settled, with recommendations. |

Both pages are **single self-contained HTML files** with three.js inlined. They
work over `file://`, would drop onto GitHub Pages as-is, and are published as
private artifacts.

### Building

Each folder is its own npm project with the same two-file setup:

```
cd palace   # or terrain
node build.mjs
```

That bundles `src/main.js` (tree-shaking three.js) and inlines it into two
outputs: `index.html` (standalone, has doctype) and `artifact.html` (body
content only, for publishing). Edit `src/`, never the built HTML.

### The files that matter

```
palace/src/presidents.js   45 pegs + a procedural prop builder for each
palace/src/main.js         room layout, walking, wallpaper, overhead view
terrain/src/world.js       biome table, noise, river/lake carving, site placement
terrain/src/main.js        meshes, orbit camera, legend
```

`terrain/src/world.js` deliberately contains **no three.js** — it is pure data,
so world generation can be reasoned about and tested in node on its own. Keep
it that way.

---

## The two designs, and why there are two

**The corridor palace** is a strict line of rooms. It works, and the
non-consecutive terms are encoded beautifully (see `design-notes.md`), but it
has one flaw: recall is *linear*. To answer "who was 34?" you either know it
outright or count from the start. There is no coarse index.

**The landscape** exists to fix that. Five regions of ten gives a two-level
address — the region tells you which ten, the site tells you which one within
it. That is the whole reason to switch.

The landscape is expected to **replace** the corridor palace once the pegs are
ported onto it. The corridor is not a thing to maintain in parallel.

---

## Next actions, in order

1. ~~Settle the station template~~ — **done**, built in `../walkway/`. The ten
   are: gate, great tree, well, bridge, mill, cabin, loft, barn, shrine,
   overlook. Re-skin these for the other four regions rather than inventing new
   station sets.
2. Decide whether regions map to **eras** or stay arbitrary buckets of ten.
3. Port the 45 peg props from `palace/src/presidents.js` onto landscape sites.
4. Add ground-level movement to the landscape.
5. Retire the corridor palace.
