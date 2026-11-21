"""The simple named-progression sheet: chords in C, labels, name, source video.

Deliberately small and hand-curated -- the auto-mined bennett_progressions.xlsx is
the messy complete index; this is the list the user actually trusts, to be added to by
hand. Minor progressions are anchored on Am per the white-note convention.

Labels use the PARALLEL-MAJOR reference (so a minor-key chord that sits below where C
major puts that degree carries a flat): Am G F = i bVII bVI. Note this is NOT the
convention chord_label.py prints, which shifts to the relative major and would give
vi V IV for the same chords -- see music_chord_label_accuracy.

    themap_venv/python named_progressions_sheet.py
"""
import os

OUT = os.path.expanduser('~/Desktop/named_progressions.xlsx')
V = 'https://youtu.be/'

# chords | labels | name | video id | which video it was presented in | notes
ROWS = [
 ('C G Am F',  'I V vi IV',        'Axis',               'U8ImkF7FMPw', 'When did the Axis chord progression become so popular?', 'user wrote "C,G,A,F" -- the vi is Am'),
 ('F G Em Am', 'IV V iii vi',      "Japan's favourite",  '6aezSL_GvZA', "Japan's favourite chord progression and why it works", 'aka the Royal Road'),
 ('G Am F C',  'V vi IV I',        'Angels',             '5pngzGN1zSI', 'Songs that use the Angels chord progression', 'the Axis cycle entered on V'),
 ('C Bb F C',  'I bVII IV I',      'Mixolydian vamp',    'Vyc8lezaa9g', '7 super common chord progressions and why they work', 'Bb written A# in the source list'),
 ('C G F G',   'I V IV V',         'Major scale vamp',   'Vyc8lezaa9g', '7 super common chord progressions and why they work', ''),
 ('C Am F G',  'I vi IV V',        'Doo-wop / 50s',      's656DS6EMZQ', 'This chord progression NEVER goes out of style!', 'also in 7 super common (Vyc8lezaa9g). Third alias: the BLUE MOON progression. He flags the name as misleading -- unlike the 12-bar blues or the axis it has been "consistently popular before and since the 50s", and he traces it to Mozart Piano Concerto No. 24. One chord away from rhythm changes: swap the IV for a ii'),
 ('F G C Am',  'IV V I vi',        'Viva la Vida',       'Vyc8lezaa9g', '7 super common chord progressions and why they work', 'the doo-wop cycle entered on IV; he calls it 4516. Also covered in "4 classic chord progressions" (9zbP0GQzUuI), where he says it outright: the 50s progression 1-6-4-5 "is the same thing but we started on the fourth degree of the scale, we started halfway through". Climbs IV-V up into the tonic, then drops to vi'),
 ('Am F C G',  'vi IV I V',        'Other axis',         'Vyc8lezaa9g', '7 super common chord progressions and why they work', 'the Axis cycle entered on vi'),
 ('Am G F G',  'i bVII bVI bVII',  'Aeolian vamp',       'Vyc8lezaa9g', '7 and 6 super common chord progressions', 'he treats it as 3 chords; the 4th is the return to bVII'),
 ('Am G F E',  'i bVII bVI V',     'Andalusian cadence', '_g9r-zRcxI0', 'Songs that use the Andalusian Cadence', 'the V is MAJOR (E, not Em) -- phrygian dominant'),
 ('Am C G D',  'i bIII bVII IV',   'Plagal cascade',     'DfoM4EfHK0k', 'Songs that use the Wonderwall chord progression', 'aka Wonderwall / Mad World / Imagine Dragons. IV is MAJOR (D). Oasis voices it Asus4 -- no third at all'),
 ('Am G Em F', 'i bVII v bVI',     "Can't Stop",         'v3YbEL-_eoI', '6 common chord progressions and why they work', 'the v is MINOR (Em). He also calls it 1756 minor = 6534 major'),
 ('C G Dm F',  'I V ii IV',        'Closing Time',       'v3YbEL-_eoI', '6 common chord progressions and why they work', ''),
 ('F C G Am',  'IV I V vi',        'Another axis',       'v3YbEL-_eoI', '6 common chord progressions and why they work', 'the Axis cycle entered on IV'),
 ('C F Am G',  'I IV vi V',        'Mr. Brightside',     'v3YbEL-_eoI', '6 common chord progressions and why they work', 'see also "Why is Mr. Brightside so popular?" (gLHwoHuaHlE)'),
 ('C E F Fm',  'I III IV iv',      'Creep',              'NyiEMdbfjG8', 'Songs that use the Creep chord progression', 'III is MAJOR (E); the iv is the minor-plagal twist'),
 ('C Dm Em F', 'I ii iii IV',      '1-2-3-4 (locomotive)','eC4SEVRT9wE', 'Songs that use the 1-2-3-4 chord progression', ''),
 ('F Em Dm C', 'IV iii ii I',      '4-3-2-1 (locomotive)','',            '', 'NO source video found in the 410 transcripts; the 1-2-3-4 video never mentions it'),
 ('C C7 F Fm', 'I I7 IV iv',       'Magnolia',           'UMiRm8NS1ok', 'Songs that use the Magnolia chord progression', ''),
 ('C Am E F',  'I vi III IV',      'Where Is My Mind',   'ttJlMFsL2ro', 'Songs that use the "Where Is My Mind" progression', 'III is MAJOR (E)'),
 ('C Am G F',  'I vi V IV',        'Purple Rain',        'YEZzB2PpIQ8', 'Songs that use the Purple Rain chord progression', ''),
 ('C D F C',   'I II IV I',        'Eight Days a Week',  '5ANjO8ypYfQ', 'the "Eight Days a Week" chord progression', 'II is MAJOR (D) -- a secondary dominant, V/V'),
 ('C G Am Em', 'I V vi iii',       "Pachelbel's Canon",  '',            '', 'NO source video found; "Classical music\'s favourite" is La Folia, not Pachelbel'),
 ('Ab Bb C',   'bVI bVII I',       'Kiss From A Rose',   'pejqyjTuJHo', '4 Useful Chord Progressions You Should Know', 'aka the Super Mario Cadence (Mario starts on the I). THREE chords; he demos it in G as Eb F G. The tonic arrives MAJOR after two borrowed-minor chords -- he calls that the pixie third -- plus parallel motion, three major chords a tone apart'),
 ('Am D G C',   'vi II V I',        "Isn't She Lovely (major II)",'pejqyjTuJHo', '4 Useful Chord Progressions You Should Know', 'the II is MAJOR (D). Played with heavy upper extensions, which is where the soulful sound comes from'),
 ('C Dm F C',   'I ii IV I',        "What's Up",          'pejqyjTuJHo', '4 Useful Chord Progressions You Should Know', 'climbs away from home and back; never feels like it NEEDS to resolve'),
 ('C Em F G',   'I iii IV V',       "Let's Get It On",    'pejqyjTuJHo&t=428s', '4 Useful Chord Progressions You Should Know', 'Eb Gm Ab Bb in the original. Cited in the Ed Sheeran lawsuit, though he notes the two songs differ'),
 ('F G Am',     'bVI bVII i',       'Running Up That Hill','6TUUe-FrPOI', 'Songs that use the Running Up That Hill chord progression', 'the MINOR-tonic twin of Kiss From A Rose: same two approach chords, different landing'),
 ('Am Bb',      'i bII',            'Phrygian vamp',      'cjOQIbkRQ-4', '5 popular chord progressions and why they work', 'deliberately TWO chords -- he demos it as Em F in E phrygian. The bII is MAJOR (Bb = Bb D F, all in A phrygian) and is the ONLY thing separating phrygian from aeolian. Spell it Bb, not A#'),
 ('C G Bb F',   'I V bVII IV',      'Linger',             'cjOQIbkRQ-4', '5 popular chord progressions and why they work', 'user\'s name. He frames it as a MAJOR/MIXOLYDIAN hybrid -- the bVII is the mixolydian element, which he calls cooler and more mellow than plain major'),
 ('C Dm F G',   'I ii IV V',        'Major scale climb',  'cjOQIbkRQ-4', '5 popular chord progressions and why they work', 'he also calls it the "My Girl" progression (Temptations). NAME COLLISION: chord_sets.json calls C Dm Em F (I ii iii IV) "Major Scale Climb" too -- different progression'),
 ('C F C G',    'I IV I V',         'Bounce',             'cjOQIbkRQ-4', '5 popular chord progressions and why they work', 'user\'s own name. IV is not begging to move, back to I to resolve, then V to start it moving again'),
 ('F C G G',    'IV I V V',         'Paradise',           'cjOQIbkRQ-4', '5 popular chord progressions and why they work', 'user\'s name. The doubled V is the point: it opens OFF the tonic (subdominant, already wanting to move), resolves, then holds the dominant two bars before settling'),
 ('C Am Dm G',  'I vi ii V',        'Rhythm changes / Sherry Baby','MAAssFBwvUY', '2 Super Satisfying Chord Progressions And How To Write Your Own', 'also s656DS6EMZQ. RHYTHM CHANGES, after "I Got Rhythm" -- the OLDER form, common in jazz and show tunes; the 50s progression swapped its ii for a IV and that became the modern choice. F and Dm differ by ONE note (C vs D), so they are interchangeable. C-Am is a minor 3rd, then every root descends a FIFTH: Am-Dm-G-C'),
 ('Am Dm G C',  'vi ii V I',        "Isn't She Lovely (6-2-5-1)",'MAAssFBwvUY', '2 Super Satisfying Chord Progressions And How To Write Your Own', 'the minor one: same loop entered one chord later, so you get FOUR consecutive descending fifths. NOT the same as the Isn\'t She Lovely row -- that one has a MAJOR II (he plays C#m7 then F#7, "rather than the F# minor you might expect"). This is the all-diatonic version'),
 ('Am C D F',   'i bIII IV bVI',    'Minor climb',        'XCzZHPD1qKk', '3 Minor key chord progressions you should know', 'aka the House of the Rising Sun progression -- its first FOUR chords, not the whole thing. Mixes AEOLIAN with DORIAN: the D major introduces F#, the raised 6th that A minor does not have'),
 ('Am Dm C E',  'i iv bIII V',      'Welcome to the Internet','XCzZHPD1qKk', '3 Minor key chord progressions you should know', "user's name; he does not name it. Mixes AEOLIAN with HARMONIC MINOR: first three chords are natural minor, then the E major brings in G# and drives it back to the top. He calls it serious and dramatic"),
 ('Am G Dm Am', 'i bVII iv i',      'Aeolian closed loop','XCzZHPD1qKk', '3 Minor key chord progressions you should know', 'FOUR chords -- user confirmed the G is played throughout the video. The transcripts are auto-captions of SPEECH ONLY, so a chord he plays without naming is invisible there; his spoken line was just "A minor, D minor and A minor again". Being closed is the point: it begins and ends on i, so unlike an open four-chord loop it does not need to repeat to resolve. Stays entirely in aeolian (all white notes)'),
 ('C Em Am G',  'I iii vi V',       'Descending stepwise','dyDFcchDl2M', '40 Songs that use Descending Stepwise chord progressions', 'defined by the BASS, not the roots: voice the iii over B so the bass walks C-B-A-G, then the V turns it back to the top. He notes many different chords can harmonise the same descending line. NOTE this is the one family where music_ignore_slash_chords is wrong -- drop the inversion and the progression stops being itself'),
 ('Am Am F E',  'i i bVI V',        'Harmonic minor vamp','9zbP0GQzUuI', '4 classic chord progressions and why they work', 'HIS name; Sweet Dreams is his example. "Begins on the minor one chord... then the sixth chord of the minor key, then the fifth chord." Harmonic minor because the E major needs the G#. Same cycle as Just the Two of Us (bVI V i) entered on the tonic, and the Andalusian with the bVII replaced by holding Am'),
 ('C/G G C',    'I6/4 V I',         'Cadential 6/4',      'jU-1N9sJ2f4', 'Songs that use the Cadential 6/4 chord progression', 'figured bass: 6/4 = SECOND INVERSION, the fifth in the bass (C/G has C a 4th and E a 6th above G). Tonic in 2nd inversion, then V, then tonic in root position -- drags out a perfect cadence. Almost always ends a phrase; he calls it musical punctuation'),
 ('C F G F',    'I IV V IV',        '1-4-5-4',            '9zbP0GQzUuI', '4 classic chord progressions and why they work', 'built only from the three primary chords: climbs I-IV-V then back down through IV. His name is just the figure'),
 ('Am D',       'i IV',             'Dorian vamp',        '9zbP0GQzUuI', '4 classic chord progressions and why they work', 'TWO chords. The IV is MAJOR (D, with F# -- the raised 6th), and that is the whole dorian signal: in natural or harmonic minor the iv would be minor and sound far more solemn'),
 ('C Am Em G',  'I vi iii V',       'She Loves You',      'riKgcUYCma0', '4 less common chord progressions in pop and rock songs', 'fully diatonic, nothing borrowed -- it is just less common. What makes it characterful is the iii: "the third chord of the key, for whatever reason, is less commonly used"'),
 ('C Dm Am F',  'I ii vi IV',       'Starlight',          'riKgcUYCma0', '4 less common chord progressions in pop and rock songs', 'Muse, verse and chorus. "Almost identical to the axis, the classic 1564, but the five has been swapped out for a [two]" -- so it is the axis with V replaced by ii'),
 ('Am C G Am',  'i bIII bVII i',    'Jolene',             'riKgcUYCma0', '4 less common chord progressions in pop and rock songs', 'a CLOSED loop: "we start at home, go on a short journey up and down the scale, then return to our home", so it has its own cadence. Polly is the same three chords with a different landing'),
 ('Am C G F',   'i bIII bVII bVI',  'Polly',              'riKgcUYCma0', '4 less common chord progressions in pop and rock songs', 'Nirvana. "It only differs by its last chord" from Jolene -- instead of returning to i it goes to bVI. User asked whether the C is right: yes, he spells it A minor, C, G, F'),
 ('Fm7 Bb7 C', 'iv7 bVII7 I', 'Backdoor', 's1tDB79UEsQ', "Songs that use the Backdoor Progression", "\"Put simply, the backdoor progression is the chords F minor 7, B flat 7 resolving to C.\" The iv and bVII both borrowed from the parallel minor; arrives at I from below instead of via V"),
 ('Em Am Dm G C', 'iii vi ii V I', 'Circle of Fifths', '-DQJmicTFGQ', "Songs that use the Circle of Fifths progression", "five chords. \"Almost every chord change is the movement of a perfect fifth\" -- he notes there is exactly one change that is not"),
 ('F F#dim C/G', 'IV #IVdim I6/4', 'Gospel Climb', 'twPIJQj9Aeg', "Songs that use The Gospel Climb chord progression", "a CLIMBING BASS, not a root progression: IV, then a diminished a semitone above it, then the tonic in second inversion. His example in Eb: Ab, Adim, Eb/Bb"),
 ('C Caug Am C7 F', 'I Iaug vi I7 IV', 'Augmented climb', 'ixIS64xvWSQ', "Songs that use the Augmented climb chord progression", "\"the climb up from the tonic chord through the augmented, the sixth, the seventh, and then to the four chord\" -- the top voice walks up by semitone. Songs finish it differently; Last Night on Earth then goes IV to iv"),
 ('Am F/A F#dim/A', 'i bVI6 vi(dim)', 'James Bond', 'rew6FBtC0Mo', "Songs that use the James Bond chord progression", "all over a STATIC bass: \"begins on E minor and then the top note just climbs up one semitone\" giving C/E, then C#, giving a diminished chord inverted over E, then walks back down"),
 ('C Cmaj7 C7 F', 'I Imaj7 I7 IV', 'Something', 'AmqiQFyCAGY', "Songs that use the Something chord progression", "the tonic decaying by semitone (B, Bb) before the IV finally arrives: \"rather than giving us the satisfaction of going to A flat, it climbs back up again\""),
 ('C E A F', 'I III VI IV', 'She\'s Electric', 'mUYgS4IP_TU', "Songs that use the “She’s Electric” chord progression", "\"very similar to the classic axis progression, the 1-5-6-4\" with the V swapped for a MAJOR III (or even a dominant III), which \"really wants to lead us up to the six\""),
 ('F E Am', 'bVI V i', 'Just the Two of Us', '7vT0RxwL1HE', "Songs that use the \"Just The Two Of Us\" chord progression", "in F minor he briefly tonicises the bVI with its own ii-V, \"a little enclave of the key of D flat in a song that\'s in F minor\""),
 ('Am F C E', 'i bVI III V', 'Harmonic Minor Axis', 'LjOKMNNo7HA', "Songs that use the Harmonic Minor Axis progression", "\"technically mixing both the harmonic minor and the natural minor\" -- the C chord gives G natural, the E major gives G#. NOTE: the stored roman writes a bare III where bIII would be consistent with the bVI"),
 ('Am AmMaj7 Am7', 'i i(maj7) i7', 'Line Cliche', 'qLHJ0mSqdmQ', "Songs that use Line Cliche chord progressions", "a MOVING INNER LINE over a static root, not a root progression: \"runs down from E flat minor, E flat minor major seven, E flat minor seven, and then it steps back up the way it came\""),
 ('C Gm Dm Fm', 'I v ii iv', 'Madness', 'dm0mzX-XW50', "This chord progression is Madness!", "\"the chord progression used in this song is C, G minor, D minor, F minor... so we have chords 1, 5, 2 and 4. However, chords five and four are MINOR, which is unusual\""),
 ('Am E Am G Am E', 'i V i bVII i V', 'La Folia', '9vWyS_JGwxQ', "Classical music\'s favourite chord progression", "\"classical music\'s favourite chord progression\" -- frequent in Corelli and Mozart, but he could find only ONE pop song using it. NOT Pachelbel"),
 ('F C G', 'IV I V', 'Coldplay (IV-I-V)', 'Qd_qpdrl2i4', "This chord progression is in every Coldplay hit", "three chords, \"the same pattern of the chords four, one and five\", recurring across Paradise, Fix You and others; often with a sus4 on the V resolving down"),
 ('C Ab G E', 'I bVI V III', 'Wuthering Heights', 'DcWMDoIr1F4', "Kate Bush\'s unique chord progression", "CHROMATIC MEDIANTS: \"two major chords a third away from each other\", twice over, and the loop closes on another third. Every chord major"),
 ('Dm G C', 'ii V I', '2-5-1', '6y-LoytFckI', "Songs that use 2 5 1 chord progressions", "a MODULATION device more than a loop. The ii and the I are both flexible in quality; \"the only chord that really has to stay in a certain form is the five chord -- it has to be major, or preferably a dominant seven\""),
 ('C Dm7/G F', 'I ii7/5 IV', 'Talk Talk', 'KreUHQ0M1ho', "We Need To Talk Talk About This Chord Progression...", "the verse only: tonic, \"a fancy version of the two chord\" voiced over the fifth, then IV. The video is about how the song\'s several progressions interact, not one fixed loop"),
 ('', '(a chord, not a loop)', 'Blur\'s dual third', 'WQdeCWnREos', "Blur\'s unique chord progression", "NOT a progression: a single chord carrying BOTH thirds at once -- \"we have both the major third and the minor third going on at once\" -- which collapses to A minor if the sharp is removed. Also uses a bII major 7 with a #11"),
 ('', '(a chord, not a loop)', 'Beatles\' II major', 'KQRwViNES0c', "The Beatles\' unique chord progression", "NOT a fixed loop: the chorus opens on a major II in a major key, and \"almost no two sections in this song are completely identical\" -- each repeat varies the chords or melody"),
]

def main():
    import openpyxl
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'named progressions'
    cols = ['chords in C', 'labels', 'name', 'video url', 'video', 'notes']
    ws.append(cols)
    for c, l, n, vid, title, note in ROWS:
        ws.append([c, l, n, (V + vid) if vid else '', title, note])
    for cell in ws[1]: cell.font = Font(bold=True)
    ws.freeze_panes = 'A2'
    for i, w in enumerate([16, 20, 22, 34, 54, 76], 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        row[5].alignment = Alignment(wrap_text=True, vertical='top')
    wb.save(OUT)
    print(f"\n  {len(ROWS)} named progressions\n")
    print(f"  {'chords in C':14} {'labels':18} {'name':22} video")
    for c, l, n, vid, title, note in ROWS:
        print(f"  {c:14} {l:18} {n:22} {(V+vid) if vid else '-- none found --'}")
    print(f"\n  -> {OUT}")

if __name__ == '__main__':
    main()
