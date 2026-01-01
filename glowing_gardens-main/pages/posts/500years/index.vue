<template>
  <Navbar />

  <v-navigation-drawer width="350" location="right" v-model="lefter">
    <v-list>
      <v-list-item
        v-for="event in events"
        :key="event"
        :prepend-avatar="event.image"
        @click="load_event(event)"
      >
        <!-- <template v-slot:prepend>
          <v-img :src="event.image" alt="event.image" />
        </template> -->
        <v-list-item-title>{{ event.event }} </v-list-item-title>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>

  <div id="container">
    <svg viewBox="0 0 600 600">
      <rect
        v-for="(decade, i) in decade_1500s"
        :x="i * 60"
        y="0"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <rect
        v-for="(decade, i) in decade_1600s"
        :id="decade"
        :x="i * 60"
        y="60"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <rect
        v-for="(decade, i) in decade_1700s"
        :id="decade"
        :x="i * 60"
        y="120"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <rect
        v-for="(decade, i) in decade_1800s"
        :id="decade"
        :x="i * 60"
        y="180"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <rect
        v-for="(decade, i) in decade_1900s"
        :id="decade"
        :x="i * 60"
        y="240"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <rect
        v-for="(decade, i) in decade_1900s"
        :id="decade"
        :x="i * 60"
        y="240"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <rect
        v-for="(decade, i) in decade_2000s"
        :id="decade"
        :x="i * 60"
        y="300"
        width="60"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
      <text x="10" y="35" fill="navy" opacity=".4">1500s</text>
      <text x="70" y="35" fill="navy" opacity=".4">1510s</text>
      <rect
        :id="2020"
        x="120"
        y="300"
        width="18"
        height="60"
        fill="lightblue"
        stroke-width="1"
        stroke="white"
      />
    </svg>
  </div>
  <v-bottom-navigation style="width: 100vw">
    <v-btn @click="lefter = !lefter">
      <!-- <v-icon>mdi-home</v-icon> -->
      List of Events
    </v-btn>
  </v-bottom-navigation>
</template>

<script setup>
import { useDisplay } from "vuetify";
const { mdAndDown } = useDisplay();

let lefter = ref(true);
let my_array = ref([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]);
let decade_1500s = ref([1500, 1510, 1520, 1530, 1540, 1550, 1560, 1570, 1580, 1590]);
let decade_1600s = ref([1600, 1610, 1620, 1630, 1640, 1650, 1660, 1670, 1680, 1690]);
let decade_1700s = ref([1700, 1710, 1720, 1730, 1740, 1750, 1760, 1770, 1780, 1790]);
let decade_1800s = ref([1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880, 1890]);
let decade_1900s = ref([1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980, 1990]);
let decade_2000s = ref([2000, 2010]);
let rect = null;

const load_event = (event) => {
  console.log(event.year);
  let svg = document.querySelector("svg");
  if (rect != null) {
    svg.removeChild(rect);
  }

  if (event.year.includes("-")) {
    let start_year = parseInt(event.year.split("-")[0]);
    let end_year = parseInt(event.year.split("-")[1]);

    if (
      event.year.split("-")[1].substring(0, 2) != event.year.split("-")[0].substring(0, 2)
    ) {
      //need two rects
      let start_year = parseInt(event.year.split("-")[0]);
      let end_year = parseInt(event.year.split("-")[1]);
      let pivot_year = parseInt(event.year.split("-")[1].substring(0, 2) + "00");
      let previous_century_start = parseInt(
        event.year.split("-")[0].substring(0, 2) + "00"
      );

      let subtracter = start_year - 1500;
      let rower = Math.floor(subtracter / 100);
      let columner = subtracter % 100;
      let nu_years = pivot_year - start_year;

      glyfs.rect(
        svg,
        6 * columner,
        rower * 60,
        6 * nu_years,
        60,
        "orange",
        "black",
        0.5,
        "years_",
        0,
        "year_rects"
      );

      //second one
      let subtracter2 = end_year - 1500;
      let rower2 = Math.floor(subtracter2 / 100);
      let columner2 = subtracter2 % 100;
      let nu_years2 = end_year - pivot_year;

      glyfs.rect(
        svg,
        0,
        rower2 * 60,
        6 * nu_years2,
        60,
        "orange",
        "black",
        0.5,
        "years_",
        0,
        "year_rects"
      );
    } else {
      let subtracter = start_year - 1500;
      let rower = Math.floor(subtracter / 100);
      let columner = subtracter % 100;
      let nu_years = end_year - start_year;

      glyfs.rect(
        svg,
        6 * columner,
        rower * 60,
        6 * nu_years,
        60,
        "orange",
        "black",
        0.5,
        "years_",
        0,
        "year_rects"
      );
    }
  } else {
    let subtracter = parseInt(event.year) - 1500;
    let rower = Math.floor(subtracter / 100);
    let columner = subtracter % 100;
    console.log(rower);
    console.log(columner);

    //add a rect where the year the event happened is
    rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", columner * 6);
    rect.setAttribute("y", rower * 60);
    rect.setAttribute("width", 6);
    rect.setAttribute("height", 60);
    rect.setAttribute("fill", "red");
    rect.setAttribute("stroke-width", 1);
    rect.setAttribute("stroke", "white");
    svg.appendChild(rect);
  }

  if (mdAndDown.value) {
    lefter.value = false;
  }
};

let events = ref([
  {
    year: "1500",
    event: "Mona Lisa is painted",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
  {
    year: "1519",
    event: "Luthers Theses",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/9/90/Lucas_Cranach_d.%C3%84._-_Martin_Luther%2C_1528_%28Veste_Coburg%29.jpg",
    url: "",
  },
  {
    year: "1543",
    event: "The earth revolves around the sun",
    image: "https://upload.wikimedia.org/wikipedia/commons/f/f2/Nikolaus_Kopernikus.jpg",
    url: "",
  },
  {
    year: "1509-1547",
    event: "Henry VIII",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
  {
    year: "1558-1603",
    event: "Queen Elisabeth I",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
  {
    year: "1760-1820",
    event: "George III",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
  {
    year: "1618",
    event: "Thirty Years War",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
  {
    year: "1776",
    event: "American Revolution",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
  {
    year: "1889",
    event: "Van Gogh paints Starry Night",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/2/25/Da_Vinci%27s_Mona_Lisa_with_original_colors_approximation.jpg",
    url: "",
  },
]);
</script>

<style scoped>
#container {
  width: 600px;
  margin: 0 auto;
  margin-top: 84px;
}

svg {
  box-shadow: 0 0 10px 5px rgba(0, 0, 0, 0.1);
}
rect:hover {
  fill: snow;
}

@media (max-width: 600px) {
  #container {
    width: 100vw;
  }
  svg {
    width: 100vw;
  }
}
</style>
