# Design notes

Why the palace is shaped the way it is. These are the decisions worth not
re-deriving later.

---

## 1. The route is the data structure

In a memory palace the spatial sequence *is* the information. That turns level
design rules you would normally ignore into hard requirements:

- **Strictly linear. No branching.** A fork destroys recall order — you can no
  longer say "and then". Every branch is a place the sequence can break.
- **No shortcuts back.** If the route can be short-circuited, the order stops
  being forced by the geometry.
- **Anchors at intervals.** Every fifth or tenth stop needs to look
  categorically different, so you can count off in fives rather than replaying
  from stop one.

This is why the corridor palace is a serpentine of single-exit rooms and not an
open plan, and why the landscape has a fixed region order rather than free roam.

## 2. Weird and huge beats tasteful and accurate

Exaggerated scale, motion, and absurd interaction encode far better than
faithful depiction. A forty-foot chrome top hat you walk *under* is more
memorable than a historically correct one.

Convenient consequence: the aesthetic that helps memory is also the cheapest to
build — big, saturated, low-poly, one object per place. Fidelity is not the
goal and would actively cost recall.

## 3. Two peg systems, mixed on purpose

Covered in `peg-list.md`. Short version: sound-alikes for the forgettable
presidents, iconic images for the ones who already own a picture, and
**escalation** for related presidents so a pair is stored as a pair.

The escalation trick is the strongest idea in the peg list and should survive
any redesign. Adams is an atom, his son is an atom *bomb*.

## 4. Non-consecutive terms are encoded spatially

Cleveland is #22 and #24. Trump is #45 and #47. The temptation is to give each
two places and paper over it.

Instead: **one place, entered twice**, with the interrupting president in a
dead-end alcove off that same place. You walk in, get interrupted, come back
out. Both ordinals are painted on the wall side by side.

The building *teaches* the fact instead of storing it. Preserve this in any
future version — it is the single best structural idea in the project.

## 5. A second cue per place, independent of the object

Every room in the corridor palace has its own wallpaper (fourteen procedural
patterns, assigned so consecutive rooms never share one) and its own colour
signature. This is not decoration.

If recall rests entirely on the peg object, a blank on the object is a total
blank. An independent surface cue gives a second route in. In the landscape,
the biome does this job at a much larger scale.

Cost, accepted knowingly: lit patterned walls reflect more than flat dark ones,
so the palace is less moody than it was. Distinguishable beat moody.

## 6. Chunking — the reason the landscape exists

A flat run of 47 has no coarse index. Five regions of ten gives one:

```
region  →  which ten     (Sand Sea = 31–40)
site    →  which one     (4th station = #34)
```

Five things to hold instead of forty-seven. "Which decade?" becomes answerable
at a glance, which the corridor palace cannot do at all.

Split is 10 / 10 / 10 / 10 / 7 = 47.

## 7. The station template (BUILT — see `../walkway/`)

**The idea:** each region contains the same ten place-*types* in the same
spatial arrangement. Something like: the gate, the tree, the well, the cabin,
the bridge, the tower, the barn, the pond, the shrine, the overlook.

You learn **one ten-stop route shape once** and reuse it five times. The address
becomes three levels:

```
#34  →  Sand Sea (31–40)  →  station 4, the cabin  →  the peg inside it
```

Why this is strong:

- The within-region route stops being arbitrary. It is the same walk every time.
- "Which one of the ten" becomes a *named* slot, not a count.
- Authoring collapses: build ten station models once, dress them per biome.

**The real risk — interference.** Five near-identical layouts can blur into each
other: you recall the well, but not *which* well. Mitigations, in order of
force:

1. Lean hard on biome dressing. The desert cabin and the tundra cabin must not
   merely be recoloured — different materials, silhouette, surroundings.
2. Vary the *arrangement* between regions while keeping the *set* of ten. Same
   stations, different walk order or spacing.
3. Give each region one station the others do not have.

Option 1 alone is probably enough given how distinct the biomes already are,
and it costs the least. Start there.

**Conflict to resolve:** the doubled presidents. Cleveland at #22 and #24 lands
on stations 2 and 4 of region 3 — but "one place entered twice" wants them to
be the *same* station. Cleanest resolution: region 3 has **nine** distinct
stations, one of which you visit twice, with Harrison's station between them.
Same for Trump in region 5. This is a feature, not damage — those two regions
being structurally odd is itself a memory hook.

## 8. Placement must change to support §7

The landscape currently places sites by **farthest-point sampling** — spread
ten points across the region, then chain them into a short walk. That is right
for arbitrary sites and *wrong* for a fixed template.

When the template lands, `placeSites()` in `terrain/src/world.js` gets replaced
by template instancing: one canonical arrangement of ten offsets, placed at each
region's centre, rotated to fit the terrain, with each station snapped to
walkable ground.


---

## 9. Scale — corrected 2026-08-11

The corridor palace was **wrong about size**, and the note in §2 above needs
reading with this caveat. "Monumental" was taken too far: props were 4–7 m tall
on 5 m-radius plinths, which meant

- you had to walk *around* every object to pass it, and
- at conversational distance the object filled the view and stopped reading as
  an object at all. It became architecture.

The corrected rule, implemented in `../walkway/`:

**Every peg is normalised to ~1.8 m and stands on a surface at waist-to-chest
height that you walk up to.** The well rim, the cabin table, the cairn, the
bridge post cap. Nothing to circle, nothing towering.

`PEG_H` in `walkway/src/main.js` is the single knob. Pegs are auto-normalised —
each peg group is measured with a `Box3` and scaled so its largest dimension
hits `PEG_H`, then seated so its base rests on the display point. That means
peg builders can stay authored at any size and still come out consistent.

## 10. The map is not a separate screen

Also corrected in the walkway. The palace had two camera modes with a tween
between them; the landscape had three view buttons. Both read as *switching
screens*.

The walkway instead has **one continuous parameter** (`lift`, 0→1) driven by
the scroll wheel. At 0 the eye sits at the player looking along their facing —
that *is* the first-person view. At 1 it sits above the valley looking at its
centre. Everything between is a straight interpolation of eye, look-target,
FOV and fog distances, so there is no seam to hide and no mode to switch.

One code path, not two blended cameras. Keep it that way.
