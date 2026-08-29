# Glowing Gardens - Design Philosophy

## No Scroll Policy
Users should scroll as little as possible. Each page should fit on one screen at a reasonable desktop size (not optimized for phones).

- Use fixed sidebars for context/explanations instead of stacking content vertically
- Keep visualizations compact and self-contained
- If content must extend, prefer horizontal layouts or steppers over vertical scrolling

---

# Music Project (`_music/`)

User has a deep music-analysis workflow built on Hookpad chord/melody data.

## Key data locations

| Path | What |
|---|---|
| `~/Desktop/music/hookpad_songs_full/` | Fresh API-pulled Hookpad JSONs (1432+ files, current) |
| `~/Desktop/music/hookpad_songs/hookpad_songs/` | Legacy partial export (1006 files, older) |
| `~/Desktop/music/songs_to_learn.csv` / `.xlsx` | User's learning tracker (1117 rows) |
| `parcels.songs` (Supabase, themap project) | Loaded table; structure as JSONB |
| `_music/.env` | Spotify creds (gitignored) |
| `/Users/robert/Desktop/themap/themap_claude/.env` | Supabase creds — load via `dotenv` |

## Python venv

Use `/Users/robert/Desktop/themap/themap_claude/.venv/bin/python` — has `supabase`, `hashids`, `cmudict`, `pyphen`, `requests` installed. Music-specific deps (librosa, sklearn) live in `_music/.venv`.

## Scripts in `_music/`

- `sync_hookpad.py` — bulk/incremental sync from Hookpad API. Use `--throttle 20` for safety, `--throttle 6` minimum. Auto-backs-off on 429.
- `download_one.py` — single song by `--slug`, `--id`, or `--name`. Zero list calls when using `--id`.
- `load_songs_to_supabase.py` — rebuilds `parcels.songs` from CSV + Hookpad JSONs. Run with `--wipe` for clean reload.
- `melisma_align.py` — aligns lyrics to melody notes, marks melisma. Encodes 12 heuristic rules.
- `melisma_examples.json` — verified test corpus (11+ examples).
- `validate_corpus.py` — runs `melisma_align` against the corpus, reports pass/fail per song.

## Hookpad API quirks

- Auth: Bearer token from any open Hookpad tab (DevTools Network → copy as cURL).
- List endpoint: `GET /v1/songs/h?per-page=100&page=N` returns `[{ID, dateModified, song}, ...]`. Only those 3 fields, no slug.
- Single-song: `GET /v1/songs/{slug}?fields=ID,xmlData,song,jsonData,isPrivate`. Slug = `Hashids(salt='XI0Y4UFrK6EPLnarrI4y', min_length=11, alphabet='A-Za-z-_').encode(numeric_id)`. The salt/alphabet are extracted from the Hookpad JS bundle.
- **Rate limiting**: 6 sec/song works most of the time. 20 sec/song never hits 429. Bulk list (15 paginated calls) at 0.1s between pages will trigger 429 — use ≥3s between pages.
- If 429 happens: stop ALL API calls (the script's backoff handles it, but external refresh of the Hookpad app also resets the cooldown — tell user not to refresh).

## Hookpad clipboard paste-import (VERIFIED 2026-05-13)

Hookpad's paste handler accepts arbitrary JSON if the `fp` fingerprint validates. Algorithm:

1. Build the object with keys in this order: `notes`, `chords`, `audioTracks` (and `fp` last, but excluded from hash)
2. Each chord must have keys in this exact order: `root, beat, duration, type, inversion, applied, adds, omits, alterations, suspensions, substitutions, pedal, alternate, borrowed, isRest, recordingEndBeat`
3. JSON-stringify the object (no fp) with `separators=(',',':')` — JS compact style
4. SHA-1 the UTF-8 bytes → that hex digest is the `fp` value
5. Add `fp` to the object and re-serialize

Bypass options if you don't want to compute fp: include `version: 1` in the object, or set `fp: "1564"` literally. Either of those skips validation.

This unlocks **programmatic song import**: chord-chart parser → paste-compatible JSON → user pastes into Hookpad → song appears. Reference code in conversation history; first working example was a I-IV-V-I, fingerprint `81d2ad45cbb6be919f675caebd42b838f5bb3792`.

**Full-song paste verified 2026-05-14**: pasting a complete song object — including `notes`, `chords`, `keys`, `tempos`, `meters`, `sections`, `breaks`, `endBeat`, `audioTracks` — into an empty Hookpad session works. The `studied-songs.html` browser has a "Copy song as Hookpad paste-JSON" button that does this. Full round-trip is now: pull from Hookpad API → analyze/visualize locally → paste back into Hookpad UI. No need to manually re-enter chords/melody.

## Chord data quirks (very important)

Inside a Hookpad JSON, each chord has:
- `root` — integer 1-7 (scale degree in the song's key)
- `type` — string like `"5"` (power/triad), `"7"` (dominant 7), `"m"` (minor — rare in practice; quality usually implied by key context)
- `borrowed` — string indicating the parallel mode the chord is borrowed from: `minor`, `dorian`, `mixolydian`, `harmonicMinor`, `phrygian`, `lydian`, `major`, `phrygianDominant`, `locrian`. Can also be a LIST for custom scales.
- `applied` — integer (secondary dominant target degree, e.g. `5` = V/V)

**The big trap**: the same chord letter (e.g. Eb in C major = bIII) can have *different* `borrowed` labels across Hookpad files — `'minor'`, `'dorian'`, `'mixolydian'` all imply a flat-3 chord. So when querying for "songs that use Eb", accept ANY non-empty borrowed flag on `root=3`, not just `borrowed='minor'`.

## Roman numeral convention

The `structure.chords` column in `parcels.songs` stores tokens like `I5`, `V5`, `VI5`, `III5` (uppercase + Hookpad type). My loader does NOT yet lowercase minor-quality chords based on key. So `iii` (lowercase) doesn't appear in the data — search for `III*` to find iii chord occurrences in major-key songs.

To-fix-someday: rewrite Roman-numeral conversion in `load_songs_to_supabase.py` to lowercase chords based on the actual quality in the key (e.g., `root=3` in major = iii lowercase; `root=3` in minor = III uppercase).

## Common analysis patterns

- **Songs/sections that use chord X**: filter `parcels.songs` rows, walk `structure[].chords`, match substring or `borrowed`+`root` combo.
- **Always check key_scale**: minor-key songs have different Roman-numeral conventions; filter to `key_scale='major'` for "borrowed chord" analysis.
- **Dedupe sections**: a song with 3 verses on the same chords counts 3× unless you dedupe by (artist, title, section name, chord seq).
- **For "how often does X happen" queries**: pull all rows once via Supabase client into Python, walk in-memory. Don't try complex JSONB queries via PostgREST.

## Melisma alignment workflow

User has a verified format for marking melisma in lyrics: 1 token = 1 note. Multi-syllable words stay intact unless melisma falls inside the word, in which case they're split into syllables. Melisma extensions repeat the last syllable or use a vowel token.

The script `melisma_align.py` implements 12 heuristic rules (Rules 1-12, documented in `~/.claude/projects/-Users-robert-Desktop-glowinggardens-claude/memory/music_melisma_alignment.md`). Validation against the corpus is the dev loop — add new examples to `melisma_examples.json`, re-run `validate_corpus.py`, tune rules until match rate climbs.

Currently 2/11 examples match exactly (Lucy, Friday v2). Remaining gaps are mostly the "concentrated melisma on emphasized syllables" hard case (Rule 6), which requires lyric-importance info pure rhythm can't provide.
