// ---------------------------------------------------------------------------
// Floor plans as plain text.
//
//   #  wall          +  doorway (walkable, no wall above it)
//   .  outside       a-z  room floor — one letter per room
//
// One character = one CELL metres square (see CELL in main.js). This is the
// whole format. It's editable in any text editor, diffable in git, and it's
// the one representation a person and a program can both author — which is
// exactly what a floor plan needs to be.
//
// The connectivity matters more than the shape. Compare `museum` and `house`:
// same footprint, same ten rooms, completely different memory properties.
// ---------------------------------------------------------------------------

export const PLANS = {
  museum: {
    name: 'Museum enfilade',
    note: 'Ten galleries in a chain. To reach 7 you MUST pass through 6 — the '
        + 'building enforces the order, which is what a memory palace wants.',
    rooms: {
      a: 'Entrance Hall', b: 'Long Gallery', c: 'Portrait Room', d: 'Map Room',
      e: 'Rotunda', f: 'Armoury', g: 'Cabinet of Curiosities', h: 'Reading Room',
      i: 'Sculpture Court', j: 'Orangery',
    },
    order: 'abcdejihgf',
    grid: [
      '#########################################',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa+bbbbbbb+ccccccc+ddddddd+eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '####################################+####',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff+ggggggg+hhhhhhh+iiiiiii+jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#########################################',
    ],
  },

  house: {
    name: 'Corridor house',
    note: 'Same ten rooms, but every one opens off a central hall. You can '
        + 'reach room 9 without passing 8 — convenient to live in, worse to '
        + 'remember, because nothing forces the sequence.',
    rooms: {
      a: 'Porch', b: 'Kitchen', c: 'Dining Room', d: 'Study', e: 'Parlour',
      f: 'Pantry', g: 'Bathroom', h: 'Bedroom', i: 'Nursery', j: 'Workshop',
      k: 'Hall',
    },
    order: 'abcdefghij',
    corridor: 'k',
    grid: [
      '#########################################',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '#aaaaaaa#bbbbbbb#ccccccc#ddddddd#eeeeeee#',
      '####+#######+#######+#######+#######+####',
      '#kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk#',
      '#kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk#',
      '#kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk#',
      '####+#######+#######+#######+#######+####',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#fffffff#ggggggg#hhhhhhh#iiiiiii#jjjjjjj#',
      '#########################################',
    ],
  },

  cottage: {
    name: 'Irregular cottage',
    note: 'Rooms of different sizes and shapes. Irregularity is an asset here '
        + '— a room you can describe ("the long thin one") is easier to hold '
        + 'than a room that is merely the fourth identical box.',
    rooms: {
      a: 'Snug', b: 'Kitchen', c: 'Long Hall', d: 'Cellar Stair',
      e: 'Box Room', f: 'Bedroom',
    },
    order: 'abcdef',
    grid: [
      '###################',
      '#aaaaaaa#bbbbbbbbb#',
      '#aaaaaaa#bbbbbbbbb#',
      '#aaaaaaa+bbbbbbbbb#',
      '#aaaaaaa#bbbbbbbbb#',
      '###+#######+#######',
      '#ccccccccccccccccc#',
      '#ccccccccccccccccc#',
      '####+####+#####+###',
      '#ddddd#eeeee#fffff#',
      '#ddddd#eeeee#fffff#',
      '#ddddd#eeeee#fffff#',
      '###################',
    ],
  },
};

// Distinct floor tints so rooms read apart from above and at eye level.
export const ROOM_TINTS = [
  0xb0553f, 0x4a7fa8, 0x6f9a4a, 0xb08a3a, 0x8a5aa8,
  0x3f9a8a, 0xc46a8a, 0x5a6f9a, 0x9a7a4a, 0x4a8a5a,
  0x7a7a86, 0xa85a5a,
];
