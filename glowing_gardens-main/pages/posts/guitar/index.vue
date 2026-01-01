<template>
  <Navbar />
  <div id="container">
    <svg viewBox="0 0 600 600">
      <rect fill="saddlebrown" y="200" x="25" height="200" width="600"></rect>
      <rect id="fret_0" fill="grey" y="200" x="25" height="200" width="5"></rect>
      <rect id="fret_1" fill="grey" y="200" x="70" height="200" width="5"></rect>
      <rect id="fret_2" fill="grey" y="200" x="115" height="200" width="5"></rect>
      <rect id="fret_3" fill="grey" y="200" x="160" height="200" width="5"></rect>
      <rect id="fret_4" fill="grey" y="200" x="205" height="200" width="5"></rect>
      <rect id="fret_5" fill="grey" y="200" x="250" height="200" width="5"></rect>
      <rect id="fret_6" fill="grey" y="200" x="295" height="200" width="5"></rect>
      <rect id="fret_7" fill="grey" y="200" x="340" height="200" width="5"></rect>
      <rect id="fret_8" fill="grey" y="200" x="385" height="200" width="5"></rect>
      <rect id="fret_9" fill="grey" y="200" x="430" height="200" width="5"></rect>
      <rect id="fret_10" fill="grey" y="200" x="475" height="200" width="5"></rect>
      <rect id="fret_11" fill="grey" y="200" x="520" height="200" width="5"></rect>
      <rect id="fret_12" fill="grey" y="200" x="565" height="200" width="5"></rect>
      <rect id="string_0" fill="gold" y="220" x="0" height="4" width="600"></rect>
      <rect id="string_1" fill="gold" y="250" x="0" height="4" width="600"></rect>
      <rect id="string_2" fill="gold" y="280" x="0" height="4" width="600"></rect>
      <rect id="string_3" fill="gold" y="310" x="0" height="4" width="600"></rect>
      <rect id="string_4" fill="gold" y="340" x="0" height="4" width="600"></rect>
      <rect id="string_5" fill="gold" y="370" x="0" height="4" width="600"></rect>
      <circle id="dot_0" fill="grey" cy="296" cx="140" r="8"></circle>
      <circle id="dot_1" fill="grey" cy="296" cx="230" r="8"></circle>
      <circle id="dot_2" fill="grey" cy="296" cx="320" r="8"></circle>
      <circle id="dot_3" fill="grey" cy="296" cx="410" r="8"></circle>
      <circle id="dot_4" fill="grey" cy="267" cx="500" r="8"></circle>
      <circle id="dot_5" fill="grey" cy="325" cx="500" r="8"></circle>
    </svg>
  </div>
</template>

<script setup>
let frets = 12;
let strings = 6;

let notes = [
  {
    string: 0,
    fret: 0,
    note: "E",
    note_number: 4,
    note_full_number: 64,
    color: "goldenrod",
    strokeColor: "white",
    x_pos: 12,
    y_pos: 222,
  },
  {
    string: 1,
    fret: 0,
    note: "F",
    note_number: 11,
    note_full_number: 59,
    color: "deeppink",
    strokeColor: "white",
    x_pos: 12,
    y_pos: 252,
  },
  {
    string: 2,
    fret: 0,
    note: "F",
    note_number: 7,
    note_full_number: 55,
    color: "blue",
    strokeColor: "white",
    x_pos: 12,
    y_pos: 282,
  },
  {
    string: 3,
    fret: 0,
    note: "D",
    note_number: 2,
    note_full_number: 50,
    color: "orange",
    strokeColor: "white",
    x_pos: 12,
    y_pos: 312,
  },
  {
    string: 4,
    fret: 0,
    note: "A",
    note_number: 9,
    note_full_number: 45,
    color: "purple",
    strokeColor: "white",
    x_pos: 12,
    y_pos: 342,
  },
  {
    string: 5,
    fret: 0,
    note: "E",
    note_number: 4,
    note_full_number: 40,
    color: "goldenrod",
    strokeColor: "white",
    x_pos: 12,
    y_pos: 372,
  },
  {
    string: 0,
    fret: 1,
    note: "F",
    note_number: 5,
    note_full_number: 65,
    color: "green",
    strokeColor: "white",
    x_pos: 52,
    y_pos: 222,
  },
  {
    string: 1,
    fret: 1,
    note: "C",
    note_number: 0,
    note_full_number: 60,
    color: "red",
    strokeColor: "white",
    x_pos: 52,
    y_pos: 252,
  },
  {
    string: 2,
    fret: 1,
    note: "G#",
    note_number: 8,
    note_full_number: 56,
    color: "navy",
    strokeColor: "black",
    x_pos: 52,
    y_pos: 282,
  },
  {
    string: 3,
    fret: 1,
    note: "D#",
    note_number: 3,
    note_full_number: 51,
    color: "orangered",
    strokeColor: "black",
    x_pos: 52,
    y_pos: 312,
  },
  {
    string: 4,
    fret: 1,
    note: "A#",
    note_number: 10,
    note_full_number: 45,
    color: "rebeccapurple",
    strokeColor: "black",
    x_pos: 52,
    y_pos: 342,
  },
  {
    string: 5,
    fret: 1,
    note: "F",
    note_number: 5,
    note_full_number: 41,
    color: "green",
    strokeColor: "white",
    x_pos: 52,
    y_pos: 372,
  },

  {
    string: 0,
    fret: 2,
    note: "F#",
    note_number: 6,
    note_full_number: 66,
    color: "darkgreen",
    strokeColor: "black",
    x_pos: 96,
    y_pos: 222,
  },
  {
    string: 1,
    fret: 2,
    note: "C#",
    note_number: 1,
    note_full_number: 61,
    color: "darkred",
    strokeColor: "black",
    x_pos: 96,
    y_pos: 252,
  },
  {
    string: 2,
    fret: 2,
    note: "A",
    note_number: 9,
    note_full_number: 57,
    color: "purple",
    strokeColor: "white",
    x_pos: 96,
    y_pos: 282,
  },
  {
    string: 3,
    fret: 2,
    note: "E",
    note_number: 4,
    note_full_number: 52,
    color: "goldenrod",
    strokeColor: "white",
    x_pos: 96,
    y_pos: 312,
  },
  {
    string: 4,
    fret: 2,
    note: "B",
    note_number: 11,
    note_full_number: 47,
    color: "deeppink",
    strokeColor: "white",
    x_pos: 96,
    y_pos: 342,
  },
  {
    string: 5,
    fret: 2,
    note: "F#",
    note_number: 6,
    note_full_number: 42,
    color: "darkgreen",
    strokeColor: "black",
    x_pos: 96,
    y_pos: 372,
  },

  //fret 3

  {
    string: 0,
    fret: 3,
    note: "G",
    note_number: 7,
    note_full_number: 67,
    color: "blue",
    strokeColor: "white",
    x_pos: 140,
    y_pos: 222,
  },
  {
    string: 1,
    fret: 3,
    note: "D",
    note_number: 2,
    note_full_number: 62,
    color: "orange",
    strokeColor: "white",
    x_pos: 140,
    y_pos: 252,
  },
  {
    string: 2,
    fret: 3,
    note: "A#",
    note_number: 10,
    note_full_number: 58,
    color: "rebeccapurple",
    strokeColor: "black",
    x_pos: 140,
    y_pos: 282,
  },
  {
    string: 3,
    fret: 3,
    note: "F",
    note_number: 5,
    note_full_number: 53,
    color: "green",
    strokeColor: "white",
    x_pos: 140,
    y_pos: 312,
  },
  {
    string: 4,
    fret: 3,
    note: "C",
    note_number: 12,
    note_full_number: 48,
    color: "red",
    strokeColor: "white",
    x_pos: 140,
    y_pos: 342,
  },
  {
    string: 5,
    fret: 3,
    note: "G",
    note_number: 7,
    strokeColor: "white",
    note_full_number: 43,
    color: "blue",
    x_pos: 140,
    y_pos: 372,
  },
];

onMounted(() => {
  let svg = document.querySelector("svg");

  for (let i = 0; i < 24; i++) {
    let note_circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    note_circle.setAttribute("cx", notes[i].x_pos);
    note_circle.setAttribute("cy", notes[i].y_pos);
    note_circle.setAttribute("r", 8);
    note_circle.setAttribute("fill", notes[i].color);
    note_circle.setAttribute("stroke", notes[i].strokeColor);
    svg.appendChild(note_circle);
  }
});

//   { string: 0, fret: 2, note: "F#" },
//   { string: 0, fret: 3, note: "G" },
//   { string: 0, fret: 4, note: "G#" },
//   { string: 0, fret: 5, note: "A" },
//   { string: 0, fret: 6, note: "A#" },
//   { string: 0, fret: 7, note: "B" },
//   { string: 0, fret: 8, note: "C" },
//   { string: 0, fret: 9, note: "C#" },
//   { string: 0, fret: 10, note: "D" },
//   { string: 0, fret: 11, note: "D#" },
//   { string: 0, fret: 12, note: "E" },
//   { string: 1, fret: 0, note: "B" },
//   { string: 1, fret: 1, note: "C" },
//   { string: 1, fret: 2, note: "C#" },
//   { string: 1, fret: 3, note: "D" },
//   { string: 1, fret: 4, note: "D#" },
//   { string: 1, fret: 5, note: "E" },
//   { string: 1, fret: 6, note: "F" },
//   { string: 1, fret: 7, note: "F#" },
//   { string: 1, fret: 8, note: "G" },
//   { string: 1, fret: 9, note: "G#" },
//   { string: 1, fret: 10, note: "A" },
//   { string: 1, fret: 11, note: "A#" },
//   { string: 1, fret: 12, note: "B" },
//   { string: 2, fret: 0, note: "G" },
//   { string: 2, fret: 1, note: "G#" },
//   { string: 2, fret: 2, note: "A" },
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
}
svg {
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.2);
}
</style>
