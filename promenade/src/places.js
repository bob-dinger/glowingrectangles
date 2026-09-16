// ---------------------------------------------------------------------------
// Fifty places, five blocks of ten.
//
// Each block draws from a DIFFERENT vocabulary, which is what keeps fifty
// places distinct — a street of fifty shops blurs by the thirtieth, but a shop
// and a lighthouse never blur. The block's character doubles as the coarse
// index: "that's in the Works, so it's 21–30."
//
// `form` is a silhouette archetype, not a style. The production test is: hold
// the building up as a black outline — can you still tell what it is? If two
// places share a silhouette they are the same place, however different their
// materials. Widths average 25 ft so each block lands near 250 ft.
// ---------------------------------------------------------------------------

export const BLOCKS = [
  {
    key: 'main', name: 'Main Street', character: 'Shops',
    note: 'Storefronts hard against the walkway. 25 ft wide because that is what a timber joist could span.',
    tint: 0xb08a5a, dir: '+x',
    places: [
      { n: 1,  name: 'Bakery',            form: 'flat',    w: 25, h: 24, c: 0xc9a06a },
      { n: 2,  name: 'Barber',            form: 'pole',    w: 18, h: 22, c: 0xbfd0dc },
      { n: 3,  name: 'Diner',             form: 'canopy',  w: 30, h: 15, c: 0xd8d2c0 },
      { n: 4,  name: 'Bookshop',          form: 'stepped', w: 22, h: 28, c: 0x8a6a4a },
      { n: 5,  name: 'Cinema',            form: 'marquee', w: 36, h: 34, c: 0xa8494a, landmark: true },
      { n: 6,  name: 'Ice Cream Parlour', form: 'gable',   w: 20, h: 20, c: 0xe0b8c0 },
      { n: 7,  name: 'Hardware Store',    form: 'flat',    w: 30, h: 22, c: 0x7a7048 },
      { n: 8,  name: 'Flower Shop',       form: 'glass',   w: 20, h: 18, c: 0x9ac48a },
      { n: 9,  name: 'Toy Shop',          form: 'gable',   w: 18, h: 26, c: 0xd8a84a },
      { n: 10, name: 'Pharmacy',          form: 'corner',  w: 28, h: 26, c: 0x7fa8b8 },
    ],
  },
  {
    key: 'civic', name: 'Civic Square', character: 'Institutions',
    note: 'Pale stone, set back a little, taller. Columns and towers instead of shopfronts.',
    tint: 0xcdc6b4, dir: '+z',
    places: [
      { n: 11, name: 'Church',       form: 'spire',    w: 30, h: 30, c: 0xd0caba, landmark: true },
      { n: 12, name: 'School',       form: 'belfry',   w: 34, h: 26, c: 0xc4a88a },
      { n: 13, name: 'Library',      form: 'portico',  w: 30, h: 26, c: 0xd4cdbd },
      { n: 14, name: 'Post Office',  form: 'flagpole', w: 24, h: 22, c: 0xc0b8a4 },
      { n: 15, name: 'Courthouse',   form: 'dome',     w: 32, h: 30, c: 0xd8d2c4 },
      { n: 16, name: 'Town Hall',    form: 'clock',    w: 28, h: 28, c: 0xc8c0ac },
      { n: 17, name: 'Fire Station', form: 'hosetower',w: 26, h: 24, c: 0xa8483a },
      { n: 18, name: 'Police Station',form: 'flat',    w: 20, h: 20, c: 0x8a94a4 },
      { n: 19, name: 'Museum',       form: 'portico',  w: 30, h: 28, c: 0xcfc8b6 },
      { n: 20, name: 'Bank',         form: 'columns',  w: 26, h: 26, c: 0xb8b0a0 },
    ],
  },
  {
    key: 'works', name: 'The Works', character: 'Industry',
    note: 'Dark, functional, tall and thin or long and low. No two the same height.',
    tint: 0x6a6558, dir: '+x',
    places: [
      { n: 21, name: 'Garage',       form: 'shed',      w: 30, h: 16, c: 0x6a6a70 },
      { n: 22, name: 'Water Tower',  form: 'lattice',   w: 22, h: 46, c: 0x8a8a86, landmark: true },
      { n: 23, name: 'Warehouse',    form: 'sawtooth',  w: 36, h: 22, c: 0x7a6f5e },
      { n: 24, name: 'Grain Silos',  form: 'silo',      w: 26, h: 38, c: 0xb0a894 },
      { n: 25, name: 'Foundry',      form: 'chimney',   w: 28, h: 26, c: 0x5a5450 },
      { n: 26, name: 'Rail Depot',   form: 'longlow',   w: 34, h: 14, c: 0x6f6558 },
      { n: 27, name: 'Sawmill',      form: 'shed',      w: 24, h: 20, c: 0x7a6448 },
      { n: 28, name: 'Gasworks',     form: 'drum',      w: 26, h: 30, c: 0x5f6a6a },
      { n: 29, name: 'Machine Shop', form: 'sawtooth',  w: 22, h: 16, c: 0x74705f },
      { n: 30, name: 'Coal Yard',    form: 'conveyor',  w: 28, h: 24, c: 0x4a4642 },
    ],
  },
  {
    key: 'park', name: 'The Park', character: 'Green',
    note: 'Open structures you see through. Lowest block, so the skyline drops.',
    tint: 0x6f9a58, dir: '+z',
    places: [
      { n: 31, name: 'Park Gates',   form: 'arch',     w: 24, h: 20, c: 0x5a6a58 },
      { n: 32, name: 'Bandstand',    form: 'pavilion', w: 26, h: 18, c: 0xc4b48a },
      { n: 33, name: 'Greenhouse',   form: 'glass',    w: 32, h: 20, c: 0xa8c8c0 },
      { n: 34, name: 'Fountain',     form: 'fountain', w: 22, h: 10, c: 0xa8a49a },
      { n: 35, name: 'Playground',   form: 'frame',    w: 26, h: 12, c: 0xd88a4a },
      { n: 36, name: 'Aviary',       form: 'cage',     w: 24, h: 24, c: 0x9aa89a },
      { n: 37, name: 'Boat Pond',    form: 'pond',     w: 30, h: 4,  c: 0x5a8aa8 },
      { n: 38, name: 'Rose Arbour',  form: 'arcade',   w: 22, h: 12, c: 0x8a6a5a },
      { n: 39, name: 'Observatory',  form: 'dome',     w: 24, h: 34, c: 0xc0bcb0, landmark: true },
      { n: 40, name: 'Tea House',    form: 'gable',    w: 20, h: 16, c: 0xd0b890 },
    ],
  },
  {
    key: 'water', name: 'The Waterfront', character: 'Water',
    note: 'The end of the walk. Horizontal, open, and one thing taller than everything else.',
    tint: 0x5f7f96, dir: '+x',
    places: [
      { n: 41, name: 'The Bridge',     form: 'archspan', w: 34, h: 22, c: 0x7a8288 },
      { n: 42, name: 'Boathouse',      form: 'gable',    w: 26, h: 18, c: 0x8a6a4a },
      { n: 43, name: 'Fish Market',    form: 'canopy',   w: 30, h: 16, c: 0xa8b0b4 },
      { n: 44, name: 'Chandlery',      form: 'flat',     w: 18, h: 22, c: 0x6a7a84 },
      { n: 45, name: 'Harbour Crane',  form: 'crane',    w: 24, h: 40, c: 0xc47a3a },
      { n: 46, name: 'Dry Dock',       form: 'dock',     w: 30, h: 8,  c: 0x6a6f72 },
      { n: 47, name: 'Ferry Terminal', form: 'canopy',   w: 28, h: 20, c: 0x8a9aa4 },
      { n: 48, name: 'Lighthouse',     form: 'taper',    w: 22, h: 52, c: 0xd8d4cc, landmark: true },
      { n: 49, name: 'Harbour Master', form: 'clock',    w: 20, h: 24, c: 0xb0a894 },
      { n: 50, name: 'The Pier',       form: 'pier',     w: 30, h: 10, c: 0x7a6a58 },
    ],
  },
];

export const ALL = BLOCKS.flatMap(b => b.places.map(p => ({ ...p, block: b })));
