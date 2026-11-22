# Music Project (`_music/`)

This folder is its own Claude project: start Claude here for anything music. The
blog side (glowingrectangles.io, Substack) is the parent folder's project. The
parent `CLAUDE.md` (design philosophy) still applies here.

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

- `hookpad_token.py` — grabs a live bearer token so no session starts with DevTools. `--show` prints it without writing the file.
- `sync_hookpad.py` — bulk/incremental sync from Hookpad API. Use `--throttle 20` for safety, `--throttle 6` minimum. Auto-backs-off on 429.
- `download_one.py` — single song by `--slug`, `--id`, or `--name`. Zero list calls when using `--id`.
- `load_songs_to_supabase.py` — rebuilds `parcels.songs` from CSV + Hookpad JSONs. Run with `--wipe` for clean reload.
- `melisma_align.py` — aligns lyrics to melody notes, marks melisma. Encodes 12 heuristic rules.
- `melisma_examples.json` — verified test corpus (11+ examples).
- `validate_corpus.py` — runs `melisma_align` against the corpus, reports pass/fail per song.
- `audio_to_hookpad.py` — a recording → Hookpad song with the sung melody (demucs vocal split → basic-pitch → one line on the band's beat grid → scale degrees) and rough chords. Run with `.venv_audio/bin/python` (Python 3.11, has demucs/basic-pitch/torch); `--base <json>` keeps that song's chords and replaces only the melody; `--upload` creates it private. Work files in `~/Desktop/music/audio_work/<name>/` (audio stays out of the repo). Nashville Blues: key and tempo guessed right, 73% of verse notes right to the half beat. A draft for cleanup, and a strong check on a hand transcription.

## Hookpad API quirks

- Auth: run `hookpad_token.py`. It loads Hookpad in the Playwright context that already has saved auth (`~/.hookpad_auth.json`), watches the requests the app makes, and lifts the bearer off the first API call — writing it to `~/.hookpad_token` (mode 600, outside the repo). `sync_hookpad.py`, `download_one.py`, `update_songs.py` and `pull_by_pattern.py` all read it, so **`--token` is optional now**; precedence is `--token` > `$HOOKPAD_TOKEN` > `~/.hookpad_token`. If the saved auth has expired, `setup_hookpad_auth.py` logs in once more. Manual fallback, no longer needed day to day: any open Hookpad tab, DevTools Network → copy as cURL.
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

Bypass options if you don't want to compute fp: include `version: 1` in the object, or set `fp: "1564"` literally. Either of those skips validation. **Hookpad 2 only: Hookpad 3 rejects any `version` but its own ("unsupported version").** For pastes that work in both, use `hp3.clipboard(obj)`: no version, real fp, numbers printed the way JavaScript prints them (2.0 → 2) so the browser's SHA-1 matches (VERIFIED pasting into Hookpad 3, 2026-11-20). Hookpad 3's paste takes its own `hooktheory-clipboard-v1` envelope, or our Hookpad 2 fields (notes/chords/keys/meters/tempos/sections/breaks; fp checked only if present; lyrics aren't part of a paste). All paste builders were switched on 2026-11-20: about 40 Python scripts write through `hp3.clipboard`, and the page copy buttons (sections*, simplified-library, hold-patterns + template, chord-chart-visualizer) use a JS `hpPaste()` that gives byte-identical output. New paste code should do the same.

This unlocks **programmatic song import**: chord-chart parser → paste-compatible JSON → user pastes into Hookpad → song appears. Reference code in conversation history; first working example was a I-IV-V-I, fingerprint `81d2ad45cbb6be919f675caebd42b838f5bb3792`.

**Full-song paste verified 2026-05-14**: pasting a complete song object — including `notes`, `chords`, `keys`, `tempos`, `meters`, `sections`, `breaks`, `endBeat`, `audioTracks` — into an empty Hookpad session works. The `studied-songs.html` browser has a "Copy song as Hookpad paste-JSON" button that does this. Full round-trip is now: pull from Hookpad API → analyze/visualize locally → paste back into Hookpad UI. No need to manually re-enter chords/melody.

## Creating songs via the API (VERIFIED 2026-10-30)

`hookpad_upload_variants.upload(tok, name, obj)` creates a private song (POST /v1/songs, then PATCH isPrivate). The object must be the WHOLE saved project, built with `tempo_variant_pastes.full_json(d, 1)` from a downloaded file, then edited. A paste-style object (notes/chords/keys/tempos/sections only) saves fine but Hookpad refuses to open it ("can't be opened by this version of hookpad"): it needs `version`, `bands`, `settings`, etc. An existing song can be overwritten with `PATCH /v1/songs/{ID} {jsonData: json_data(obj)}`. Never empty `inactiveNotes` (the melody layers): `activeMelodyIndex` points into it, and a song whose active layer is gone gives the same "can't be opened" error by URL and hangs in the UI (Talk, 2026-11-01).

## Hookpad 3 (released 2026-11-18, VERIFIED 2026-11-20)

hookpad.hooktheory.com is now Hookpad 3; Hookpad 2 keeps working. Same API (`api.hooktheory.com/v1/songs`, same fields; the app itself calls `www.hooktheory.com/v1`), and our token grab, reads, POST uploads and PATCHes all still work. Songs we upload open in 3. But:

- **Saving in 3 makes a NEW song with the same name** (list entry `madeInHookpad3: true`); the Hookpad 2 original is left untouched.
- **New format** (`version: "3.x"`, `ppqn: 480`, `score.sections[]` each holding its own notes/chords/keys/tempos/meters/swings/lyrics in ticks, `score.arrangement[]` = section order, note `voice` 1-4). Applied chords are flipped (3: root = target, applied = function). A note crossing a section boundary is split, second half has an `n_` id.
- `hp3.py` converts 3 → the Hookpad 2 shape (verified exact on Tangled Up in Blue: 1254 notes, 172 chords, sections, lyrics, corpus analyses identical). `sync_hookpad`, `download_one`, `update_songs`, `pull_by_pattern` save Hookpad 3 songs converted (raw kept in `~/Desktop/music/hookpad_songs_hp3/`) and keep the newest copy per name. Converted files carry `hp3: true`.
- **Writing works both ways (VERIFIED in the Hookpad 3 UI 2026-11-20)**: scripts keep editing the Hookpad 2 shape; `hp3.from_hp2(edited, live)` puts it back into the live Hookpad 3 song (instruments, mixer, section ids kept; resized sections get their regions and drum markers rebuilt; boundary-crossing notes re-split with `n_` ids). `hookpad_upload_variants.call` does this automatically for any PATCH of a Hookpad 3 song; `lyrics_run`, `fill_repeat_chords`, `three_way_fill` read live copies through `hp3.to_hp2`. Round trips on Tangled are exact. New uploads can go either way: POST the Hookpad 2 format (3 opens it, but the user's first save makes a copy), or POST `json.dumps(hp3.from_hp2(o, base_hp3_song))` with no fp, which the server flags `madeInHookpad3` and the user's saves update in place, no copy (VERIFIED 2026-11-20, hp3test-new1120). Prefer the Hookpad 3 route for new songs and templates now that the user works in 3. The base supplies instruments and mixer (any downloaded Hookpad 3 song, raw copies in `hookpad_songs_hp3/`).
- `hp3test-write1120` (two copies, Hookpad 2 + 3) are kept as test fixtures; `corpus.is_scratch` ignores `hp3test*`.
- **The user works in Hookpad 3 from 2026-11-20 on.** First save of a Hookpad 2 song opens a filename popup already filled with the same name, and accepting it keeps the name, which is what our name matching needs. Later saves go in place. Don't edit the old original in Hookpad 2 afterwards, or it becomes the newest and the scripts follow it. Parked follow-ups (`-hp2` rename tidy, per-upgrade check) are in memory.
- Hookpad 3 deletes `?idOfUserSong=` (and `idOfSong`) from the address bar once a song loads (on purpose, in its code). Our links still open songs, but the user can't copy a link out of the bar, so give full links when asked. Don't suggest "Create Shareable Link": the guide says it saves a copy.
- `template_8` in Hookpad 3 is ID 101374908 (`template_8.py --upload --id 101374908`); the Hookpad 2 original is 101367296. `template_8-melodies` in Hookpad 3 is ID 101374936 (`template_8_melodies.py --upload --id 101374936`). `template_8-full` (each template section with a real library melody moved onto its chords, at that song's tempo) is ID 101374993 (`template_8_full.py --upload --id 101374993`). `template_starlight-combos` (Starlight verse rhythm under the 12 commonest loops, melody "follows" vs "same notes"; `rhythm_combos.py` works for any section) is ID 101375012; `template_under-the-bridge-combos` (its second verse) is ID 101375614.
- Login: the saved auth must be from a Hookpad 3 sign-in (`setup_hookpad_auth.py`); the Hookpad 2-era one gave "Sign in to use Hookpad 3" and no token.

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
