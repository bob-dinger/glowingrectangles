#!/usr/bin/env python3
"""
Update song database with verified BPM/duration data.

This script updates all_songs_database.json with accurate data.
"""

import json

DATABASE_PATH = "/Users/robert/Desktop/hookpad_songs/all_songs_database.json"

# Verified song data from web research
# Format: (artist, title, key, bpm, duration_sec)
VERIFIED_SONGS = [
    # NIRVANA
    ("Nirvana", "Smells Like Teen Spirit", "Db", 117, 301),
    ("Nirvana", "Come As You Are", "F#m", 120, 219),
    ("Nirvana", "Lithium", "D", 124, 257),
    ("Nirvana", "In Bloom", "Bb", 78, 255),
    ("Nirvana", "Heart-Shaped Box", "A", 98, 281),
    ("Nirvana", "All Apologies", "D", 111, 230),
    ("Nirvana", "About A Girl", "Em", 136, 171),
    ("Nirvana", "Breed", "A", 157, 184),
    ("Nirvana", "Drain You", "A", 149, 224),
    ("Nirvana", "Polly", "E", 121, 177),
    ("Nirvana", "Rape Me", "A", 132, 234),
    ("Nirvana", "Dumb", "E", 97, 152),
    ("Nirvana", "Pennyroyal Tea", "Am", 118, 222),
    ("Nirvana", "Lounge Act", "C", 138, 156),
    ("Nirvana", "On A Plain", "D", 120, 195),
    ("Nirvana", "Something In The Way", "E", 109, 232),
    ("Nirvana", "Territorial Pissings", "A", 179, 142),
    ("Nirvana", "Aneurysm", "B", 135, 271),
    ("Nirvana", "Sliver", "C", 119, 132),
    ("Nirvana", "Been A Son", "A", 175, 117),

    # TOM PETTY
    ("Tom Petty", "Free Fallin", "F", 84, 269),
    ("Tom Petty", "I Wont Back Down", "G", 118, 171),
    ("Tom Petty", "American Girl", "D", 118, 234),
    ("Tom Petty", "Breakdown", "Am", 114, 171),
    ("Tom Petty", "Refugee", "F#m", 116, 200),
    ("Tom Petty", "Learning To Fly", "F", 116, 241),
    ("Tom Petty", "Runnin Down A Dream", "E", 171, 284),
    ("Tom Petty", "Mary Janes Last Dance", "Am", 86, 269),
    ("Tom Petty", "Into The Great Wide Open", "G", 80, 238),
    ("Tom Petty", "Dont Do Me Like That", "G", 175, 157),
    ("Tom Petty", "You Dont Know How It Feels", "A", 84, 314),
    ("Tom Petty", "Wildflowers", "F", 80, 219),
    ("Tom Petty", "Dont Come Around Here No More", "Am", 95, 328),
    ("Tom Petty", "The Waiting", "D", 122, 208),
    ("Tom Petty", "Listen To Her Heart", "A", 144, 186),
    ("Tom Petty", "Jammin Me", "G", 117, 253),

    # ROLLING STONES
    ("Rolling Stones", "Satisfaction", "E", 136, 224),
    ("Rolling Stones", "Paint It Black", "Em", 159, 226),
    ("Rolling Stones", "Gimme Shelter", "C#m", 120, 271),
    ("Rolling Stones", "Sympathy For The Devil", "E", 116, 382),
    ("Rolling Stones", "Start Me Up", "C", 125, 214),
    ("Rolling Stones", "Brown Sugar", "C", 126, 229),
    ("Rolling Stones", "Jumpin Jack Flash", "Bb", 137, 227),
    ("Rolling Stones", "Miss You", "Am", 111, 296),
    ("Rolling Stones", "Angie", "Am", 73, 271),
    ("Rolling Stones", "Wild Horses", "G", 71, 341),
    ("Rolling Stones", "Get Off Of My Cloud", "G", 142, 178),
    ("Rolling Stones", "Beast Of Burden", "E", 100, 262),
    ("Rolling Stones", "Tumbling Dice", "B", 105, 235),
    ("Rolling Stones", "Under My Thumb", "F", 132, 220),
    ("Rolling Stones", "Ruby Tuesday", "C", 100, 195),
    ("Rolling Stones", "You Cant Always Get What You Want", "C", 97, 448),

    # U2
    ("U2", "With Or Without You", "D", 110, 296),
    ("U2", "One", "Am", 92, 276),
    ("U2", "Beautiful Day", "A", 136, 248),
    ("U2", "Where The Streets Have No Name", "D", 126, 336),
    ("U2", "I Still Havent Found What Im Looking For", "D", 100, 280),
    ("U2", "Pride", "B", 106, 231),
    ("U2", "Sunday Bloody Sunday", "Bm", 103, 281),
    ("U2", "Mysterious Ways", "E", 99, 244),
    ("U2", "Elevation", "E", 105, 227),
    ("U2", "Vertigo", "E", 140, 193),
    ("U2", "New Years Day", "Am", 136, 335),
    ("U2", "Bad", "A", 105, 352),
    ("U2", "Desire", "E", 135, 179),
    ("U2", "Angel Of Harlem", "C", 102, 232),

    # GREEN DAY
    ("Green Day", "Basket Case", "Eb", 171, 181),
    ("Green Day", "American Idiot", "Ab", 186, 175),
    ("Green Day", "Boulevard Of Broken Dreams", "Fm", 83, 263),
    ("Green Day", "Good Riddance", "G", 95, 154),
    ("Green Day", "Wake Me Up When September Ends", "G", 104, 285),
    ("Green Day", "Holiday", "Fm", 144, 232),
    ("Green Day", "21 Guns", "Dm", 80, 305),
    ("Green Day", "When I Come Around", "G", 98, 177),
    ("Green Day", "Longview", "E", 149, 235),
    ("Green Day", "Minority", "C", 138, 168),
    ("Green Day", "Brain Stew", "A", 76, 192),
    ("Green Day", "Hitchin A Ride", "A", 175, 168),

    # WEEZER
    ("Weezer", "Buddy Holly", "E", 118, 159),
    ("Weezer", "Say It Aint So", "Cm", 76, 258),
    ("Weezer", "Undone", "E", 118, 309),
    ("Weezer", "Island In The Sun", "Em", 118, 193),
    ("Weezer", "Beverly Hills", "F", 117, 194),
    ("Weezer", "Hash Pipe", "E", 135, 184),
    ("Weezer", "My Name Is Jonas", "C", 93, 204),
    ("Weezer", "Pork And Beans", "G", 165, 184),
    ("Weezer", "Perfect Situation", "Ab", 102, 282),
    ("Weezer", "In The Garage", "G", 90, 235),

    # PEARL JAM
    ("Pearl Jam", "Alive", "A", 76, 341),
    ("Pearl Jam", "Jeremy", "A", 106, 320),
    ("Pearl Jam", "Even Flow", "D", 120, 293),
    ("Pearl Jam", "Black", "E", 76, 343),
    ("Pearl Jam", "Daughter", "G", 97, 238),
    ("Pearl Jam", "Better Man", "D", 126, 256),
    ("Pearl Jam", "Last Kiss", "G", 122, 186),
    ("Pearl Jam", "Elderly Woman Behind The Counter In A Small Town", "E", 106, 195),
    ("Pearl Jam", "Corduroy", "E", 126, 322),
    ("Pearl Jam", "Given To Fly", "E", 130, 244),

    # COLDPLAY
    ("Coldplay", "Yellow", "B", 87, 266),
    ("Coldplay", "The Scientist", "Dm", 75, 309),
    ("Coldplay", "Clocks", "Eb", 131, 307),
    ("Coldplay", "Fix You", "Eb", 69, 296),
    ("Coldplay", "Viva La Vida", "Ab", 138, 242),
    ("Coldplay", "Paradise", "Bb", 140, 278),
    ("Coldplay", "Speed Of Sound", "A", 123, 288),
    ("Coldplay", "In My Place", "A", 72, 229),
    ("Coldplay", "Trouble", "G", 70, 270),

    # OASIS
    ("Oasis", "Wonderwall", "F#m", 87, 258),
    ("Oasis", "Dont Look Back In Anger", "C", 82, 287),
    ("Oasis", "Champagne Supernova", "A", 76, 452),
    ("Oasis", "Live Forever", "G", 92, 276),
    ("Oasis", "Slide Away", "Am", 72, 407),
    ("Oasis", "Supersonic", "F#m", 92, 284),
    ("Oasis", "Some Might Say", "D", 108, 319),
    ("Oasis", "Morning Glory", "Am", 100, 304),

    # R.E.M.
    ("Rem", "Losing My Religion", "Am", 126, 269),
    ("Rem", "Everybody Hurts", "D", 98, 316),
    ("Rem", "Man On The Moon", "C", 124, 309),
    ("Rem", "Its The End Of The World As We Know It", "D", 125, 247),
    ("Rem", "Nightswimming", "G", 61, 255),
    ("Rem", "The One I Love", "Em", 125, 197),
    ("Rem", "Shiny Happy People", "D", 126, 229),
    ("Rem", "Orange Crush", "Em", 120, 230),

    # CCR
    ("Ccr", "Fortunate Son", "G", 132, 139),
    ("Ccr", "Bad Moon Rising", "D", 177, 140),
    ("Ccr", "Proud Mary", "D", 127, 192),
    ("Ccr", "Have You Ever Seen The Rain", "C", 116, 160),
    ("Ccr", "Down On The Corner", "C", 105, 165),
    ("Ccr", "Born On The Bayou", "E", 88, 307),
    ("Ccr", "Lookin Out My Back Door", "G", 131, 149),
    ("Ccr", "Travelin Band", "E", 164, 132),
    ("Ccr", "Green River", "E", 160, 150),
    ("Ccr", "Lodi", "D", 82, 192),
    ("Ccr", "Who'll Stop The Rain", "G", 143, 149),
    ("Ccr", "Susie Q", "E", 120, 289),

    # METALLICA
    ("Metallica", "Enter Sandman", "Em", 123, 331),
    ("Metallica", "Nothing Else Matters", "Em", 69, 388),
    ("Metallica", "Master Of Puppets", "Em", 212, 517),
    ("Metallica", "One", "Bm", 108, 446),
    ("Metallica", "Fade To Black", "Bm", 116, 417),
    ("Metallica", "The Unforgiven", "Am", 69, 387),
    ("Metallica", "Sad But True", "D", 96, 325),
    ("Metallica", "Wherever I May Roam", "Em", 112, 404),
    ("Metallica", "For Whom The Bell Tolls", "E", 120, 311),

    # POLICE
    ("Police", "Every Breath You Take", "Ab", 117, 253),
    ("Police", "Roxanne", "Gm", 132, 195),
    ("Police", "Message In A Bottle", "C#m", 150, 291),
    ("Police", "Every Little Thing She Does Is Magic", "Ab", 138, 257),
    ("Police", "Wrapped Around Your Finger", "Am", 100, 319),
    ("Police", "Dont Stand So Close To Me", "Eb", 161, 241),
    ("Police", "King Of Pain", "Bm", 118, 300),
    ("Police", "So Lonely", "C", 144, 287),
    ("Police", "Walking On The Moon", "Dm", 147, 304),

    # RED HOT CHILI PEPPERS
    ("Red Hot Chili Peppers", "Under The Bridge", "E", 68, 264),
    ("Red Hot Chili Peppers", "Californication", "Am", 96, 330),
    ("Red Hot Chili Peppers", "Scar Tissue", "F", 90, 217),
    ("Red Hot Chili Peppers", "Otherside", "Am", 124, 255),
    ("Red Hot Chili Peppers", "By The Way", "F", 122, 216),
    ("Red Hot Chili Peppers", "Cant Stop", "Em", 92, 269),
    ("Red Hot Chili Peppers", "Give It Away", "A", 92, 283),
    ("Red Hot Chili Peppers", "Dani California", "Am", 96, 283),
    ("Red Hot Chili Peppers", "Snow", "Em", 105, 334),

    # FLEETWOOD MAC
    ("Fleetwood Mac", "Dreams", "F", 120, 257),
    ("Fleetwood Mac", "Go Your Own Way", "F", 136, 219),
    ("Fleetwood Mac", "The Chain", "Em", 152, 271),
    ("Fleetwood Mac", "Landslide", "Eb", 82, 199),
    ("Fleetwood Mac", "Rhiannon", "Am", 134, 252),
    ("Fleetwood Mac", "Everywhere", "Bb", 114, 223),
    ("Fleetwood Mac", "Little Lies", "Db", 104, 213),

    # LED ZEPPELIN
    ("Led Zeppelin", "Stairway To Heaven", "Am", 82, 482),
    ("Led Zeppelin", "Whole Lotta Love", "E", 89, 334),
    ("Led Zeppelin", "Kashmir", "Dm", 82, 517),
    ("Led Zeppelin", "Black Dog", "A", 100, 295),
    ("Led Zeppelin", "Rock And Roll", "A", 170, 220),
    ("Led Zeppelin", "Immigrant Song", "F#m", 113, 146),
    ("Led Zeppelin", "Ramble On", "E", 132, 273),

    # BILLY JOEL
    ("Billy Joel", "Piano Man", "C", 88, 339),
    ("Billy Joel", "Uptown Girl", "E", 144, 193),
    ("Billy Joel", "Just The Way You Are", "D", 114, 279),
    ("Billy Joel", "Vienna", "Bb", 98, 212),
    ("Billy Joel", "New York State Of Mind", "C", 75, 332),

    # FOO FIGHTERS
    ("Foo Fighters", "Everlong", "Dm", 158, 250),
    ("Foo Fighters", "Learn To Fly", "Bb", 136, 238),
    ("Foo Fighters", "The Pretender", "Am", 173, 269),
    ("Foo Fighters", "Best Of You", "Eb", 129, 256),
    ("Foo Fighters", "Times Like These", "D", 152, 268),

    # DOORS
    ("Doors", "Light My Fire", "Am", 126, 428),
    ("Doors", "Riders On The Storm", "Em", 109, 437),
    ("Doors", "Break On Through", "Em", 180, 146),
    ("Doors", "People Are Strange", "Em", 129, 133),
    ("Doors", "LA Woman", "A", 100, 467),

    # AC/DC
    ("Acdc", "Back In Black", "Em", 92, 255),
    ("Acdc", "Highway To Hell", "A", 116, 208),
    ("Acdc", "Thunderstruck", "B", 133, 292),
    ("Acdc", "You Shook Me All Night Long", "G", 128, 210),
    ("Acdc", "TNT", "A", 125, 215),

    # BOB DYLAN
    ("Bob Dylan", "Blowin In The Wind", "G", 85, 168),
    ("Bob Dylan", "Like A Rolling Stone", "C", 96, 369),
    ("Bob Dylan", "Knockin On Heavens Door", "G", 69, 151),
    ("Bob Dylan", "The Times They Are A Changin", "G", 106, 195),
    ("Bob Dylan", "Mr Tambourine Man", "D", 85, 330),
    ("Bob Dylan", "Tangled Up In Blue", "A", 107, 340),
    ("Bob Dylan", "Hurricane", "Am", 194, 528),
    ("Bob Dylan", "All Along The Watchtower", "Am", 112, 152),
    ("Bob Dylan", "Lay Lady Lay", "A", 81, 201),
    ("Bob Dylan", "Positively 4th Street", "D", 118, 236),
    ("Bob Dylan", "Subterranean Homesick Blues", "A", 168, 136),
    ("Bob Dylan", "Dont Think Twice Its All Right", "C", 109, 222),

    # BEATLES
    ("Beatles", "A Day In The Life", "G", 78, 335),
    ("Beatles", "A Hard Days Night", "G", 139, 154),
    ("Beatles", "Across The Universe", "D", 76, 228),
    ("Beatles", "All Ive Gotta Do", "E", 117, 124),
    ("Beatles", "All My Loving", "E", 156, 125),
    ("Beatles", "All You Need Is Love", "G", 104, 237),
    ("Beatles", "And I Love Her", "E", 122, 150),
    ("Beatles", "Baby You'Re A Rich Man", "G", 110, 182),
    ("Beatles", "Back In The Ussr", "A", 144, 163),
    ("Beatles", "Because", "C#m", 91, 165),
    ("Beatles", "Being For The Benefit Of Mr Kite", "Dm", 110, 157),
    ("Beatles", "Birthday", "A", 139, 168),
    ("Beatles", "Blackbird", "G", 94, 138),
    ("Beatles", "Can'T Buy Me Love", "C", 176, 135),
    ("Beatles", "Come Together", "Dm", 82, 259),
    ("Beatles", "Day Tripper", "E", 137, 169),
    ("Beatles", "Dear Prudence", "D", 140, 236),
    ("Beatles", "Dr Robert", "A", 120, 137),
    ("Beatles", "Drive My Car", "D", 125, 157),
    ("Beatles", "Eight Days A Week", "D", 138, 163),
    ("Beatles", "Eleanor Rigby", "Em", 137, 125),
    ("Beatles", "For No One", "B", 86, 122),
    ("Beatles", "From Me To You", "C", 127, 117),
    ("Beatles", "Get Back", "A", 120, 190),
    ("Beatles", "Getting Better", "C", 122, 167),
    ("Beatles", "Girl", "Cm", 120, 153),
    ("Beatles", "Glass Onion", "Am", 114, 130),
    ("Beatles", "Good Day Sunshine", "A", 118, 129),
    ("Beatles", "Got To Get You Into My Life", "G", 125, 148),
    ("Beatles", "Hello Goodbye", "C", 108, 210),
    ("Beatles", "Help", "A", 95, 139),
    ("Beatles", "Helter Skelter", "E", 94, 270),
    ("Beatles", "Here Comes The Sun", "A", 129, 185),
    ("Beatles", "Here There And Everywhere", "G", 84, 145),
    ("Beatles", "Hey Jude", "F", 74, 431),
    ("Beatles", "I Am The Walrus", "A", 86, 274),
    ("Beatles", "I Feel Fine", "G", 178, 139),
    ("Beatles", "I Saw Her Standing There", "E", 163, 175),
    ("Beatles", "I Should Have Known Better", "G", 144, 166),
    ("Beatles", "I Want To Hold Your Hand", "G", 131, 145),
    ("Beatles", "I'M Happy Just To Dance With You", "E", 140, 116),
    ("Beatles", "Im Happy Just To Dance With You", "E", 140, 116),
    ("Beatles", "I'M Only Sleeping", "Em", 100, 181),
    ("Beatles", "I'M So Tired", "A", 76, 123),
    ("Beatles", "Im A Loser", "G", 150, 146),
    ("Beatles", "Im A Loser Ly O Completed", "G", 150, 146),
    ("Beatles", "Im Looking Through You", "Ab", 180, 147),
    ("Beatles", "If I Fell", "D", 102, 142),
    ("Beatles", "If I Needed Someone", "A", 131, 144),
    ("Beatles", "In My Life", "A", 103, 147),
    ("Beatles", "Lady Madonna", "A", 104, 142),
    ("Beatles", "Let It Be", "C", 73, 243),
    ("Beatles", "Love Me Do", "G", 148, 142),
    ("Beatles", "Lovely Rita", "E", 88, 164),
    ("Beatles", "Lucy In The Sky With Diamonds", "A", 128, 207),
    ("Beatles", "Martha My Dear", "Eb", 152, 148),
    ("Beatles", "Maxwell'S Silver Hammer", "D", 111, 207),
    ("Beatles", "Michelle", "F", 118, 160),
    ("Beatles", "No Reply", "C", 134, 136),
    ("Beatles", "Norwegian Wood", "E", 177, 125),
    ("Beatles", "Nowhere Man", "E", 120, 164),
    ("Beatles", "Obladioblada", "Bb", 114, 189),
    ("Beatles", "Oh Darling", "A", 84, 206),
    ("Beatles", "Paperback Writer", "G", 160, 144),
    ("Beatles", "Penny Lane", "B", 114, 180),
    ("Beatles", "Please Please Me", "E", 138, 120),
    ("Beatles", "Rain", "G", 112, 178),
    ("Beatles", "Run For Your Life", "D", 150, 138),
    ("Beatles", "Sexy Sadie", "F", 116, 188),
    ("Beatles", "She Loves You", "G", 151, 141),
    ("Beatles", "She Said She Said", "Bb", 140, 157),
    ("Beatles", "She'S Leaving Home", "E", 95, 215),
    ("Beatles", "Something", "C", 66, 182),
    ("Beatles", "Strawberry Fields Forever", "Bb", 92, 250),
    ("Beatles", "The Ballad Of John And Yoko", "E", 132, 178),
    ("Beatles", "The Continuing Story Of Bungalow Bill", "C", 119, 187),
    ("Beatles", "The Night Before", "D", 142, 153),
    ("Beatles", "The Word", "D", 130, 161),
    ("Beatles", "Think For Yourself", "G", 133, 138),
    ("Beatles", "Ticket To Ride", "A", 117, 191),
    ("Beatles", "Twist And Shout", "D", 125, 155),
    ("Beatles", "Wait", "A", 128, 136),
    ("Beatles", "We Can Work It Out", "D", 115, 136),
    ("Beatles", "What Goes On", "E", 132, 169),
    ("Beatles", "When I'M Sixty-Four", "C", 140, 157),
    ("Beatles", "While My Guitar Gently Weeps", "Am", 116, 284),
    ("Beatles", "With A Little Help From My Friends", "E", 112, 164),
    ("Beatles", "Yellow Submarine", "G", 111, 159),
    ("Beatles", "Yesterday", "F", 98, 125),
    ("Beatles", "You Wont See Me", "A", 120, 201),
    ("Beatles", "You'Ve Got To Hide Your Love Away", "G", 184, 129),

    # JOURNEY
    ("Journey", "Dont Stop Believin", "E", 118, 251),
    ("Journey", "Open Arms", "Db", 102, 222),
    ("Journey", "Faithfully", "B", 134, 267),
    ("Journey", "Separate Ways", "Em", 163, 324),
    ("Journey", "Any Way You Want It", "G", 124, 202),

    # PINK FLOYD
    ("Pink Floyd", "Wish You Were Here", "Em", 60, 334),
    ("Pink Floyd", "Comfortably Numb", "Bm", 126, 382),
    ("Pink Floyd", "Another Brick In The Wall", "Dm", 104, 239),
    ("Pink Floyd", "Time", "F#m", 120, 413),
    ("Pink Floyd", "Money", "Bm", 126, 382),

    # JIMI HENDRIX
    ("Jimi Hendrix", "Purple Haze", "E", 107, 170),
    ("Jimi Hendrix", "Hey Joe", "E", 80, 208),
    ("Jimi Hendrix", "All Along The Watchtower", "C#m", 115, 240),
    ("Jimi Hendrix", "Voodoo Child", "E", 88, 300),
    ("Jimi Hendrix", "The Wind Cries Mary", "F", 72, 200),

    # CURE
    ("Cure", "Friday Im In Love", "D", 124, 215),
    ("Cure", "Just Like Heaven", "A", 147, 210),
    ("Cure", "Lovesong", "Gm", 85, 206),
    ("Cure", "Pictures Of You", "A", 107, 448),
    ("Cure", "Boys Dont Cry", "A", 135, 163),
    ("Cure", "Close To Me", "G", 126, 213),

    # MADONNA
    ("Madonna", "Like A Prayer", "Dm", 111, 340),
    ("Madonna", "Material Girl", "A", 143, 239),
    ("Madonna", "Like A Virgin", "F", 119, 219),
    ("Madonna", "Papa Dont Preach", "F#m", 116, 269),
    ("Madonna", "Vogue", "Cm", 116, 276),
    ("Madonna", "Hung Up", "Dm", 121, 338),
    ("Madonna", "Ray Of Light", "Eb", 126, 305),

    # EAGLES
    ("Eagles", "Hotel California", "Bm", 74, 391),
    ("Eagles", "Take It Easy", "G", 139, 211),
    ("Eagles", "Desperado", "G", 71, 213),
    ("Eagles", "Life In The Fast Lane", "A", 111, 285),
    ("Eagles", "One Of These Nights", "Em", 108, 289),

    # ADDITIONAL SONGS (exact title matches)
    # Nirvana
    ("Nirvana", "Blew", "F", 88, 174),
    ("Nirvana", "Dive", "A", 140, 226),
    ("Nirvana", "Sappy", "E", 104, 183),

    # Tom Petty
    ("Tom Petty", "A Higher Place", "E", 92, 280),
    ("Tom Petty", "Stop Dragging My Heart Around", "Am", 136, 263),
    ("Tom Petty", "Won'T Back Down", "G", 118, 171),
    ("Tom Petty", "You Got Lucky", "Em", 120, 220),
    ("Tom Petty", "You Wreck Me", "E", 144, 207),

    # Rolling Stones
    ("Rolling Stones", "Cant You Hear My Knocking", "E", 135, 439),
    ("Rolling Stones", "Happy", "G", 136, 184),
    ("Rolling Stones", "Satisfation", "E", 136, 224),  # typo in database
    ("Rolling Stones", "Street Fighting Man", "C", 122, 195),
    ("Rolling Stones", "The Last Time", "E", 124, 222),

    # Led Zeppelin
    ("Led Zeppelin", "Good Times Bad Times", "E", 95, 166),
    ("Led Zeppelin", "Misty Mountain Hop", "A", 104, 278),
    ("Led Zeppelin", "Over The Hills And Far Away", "G", 106, 288),
    ("Led Zeppelin", "Tangerine", "A", 78, 186),
    ("Led Zeppelin", "When The Levee Breaks", "F", 71, 427),

    # Madonna
    ("Madonna", "Beautiful Stranger", "E", 128, 276),
    ("Madonna", "Borderline", "F", 119, 239),
    ("Madonna", "La Isla Bonita", "Gm", 100, 242),
    ("Madonna", "Open Your Heart", "F#m", 112, 262),
    ("Madonna", "Whos That Girl", "F", 107, 224),

    # Journey
    ("Journey", "Lights", "D", 120, 199),
    ("Journey", "Lovin Touchin Squeezin'", "A", 100, 230),
    ("Journey", "Wheel In The Sky", "Dm", 83, 265),

    # Pink Floyd
    ("Pink Floyd", "Have A Cigar", "Em", 120, 307),
    ("Pink Floyd", "Hey You", "Dm", 115, 281),
    ("Pink Floyd", "Learning To Fly", "F#m", 132, 288),
    ("Pink Floyd", "Welcome To The Machine", "Em", 135, 446),

    # SMASHING PUMPKINS
    ("Smashing Pumpkins", "1979", "Eb", 127, 263),
    ("Smashing Pumpkins", "Tonight Tonight", "Bb", 60, 258),
    ("Smashing Pumpkins", "Bullet With Butterfly Wings", "D", 124, 255),
    ("Smashing Pumpkins", "Today", "Eb", 80, 205),
    ("Smashing Pumpkins", "Disarm", "Eb", 68, 198),

    # 3 DOORS DOWN
    ("3 Doors Down", "Kryptonite", "Bm", 99, 233),
    ("3 Doors Down", "Here Without You", "Bbm", 144, 239),
    ("3 Doors Down", "When I'm Gone", "G", 80, 285),
    ("3 Doors Down", "Be Like That", "D", 86, 270),
    ("3 Doors Down", "Loser", "Eb", 100, 234),

    # WHO
    ("Who", "Baba ORiley", "F", 117, 302),
    ("Who", "Wont Get Fooled Again", "A", 134, 510),
    ("Who", "Behind Blue Eyes", "Em", 60, 217),
    ("Who", "Pinball Wizard", "B", 132, 183),
    ("Who", "My Generation", "G", 192, 198),

    # AEROSMITH
    ("Aerosmith", "Dream On", "Fm", 78, 267),
    ("Aerosmith", "I Dont Want To Miss A Thing", "D", 82, 298),
    ("Aerosmith", "Walk This Way", "C", 109, 207),
    ("Aerosmith", "Sweet Emotion", "A", 99, 274),

    # ABBA
    ("Abba", "Dancing Queen", "A", 101, 232),
    ("Abba", "Mamma Mia", "D", 136, 214),
    ("Abba", "Waterloo", "D", 147, 169),
    ("Abba", "Take A Chance On Me", "B", 112, 246),

    # BEACH BOYS
    ("Beach Boys", "Good Vibrations", "Eb", 150, 218),
    ("Beach Boys", "Wouldnt It Be Nice", "A", 124, 152),
    ("Beach Boys", "California Girls", "B", 158, 156),
    ("Beach Boys", "Surfin Usa", "A", 160, 150),

    # BLINK 182
    ("Blink 182", "All The Small Things", "C", 149, 167),
    ("Blink 182", "I Miss You", "B", 110, 227),
    ("Blink 182", "Whats My Age Again", "F#", 158, 149),
    ("Blink 182", "Dammit", "C", 220, 165),

    # KATY PERRY
    ("Katy Perry", "Firework", "Ab", 124, 228),
    ("Katy Perry", "Roar", "Gm", 90, 224),
    ("Katy Perry", "Teenage Dream", "Bb", 120, 227),
    ("Katy Perry", "Hot N Cold", "G", 132, 220),
    ("Katy Perry", "California Gurls", "C", 125, 234),
    ("Katy Perry", "Dark Horse", "F#", 132, 215),
    ("Katy Perry", "Wide Awake", "F", 160, 220),

    # 4 NON BLONDES
    ("4 Non Blondes", "What'S Up", "A", 67, 307),

    # 311
    ("311", "Amber", "A", 95, 273),

    # 38 SPECIAL
    ("38 Special", "Caught Up In You", "D", 131, 263),
    ("38 Special", "Hold On Loosely", "G", 127, 279),

    # 3 DAYS GRACE
    ("3 Days Grace", "Just Like You", "D", 89, 194),
    ("3 Days Grace", "Pain", "Em", 81, 190),
]

def update_database():
    """Update the database with verified song data."""

    # Load existing database
    with open(DATABASE_PATH, 'r') as f:
        data = json.load(f)

    # Create lookup for verified songs
    verified_lookup = {}
    for artist, title, key, bpm, duration in VERIFIED_SONGS:
        # Normalize for matching
        key_norm = (artist.lower(), title.lower().replace("'", "").replace("-", " "))
        verified_lookup[key_norm] = {
            "key": key,
            "bpm": bpm,
            "duration_sec": duration,
            "verified": True
        }

    # Update songs
    updated_count = 0
    for song in data['songs']:
        artist_norm = song['artist'].lower()
        title_norm = song['title'].lower().replace("'", "").replace("-", " ")

        # Try exact match
        lookup_key = (artist_norm, title_norm)
        if lookup_key in verified_lookup:
            verified = verified_lookup[lookup_key]
            song['key'] = verified['key']
            song['bpm'] = verified['bpm']
            song['duration_sec'] = verified['duration_sec']
            song['total_measures'] = round((verified['duration_sec'] * verified['bpm']) / 240)
            song['verified'] = True
            updated_count += 1
        else:
            # Try partial match (title contains)
            for (v_artist, v_title), verified in verified_lookup.items():
                if v_artist == artist_norm and v_title in title_norm:
                    song['key'] = verified['key']
                    song['bpm'] = verified['bpm']
                    song['duration_sec'] = verified['duration_sec']
                    song['total_measures'] = round((verified['duration_sec'] * verified['bpm']) / 240)
                    song['verified'] = True
                    updated_count += 1
                    break

    # Save updated database
    with open(DATABASE_PATH, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Updated {updated_count} songs with verified data")
    print(f"Database saved to: {DATABASE_PATH}")

    # Show verified count
    verified_count = sum(1 for s in data['songs'] if s.get('verified'))
    print(f"\nTotal verified songs: {verified_count} / {len(data['songs'])}")

if __name__ == "__main__":
    update_database()
