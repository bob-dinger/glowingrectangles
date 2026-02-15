# Hookpad File Parsing

Instructions for parsing Hookpad files and generating song structure visualizations.

## File Format

### .hookpad files
ZIP archives containing `project.json`. Extract with:
```bash
unzip -p file.hookpad project.json
```

### .json files
Direct JSON. May have UTF-8 BOM, so read with `encoding='utf-8-sig'`.

## Key Fields

### Key/Tonic
```python
keys = d.get('keys', [])
tonic = keys[0].get('tonic', 'C')  # e.g. 'A', 'G', 'C'
```
NOT `d.get('key')` - that's the old format.

### Sections
```python
sections = d.get('sections', [])
# Each section: {'beat': 33, 'name': 'verse'}
```
Common names: Intro, verse, chorus, bridge, outro, refrain, prechorus, interlude, solo

### Chords
```python
chords = d.get('chords', [])
# Each chord:
{
  'root': 2,        # Scale degree: 1=I, 2=ii, 3=iii, 4=IV, 5=V, 6=vi, 7=vii°
  'beat': 1,        # Start beat (1-indexed)
  'duration': 4,    # In beats
  'applied': 0,     # Secondary chord target (0 = none, 4 = IV/IV, etc.)
  'type': 5,        # Chord type (5 = triad)
}
```

### Applied Chords (Secondary Functions)
When `applied > 0`, the chord is a secondary function. The root is relative to the applied degree:

```python
if applied > 0:
    # Root is relative to the key of the applied degree
    # Example: root=4, applied=4 means IV/IV
    # In A major: IV=D, IV of D = G (the bVII of A)
    actual_semitones = (key_num + DEGREE_SEMITONES[applied] + DEGREE_SEMITONES[root]) % 12
```

## Converting Scale Degrees to Chord Names

```python
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
NOTE_TO_NUM = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11, ...}
DEGREE_SEMITONES = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
DEGREE_QUALITY = {1: '', 2: 'm', 3: 'm', 4: '', 5: '', 6: 'm', 7: 'dim'}

def get_chord_name(chord, key_num):
    root_deg = chord['root']
    applied = chord.get('applied', 0)

    root_semitones = DEGREE_SEMITONES[root_deg]

    if applied > 0:
        applied_semitones = DEGREE_SEMITONES[applied]
        actual_semitones = (key_num + applied_semitones + root_semitones) % 12
    else:
        actual_semitones = (key_num + root_semitones) % 12

    quality = DEGREE_QUALITY[root_deg]
    return NOTES[actual_semitones] + quality
```

## Visual Format

### Beat Grid
8 characters per bar (2 chars per beat). Each chord name followed by dashes for duration:

```
|A———————|A———————|C#m—————|C#m—————|
```

- 8 dashes = 1 bar (4 beats)
- 4 dashes = 2 beats
- 2 dashes = 1 beat
- `|` = bar line

### Line Breaks
4 bars per line (one phrase):

```
Help (A)
  Verse (16 bars)
    |A———————|A———————|C#m—————|C#m—————|
    |F#m—————|F#m—————|D———G———|A———————|
    |A———————|A———————|C#m—————|C#m—————|
    |F#m—————|F#m—————|D———G———|A———————|
```

This shows:
- Phrase repetition (lines 1-2 = lines 3-4)
- Harmonic acceleration (D—G— crammed into one bar before resolution)
- Section length (16 bars = 4 phrases)

## Workflow

1. Drop `.hookpad` files on Desktop
2. Run the parser script (in beatles-structures.md generator)
3. Output goes to `_music/beatles-structures.md`

## Common Gotchas

1. **Key field**: Use `keys[0].tonic`, not `key`
2. **Applied chords**: Check `applied` field - affects the actual chord
3. **Section beats**: 1-indexed, sections run from their beat to the next section's beat
4. **UTF-8 BOM**: Use `encoding='utf-8-sig'` for .json files
5. **Trailing suffixes**: Filenames often have ` ly o` or ` (1)` - strip these for deduplication
