# Potential

The 22 core topics, and where each one actually stands.

Status checked 2026-09-07 by reading the pages, not guessing.

## Built

| Topic | Lives at |
|---|---|
| non-linearity | `curves.html` — S, J, exponential, diminishing returns, U, inverted-U |
| emotion wheel | `emotion-wheel.html` — Plutchik's 8, rotatable, spin |
| 1 percent is not 0% | `one-percent.html` + `make_one_percent.py` → 32 cards |
| hormones | `posts/hormones/index.html` |
| fractals | `fractals.html` — 2D + 3D trees |
| bliss symbolics | `bliss.html`, `bliss-dictionary.html`, `posts/bliss/` |
| how learning works | `learning-stone.html` — sourced to Sapolsky, *Behave* pp.138-139 |
| the elephant and the rider | `posts/elephant_rider/index.html` — Haidt |
| genetics | `genetic-code.html` + `posts/dna.html` |
| genetics → amino acids | `genetic-code.html` — codons → amino acids |
| phenotype vs. genotype | `posts/dna.html` |
| the angel and the dragon | `gg/gg-posts/current/angel_and_dragon/index3.html` |
| 526 years | `524-years.html` |
| waves | `posts/waves/` + waves2, waves3 — **stub, one line** |

## Not written

1. black vs. white (all or nothing)
2. neurotransmitters
3. triggers
4. uncertainty
5. certainty vs. uncertainty
6. addiction
7. distance vs. heat/humidity

## Things to settle

- **524 or 526?** Every page says 524. The list says 526.
- **"angle" is "angel."** And the **soldiers** don't appear in the page.
- **`posts/binary/` is NOT the all-or-nothing piece.** It's about computer
  binary — bits, bytes, `A = 65`. The psychological one doesn't exist.
- **Waves is a stub** and exists in three versions.
- **Content is scattered** across the repo root (~397 html), `posts/` (~52),
  and an older `gg/` tree. Bliss exists in all three.

## Visual notes

Built with d3 / three.js / GSAP / SVG. Some of these should be standalone
visual pieces rather than illustrations for text — a diagram serves the
article, a piece has to hold up with the words removed.

Ideas parked:
- **black vs. white** — a thousand-value gradient, then a threshold slams
  down and every value snaps to pure black or white. Drag the threshold to
  watch which information dies.
- **uncertainty** — three.js. A cloud of possible futures that collapses to a
  point when you demand an answer, then re-expands.
- **addiction** — the tolerance curve: baseline sinking while the required
  dose climbs, until the dose only restores you to where you started.
