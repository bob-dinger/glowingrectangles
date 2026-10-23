#!/usr/bin/env python3
"""
Give every _music page its own browser-tab icon, so a row of tabs can be told
apart: a coloured tile with a short label (PM = Palette Map, 50 = Guitar 50 ...).

    themap_venv/python add_favicons.py

Colour = kind of page; label = which one. The icon is an inline SVG
<link rel="icon" id="gg-icon">, replaced in place on a re-run. Templates get
the icon of the page they build, so palette/runners/tempo rebuilds keep theirs.
Pages written straight from a Python builder lose it on rebuild -- re-run this.
"""
import glob, os, re, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
C = dict(map='#0f8b8d', quiz='#e07a00', guitar='#2f8a3a', sect='#1663c7', pat='#6b3fc0',
         chord='#d02828', beatles='#8038c0', key='#b8860b', song='#3a3a3a', rhythm='#c02080',
         melody='#1f6f5c', home='#151515')

ICONS = {
    'index.html': ('♪', 'home'),
    # maps
    'palette-map.html': ('PM', 'map'), 'palette_map_template.html': ('PM', 'map'),
    'palette-groups.html': ('PG', 'map'), 'palette_groups_template.html': ('PG', 'map'),
    'runners-map.html': ('RM', 'map'), 'runners_map_template.html': ('RM', 'map'),
    'same-progressions.html': ('SP', 'map'), 'same_progressions_template.html': ('SP', 'map'),
    'tempo-map.html': ('TM', 'map'), 'tempo_map_template.html': ('TM', 'map'),
    'beatles-tempo-map.html': ('TM', 'beatles'), 'key-map.html': ('KM', 'map'),
    # quizzes
    'g100-quiz.html': ('Q1', 'quiz'), 'g150-quiz.html': ('Q15', 'quiz'), 'g200-quiz.html': ('Q2', 'quiz'),
    'g250-quiz.html': ('Q25', 'quiz'), 'pool_quiz_template.html': ('Q', 'quiz'),
    'tempo-quiz.html': ('TQ', 'quiz'), 'tempo_quiz_template.html': ('TQ', 'quiz'),
    'key-quiz.html': ('KQ', 'quiz'), 'chord-quiz.html': ('CQ', 'quiz'), 'tab-quiz.html': ('TB', 'quiz'),
    'quiz-facts.html': ('QF', 'quiz'), 'quiz50.html': ('Q50', 'quiz'), 'chord-change-ear.html': ('EAR', 'quiz'),
    # section browsers (bar length) and patterns
    'eight-bar-sections.html': ('8', 'sect'), 'ten-bar-sections.html': ('10', 'sect'),
    'twelve-bar-sections.html': ('12', 'sect'), 'sixteen-bar-sections.html': ('16', 'sect'),
    'eight-bar-patterns.html': ('8', 'pat'), 'ten-bar-patterns.html': ('10', 'pat'),
    'twelve-bar-patterns.html': ('12', 'pat'), 'fourteen-bar-patterns.html': ('14', 'pat'),
    'sixteen-bar-patterns.html': ('16', 'pat'), 'twenty-four-bar-patterns.html': ('24', 'pat'),
    'sections.html': ('S', 'sect'), 'sections-beatles.html': ('SB', 'sect'), 'sections-other.html': ('SO', 'sect'),
    'sections-studied.html': ('SS', 'sect'), 'section-signatures.html': ('SIG', 'sect'),
    'patterns.html': ('P', 'pat'), 'phrase-patterns.html': ('PP', 'pat'), 'phrases.html': ('PF', 'pat'),
    'breaks.html': ('BR', 'pat'), 'changes.html': ('CH', 'pat'), 'forms.html': ('F', 'beatles'),
    'forms2.html': ('F', 'pat'), 'templates.html': ('T', 'pat'), 'blocks.html': ('BL', 'pat'),
    # chords
    'chord-colors.html': ('CC', 'chord'), 'chord-groups.html': ('50', 'chord'), 'chord-groups-sounds.html': ('GS', 'chord'),
    'chord-sounds-sheet.html': ('SH', 'chord'), 'chord-set-names.html': ('SET', 'chord'), 'chord-sets.html': ('4', 'chord'),
    'chord-tree.html': ('TR', 'chord'), 'chord-viz.html': ('CV', 'chord'), 'chord-chart-visualizer.html': ('CV', 'chord'),
    'permutations.html': ('PRM', 'chord'), 'permutations-120.html': ('120', 'chord'), 'nineteen.html': ('19', 'chord'),
    'thirteen.html': ('13', 'chord'), 'how-few.html': ('HF', 'chord'), 'sigils.html': ('SG', 'chord'),
    'mixolydian.html': ('MX', 'chord'), 'vamp-home.html': ('VH', 'chord'), 'blues.html': ('12B', 'chord'),
    'fire-escape-mashup.html': ('360', 'chord'), 'getting-better-voicings.html': ('GB', 'chord'),
    'simplified-library.html': ('SL', 'chord'), 'favorites.html': ('★', 'chord'),
    # keys
    'key-changes.html': ('KC', 'key'), 'key-journeys.html': ('KJ', 'key'), 'key-roles.html': ('KR', 'key'),
    'keys.html': ('K', 'key'), 'songs-by-key.html': ('SK', 'key'),
    # rhythm
    'change-rhythm.html': ('CR', 'rhythm'), 'rhythm-library.html': ('RL', 'rhythm'), 'rhythm-slots.html': ('16S', 'rhythm'),
    'strum-library.html': ('ST', 'rhythm'), 'drums.html': ('DR', 'rhythm'), 'drums_template.html': ('DR', 'rhythm'),
    # melody
    'melody-structures.html': ('MS', 'melody'),
    # beatles
    'Beatles-Study.html': ('B', 'beatles'), 'beatles_by_project.html': ('BP', 'beatles'),
    # songs / tools
    'songs.html': ('SN', 'song'), 'song-browser.html': ('SBR', 'song'), 'song.html': ('SV', 'song'),
    'song_viewer.html': ('NW', 'song'), 'videos.html': ('▶', 'song'), 'ug.html': ('UG', 'song'),
    'piano.html': ('PNO', 'song'), 'fretboard.html': ('FB', 'song'),
    'guitar-lessons.html': ('GL', 'guitar'), 'guitar_lessons_template.html': ('GL', 'guitar'),
    'john-deere-verse.html': ('JD', 'song'), 'times-they-are-a-changin-verse.html': ('TT', 'song'),
}


def svg(label, color):
    n = len(label)
    size = 40 if n == 1 else 30 if n == 2 else 22
    s = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'>"
         f"<rect width='64' height='64' rx='14' fill='{color}'/>"
         f"<text x='32' y='33' font-family='-apple-system,Helvetica,Arial,sans-serif' font-weight='800' "
         f"font-size='{size}' fill='white' text-anchor='middle' dominant-baseline='central'>{label}</text></svg>")
    return 'data:image/svg+xml,' + urllib.parse.quote(s, safe="/:=' ,-")


def icon_for(name):
    if name in ICONS: return ICONS[name]
    m = re.fullmatch(r'Guitar(\d+)\.html', name)
    if m: return m.group(1), 'guitar'
    return None


def main():
    done, missing = 0, []
    for path in sorted(glob.glob(os.path.join(HERE, '*.html'))):
        name = os.path.basename(path)
        ic = icon_for(name)
        if not ic: missing.append(name); continue
        label, kind = ic
        tag = f'<link rel="icon" id="gg-icon" href="{svg(label, C[kind])}">'
        h = open(path, encoding='utf-8', newline='').read()      # keep CRLF files CRLF
        if 'id="gg-icon"' in h:
            h = re.sub(r'<link rel="icon" id="gg-icon"[^>]*>', lambda m: tag, h, count=1)
        elif '</title>' in h:
            h = h.replace('</title>', '</title>' + ('\r\n' if '\r\n' in h else '\n') + tag, 1)
        else:
            missing.append(name + ' (no <title>)'); continue
        open(path, 'w', encoding='utf-8', newline='').write(h)
        done += 1
    print(f'{done} pages have an icon' + (f'; none for: {missing}' if missing else ''))


if __name__ == '__main__':
    main()
