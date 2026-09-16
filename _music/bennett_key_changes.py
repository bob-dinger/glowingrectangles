"""David Bennett's catalogue of Beatles key changes, from his video
"Every Beatles key change EXPLAINED" (youtube JKdr4zHa7Z8). He listened to all
186 originals; 53-54 use a key change. Each entry: the TYPE he assigns + detail.
This is the authoritative 'type' source for beatles_key_changes.xlsx.
"""
# type buckets in his taxonomy
BENNETT = {
    # --- up a semitone ---
    'If I Fell':                           ('semitone up',   'Db -> D by the end of the 8-bar intro'),
    'And I Love Her':                      ('semitone up',   'E->F for the acoustic guitar solo'),
    'Lucy in the Sky with Diamonds':       ('semitone up',   'verse A -> pre-chorus Bb -> chorus G'),
    # --- up a whole tone ---
    'Being For The Benefit Of Mr. Kite':   ('whole-step up', 'verse C minor -> chorus D minor'),
    "Sgt. Pepper's Lonely Hearts Club Band": ('whole-step up', 'reprise: F -> G'),
    'Martha My Dear':                      ('whole-step up', 'subtle, weaves up a tone'),
    'Penny Lane':                          ('whole-step down','B (->parallel Bm) -> chorus A; up to B near end'),
    'Day Tripper':                         ('whole-step up', 'verse E -> chorus F#'),
    # --- down a whole tone ---
    'Magical Mystery Tour':                ('whole-step down','E -> chorus D'),
    'Good Day Sunshine':                   ('whole-step down','chorus B -> verse A; later D for solo'),
    'I Am The Walrus':                     ('whole-step down','B -> A'),
    # --- minor third ---
    'Here, There And Everywhere':          ('minor third',   'G -> chorus Bb'),
    "You're Going To Lose That Girl":      ('minor third',   ''),
    'Lady Madonna':                        ('minor third',   ''),
    'Two Of Us':                           ('minor third',   ''),
    'Doctor Robert':                       ('minor third',   ''),
    'When I Get Home':                     ('minor third',   ''),
    'The Continuing Story Of Bungalow Bill': ('minor third', 'phrase C -> moved down to A'),
    'Something':                           ('minor third',   'C -> A for middle-eight'),
    'A Day In The Life':                   ('minor third',   'G (John) -> E (Paul), atonal crescendo — debatable'),
    'The End':                             ('minor third',   'A -> C for the very last bit'),
    # --- major third ---
    'Sun King':                            ('major third',   '4 semitones'),
    # --- closely related (4th/5th) ---
    'Do You Want To Know A Secret':        ('up a 4th',      'middle section'),
    'I Want To Hold Your Hand':            ('up a 4th',      'middle section'),
    "I Want You (She's So Heavy)":         ('closely related','riff/intro D minor -> verse A minor'),
    'Strawberry Fields Forever':           ('closely related','F -> Bb (between-keys concept)'),
    'Julia':                               ('closely related','D major -> F minor via C minor chord (middle-eight)'),
    'Help!':                               ('closely related','B minor <-> A major (very subtle)'),
    'For No One':                          ('closely related','B major -> chorus C minor (relative, 5-1 cadences)'),
    "Octopus's Garden":                    ('closely related','E -> A'),
    # --- tonicizations (brief) ---
    'From Me To You':                      ('tonicization',  'briefly C -> F in the middle'),
    'Yes It Is':                           ('tonicization',  'brief'),
    'Another Girl':                        ('tonicization',  'brief'),
    # --- parallel major/minor (same tonic) ---
    'While My Guitar Gently Weeps':        ('parallel maj/min','verse A minor -> chorus A major'),
    "I'll Be Back":                        ('parallel maj/min',''),
    'Things We Said Today':                ('parallel maj/min',''),
    'Michelle':                            ('parallel maj/min',''),
    'The Fool On The Hill':                ('parallel maj/min',''),
    'You Never Give Me Your Money':        ('parallel maj/min',''),
    # --- parallel modes ---
    'Norwegian Wood':                      ('parallel modes','E mixolydian -> E dorian'),
    # --- relative major/minor (& relative modes) ---
    'Yesterday':                           ('relative maj/min','F major -> D minor via 2-5-1'),
    "I'm Happy Just To Dance With You":    ('relative maj/min','C minor -> relative major Eb'),
    "I'm Only Sleeping":                   ('relative maj/min',''),
    'Happiness Is A Warm Gun':             ('relative maj/min',''),
    'When I\'m Sixty-Four':                ('relative maj/min',''),
    'Carry That Weight':                   ('relative maj/min',''),
    'We Can Work It Out':                  ('relative maj/min',''),
    'Lovely Rita':                         ('relative modes','Bb mixolydian -> Eb major'),
    'If I Needed Someone':                 ('relative min',  'A mixolydian -> middle-eight B minor'),
    'Come Together':                       ('ambiguous',     'verse D minor -> chorus B minor or D major'),
    # --- miscellaneous / tag ---
    'Cry Baby Cry':                        ('tag/hidden',    '"Can You Take Me Back" tag at the end'),
    # explicitly NOT counted by Bennett (kept for reference):
    # 'Hey Jude' F ionian->F mixolydian (major modes), 'Piggies' too fleeting
}
